"""
Importacao de contatos via CSV/Excel.
Espera colunas: nome, email, telefone, empresa, cargo, origem, notas
"""

import csv
import io
import logging

logger = logging.getLogger(__name__)

# Mapeamento de nomes de colunas aceitos -> campo interno
COLUMN_MAP = {
    "nome": "nome",
    "name": "nome",
    "email": "email",
    "e-mail": "email",
    "telefone": "telefone",
    "phone": "telefone",
    "celular": "telefone",
    "empresa": "empresa",
    "company": "empresa",
    "cargo": "cargo",
    "title": "cargo",
    "job_title": "cargo",
    "origem": "origem",
    "source": "origem",
    "notas": "notas",
    "notes": "notas",
    "observacoes": "notas",
}


async def import_contacts_from_file(
    content: bytes,
    filename: str,
    workspace_id: str,
) -> dict:
    """Importa contatos de CSV. Retorna resultado com contagens."""
    from core.db import get_supabase

    if filename.endswith((".xlsx", ".xls")):
        rows = _parse_excel(content)
    else:
        rows = _parse_csv(content)

    supabase = get_supabase()
    total = len(rows)
    criados = 0
    erros = 0
    detalhes_erros = []

    for i, row in enumerate(rows, start=2):  # linha 2+ (1 = header)
        try:
            nome = row.get("nome", "").strip()
            if not nome:
                detalhes_erros.append(f"Linha {i}: campo 'nome' obrigatorio")
                erros += 1
                continue

            data = {
                "workspace_id": workspace_id,
                "nome": nome,
                "email": row.get("email", "").strip() or None,
                "telefone": row.get("telefone", "").strip() or None,
                "empresa": row.get("empresa", "").strip() or None,
                "cargo": row.get("cargo", "").strip() or None,
                "origem": "importacao",
                "notas": row.get("notas", "").strip() or None,
                "dados_extras": {},
            }

            supabase.table("contacts").insert(data).execute()
            criados += 1

        except Exception as e:
            erros += 1
            detalhes_erros.append(f"Linha {i}: {str(e)[:100]}")
            logger.warning(f"Erro ao importar contato linha {i}: {e}")

    # Atualizar billing
    if criados > 0:
        try:
            from core.billing import increment_usage
            for _ in range(criados):
                increment_usage(workspace_id, "contatos_crm")
        except Exception as e:
            logger.warning(f"Falha ao incrementar contatos_crm: {e}")

    return {
        "total": total,
        "criados": criados,
        "erros": erros,
        "detalhes_erros": detalhes_erros[:20],  # Limitar erros retornados
    }


def _parse_csv(content: bytes) -> list[dict]:
    """Parse CSV e retorna lista de dicts com campos mapeados."""
    text = content.decode("utf-8-sig")  # utf-8-sig lida com BOM do Excel
    reader = csv.DictReader(io.StringIO(text))

    rows = []
    for raw_row in reader:
        mapped = {}
        for col, value in raw_row.items():
            if col is None:
                continue
            key = COLUMN_MAP.get(col.strip().lower())
            if key:
                mapped[key] = value
        rows.append(mapped)

    return rows


def _parse_excel(content: bytes) -> list[dict]:
    """Parse Excel (.xlsx/.xls) via openpyxl."""
    try:
        import openpyxl
    except ImportError:
        raise ValueError("Instale openpyxl para importar Excel: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    headers_raw = next(rows_iter, None)
    if not headers_raw:
        return []

    headers = []
    for h in headers_raw:
        key = COLUMN_MAP.get(str(h).strip().lower()) if h else None
        headers.append(key)

    rows = []
    for row_values in rows_iter:
        mapped = {}
        for i, val in enumerate(row_values):
            if i < len(headers) and headers[i]:
                mapped[headers[i]] = str(val) if val is not None else ""
        rows.append(mapped)

    wb.close()
    return rows
