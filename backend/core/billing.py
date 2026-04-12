"""
Serviço de integração com Asaas para billing.
Gerencia customers, subscriptions e webhooks.
"""

import logging
from typing import Optional

import httpx

from core.config import get_settings
from core.db import get_supabase

logger = logging.getLogger(__name__)

settings = get_settings()


class AsaasService:
    """Cliente para a API do Asaas."""

    def __init__(self):
        self.base_url = settings.asaas_base_url
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access_token": settings.asaas_api_key,
        }

    async def create_customer(
        self,
        name: str,
        email: str,
        cpf_cnpj: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> dict:
        """Cria customer no Asaas. Retorna dict com 'id' do customer."""
        payload = {
            "name": name,
            "email": email,
        }
        if cpf_cnpj:
            payload["cpfCnpj"] = cpf_cnpj
        if phone:
            payload["phone"] = phone

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/customers",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_subscription(
        self,
        customer_id: str,
        plan_value_cents: int,
        billing_type: str = "UNDEFINED",
        cycle: str = "MONTHLY",
        description: str = "Assinatura Usina do Tempo",
    ) -> dict:
        """Cria assinatura no Asaas."""
        payload = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": plan_value_cents / 100,
            "cycle": cycle,
            "description": description,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/subscriptions",
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_subscription(self, subscription_id: str) -> dict:
        """Consulta status de uma assinatura."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_subscription(self, subscription_id: str) -> dict:
        """Cancela uma assinatura."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.base_url}/subscriptions/{subscription_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_payment_link(self, payment_id: str) -> dict:
        """Obtém link de pagamento (boleto/pix) de uma cobrança."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/payments/{payment_id}/pixQrCode",
                headers=self.headers,
            )
            if resp.status_code == 200:
                return resp.json()
            return {}


def get_asaas_service() -> AsaasService:
    return AsaasService()


# --- Helper: buscar subscription ativa do workspace ---

def get_workspace_subscription(workspace_id: str) -> Optional[dict]:
    """Retorna a subscription ativa (ou trial) do workspace, com dados do plano."""
    supabase = get_supabase()
    result = (
        supabase.table("subscriptions")
        .select("*, plans(*)")
        .eq("workspace_id", workspace_id)
        .in_("status", ["active", "trial", "past_due"])
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def get_workspace_usage(workspace_id: str) -> dict:
    """Retorna uso do mês atual do workspace."""
    supabase = get_supabase()
    from datetime import date
    first_day = date.today().replace(day=1).isoformat()

    result = (
        supabase.table("usage_metrics")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("mes_referencia", first_day)
        .execute()
    )
    if result.data:
        return result.data[0]
    return {
        "videos_gerados": 0,
        "videos_publicados": 0,
        "conteudos_gerados": 0,
        "campanhas_criadas": 0,
        "contatos_crm": 0,
        "benchmarks_executados": 0,
        "storage_bytes": 0,
        "api_calls": 0,
    }


def increment_usage(workspace_id: str, field: str, amount: int = 1):
    """Incrementa uma métrica de uso do workspace no mês atual."""
    supabase = get_supabase()
    from datetime import date
    first_day = date.today().replace(day=1).isoformat()

    # Upsert: cria registro se não existe, incrementa se existe
    existing = (
        supabase.table("usage_metrics")
        .select("id, " + field)
        .eq("workspace_id", workspace_id)
        .eq("mes_referencia", first_day)
        .execute()
    )

    if existing.data:
        current = existing.data[0].get(field, 0) or 0
        supabase.table("usage_metrics").update(
            {field: current + amount}
        ).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("usage_metrics").insert({
            "workspace_id": workspace_id,
            "mes_referencia": first_day,
            field: amount,
        }).execute()
