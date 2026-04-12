import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import get_current_user, require_role
from core.db import get_supabase
from core.config import get_settings
from core.schemas import (
    PlanResponse, SubscriptionResponse, CheckoutRequest,
    UsageResponse, InvoiceResponse,
)
from core.billing import (
    get_asaas_service, get_workspace_subscription, get_workspace_usage,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans():
    """Lista planos disponíveis (público)."""
    supabase = get_supabase()
    result = (
        supabase.table("plans")
        .select("*")
        .eq("ativo", True)
        .neq("slug", "enterprise")
        .order("preco_centavos")
        .execute()
    )
    return result.data


@router.get("/subscription")
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """Retorna a subscription ativa do workspace com dados do plano."""
    sub = get_workspace_subscription(current_user["workspace_id"])
    if not sub:
        raise HTTPException(status_code=404, detail="Nenhuma assinatura encontrada")
    return sub


@router.get("/usage", response_model=UsageResponse)
async def get_usage(current_user: dict = Depends(get_current_user)):
    """Retorna uso do mês atual do workspace."""
    usage = get_workspace_usage(current_user["workspace_id"])
    return usage


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(current_user: dict = Depends(get_current_user)):
    """Lista faturas do workspace."""
    supabase = get_supabase()
    result = (
        supabase.table("invoices")
        .select("*")
        .eq("workspace_id", current_user["workspace_id"])
        .order("criado_em", desc=True)
        .limit(50)
        .execute()
    )
    return result.data


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    current_user: dict = Depends(require_role(["admin"])),
):
    """Gera checkout para upgrade de plano via Asaas."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Buscar plano
    plan_result = supabase.table("plans").select("*").eq("slug", body.plan_slug).eq("ativo", True).execute()
    if not plan_result.data:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    plan = plan_result.data[0]

    if plan["preco_centavos"] == 0:
        raise HTTPException(status_code=400, detail="Plano gratuito não requer checkout")

    # Buscar workspace
    ws_result = supabase.table("workspaces").select("*").eq("id", workspace_id).execute()
    if not ws_result.data:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    workspace = ws_result.data[0]

    asaas = get_asaas_service()

    # Criar customer no Asaas se não existir
    customer_id = workspace.get("asaas_customer_id")
    if not customer_id:
        try:
            customer = await asaas.create_customer(
                name=workspace["nome"],
                email=workspace.get("email_cobranca") or current_user.get("email", ""),
                cpf_cnpj=workspace.get("documento_titular"),
                phone=workspace.get("telefone"),
            )
            customer_id = customer["id"]
            supabase.table("workspaces").update(
                {"asaas_customer_id": customer_id}
            ).eq("id", workspace_id).execute()
        except Exception as e:
            logger.error(f"Erro ao criar customer no Asaas: {e}")
            raise HTTPException(status_code=502, detail="Erro ao processar pagamento. Tente novamente.")

    # Criar subscription no Asaas
    try:
        asaas_sub = await asaas.create_subscription(
            customer_id=customer_id,
            plan_value_cents=plan["preco_centavos"],
            description=f"Usina do Tempo — Plano {plan['nome']}",
        )
    except Exception as e:
        logger.error(f"Erro ao criar subscription no Asaas: {e}")
        raise HTTPException(status_code=502, detail="Erro ao processar pagamento. Tente novamente.")

    # Atualizar/criar subscription no banco
    existing_sub = get_workspace_subscription(workspace_id)
    now = datetime.now(timezone.utc).isoformat()

    if existing_sub:
        supabase.table("subscriptions").update({
            "plan_id": plan["id"],
            "asaas_subscription_id": asaas_sub.get("id"),
            "asaas_customer_id": customer_id,
            "status": "active",
            "current_period_start": now,
            "atualizado_em": now,
        }).eq("id", existing_sub["id"]).execute()
    else:
        supabase.table("subscriptions").insert({
            "workspace_id": workspace_id,
            "plan_id": plan["id"],
            "asaas_subscription_id": asaas_sub.get("id"),
            "asaas_customer_id": customer_id,
            "status": "active",
            "current_period_start": now,
        }).execute()

    return {
        "detail": "Assinatura criada com sucesso",
        "asaas_subscription_id": asaas_sub.get("id"),
        "plan": plan["nome"],
    }


@router.post("/webhook")
async def asaas_webhook(request: Request):
    """Recebe webhooks do Asaas (payment events)."""
    body = await request.json()
    event = body.get("event")
    payment = body.get("payment", {})

    # Validar webhook token se configurado
    webhook_token = request.headers.get("asaas-access-token", "")
    if settings.asaas_webhook_token and webhook_token != settings.asaas_webhook_token:
        raise HTTPException(status_code=401, detail="Token de webhook inválido")

    logger.info(f"Asaas webhook: event={event}, payment_id={payment.get('id')}")

    supabase = get_supabase()
    subscription_id = payment.get("subscription")

    if not subscription_id:
        return {"status": "ignored", "reason": "no subscription_id"}

    # Buscar subscription local pelo asaas_subscription_id
    sub_result = (
        supabase.table("subscriptions")
        .select("*")
        .eq("asaas_subscription_id", subscription_id)
        .execute()
    )
    if not sub_result.data:
        logger.warning(f"Subscription não encontrada para asaas_id={subscription_id}")
        return {"status": "ignored", "reason": "subscription not found"}

    sub = sub_result.data[0]
    now = datetime.now(timezone.utc).isoformat()

    if event == "PAYMENT_CONFIRMED" or event == "PAYMENT_RECEIVED":
        # Ativar subscription
        supabase.table("subscriptions").update({
            "status": "active",
            "atualizado_em": now,
        }).eq("id", sub["id"]).execute()

        # Registrar invoice
        supabase.table("invoices").insert({
            "subscription_id": sub["id"],
            "workspace_id": sub["workspace_id"],
            "asaas_payment_id": payment.get("id"),
            "valor_centavos": int(float(payment.get("value", 0)) * 100),
            "status": "confirmed",
            "pago_em": now,
        }).execute()

    elif event == "PAYMENT_OVERDUE":
        supabase.table("subscriptions").update({
            "status": "past_due",
            "atualizado_em": now,
        }).eq("id", sub["id"]).execute()

        supabase.table("invoices").insert({
            "subscription_id": sub["id"],
            "workspace_id": sub["workspace_id"],
            "asaas_payment_id": payment.get("id"),
            "valor_centavos": int(float(payment.get("value", 0)) * 100),
            "status": "overdue",
            "vencimento": payment.get("dueDate"),
        }).execute()

    elif event in ("SUBSCRIPTION_DELETED", "SUBSCRIPTION_ENDED"):
        supabase.table("subscriptions").update({
            "status": "canceled",
            "canceled_at": now,
            "atualizado_em": now,
        }).eq("id", sub["id"]).execute()

    return {"status": "processed", "event": event}


@router.post("/cancel")
async def cancel_subscription(current_user: dict = Depends(require_role(["admin"]))):
    """Cancela a assinatura do workspace."""
    workspace_id = current_user["workspace_id"]
    sub = get_workspace_subscription(workspace_id)

    if not sub:
        raise HTTPException(status_code=404, detail="Nenhuma assinatura ativa")

    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    # Cancelar no Asaas se existir
    if sub.get("asaas_subscription_id"):
        try:
            asaas = get_asaas_service()
            await asaas.cancel_subscription(sub["asaas_subscription_id"])
        except Exception as e:
            logger.warning(f"Erro ao cancelar no Asaas: {e}")

    # Buscar plano free
    free_plan = supabase.table("plans").select("id").eq("slug", "free").execute()

    # Atualizar para canceled e criar nova subscription free
    supabase.table("subscriptions").update({
        "status": "canceled",
        "canceled_at": now,
        "atualizado_em": now,
    }).eq("id", sub["id"]).execute()

    if free_plan.data:
        supabase.table("subscriptions").insert({
            "workspace_id": workspace_id,
            "plan_id": free_plan.data[0]["id"],
            "status": "active",
            "current_period_start": now,
        }).execute()

    return {"detail": "Assinatura cancelada. Workspace migrado para plano Free."}
