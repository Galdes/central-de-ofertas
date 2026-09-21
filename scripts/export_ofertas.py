"""Lê as abas Amazon/Shopee/MercadoLivre/Magalu da planilha do bot (amazon-telegram) e gera
src/data/ofertas.json — o feed que a home do site renderiza no build.

Site público, planilha e credenciais só de leitura por aqui: aceita as credenciais da
service account tanto por arquivo (GOOGLE_CREDENTIALS_FILE, uso local) quanto por
variável de ambiente com o JSON inteiro (GOOGLE_CREDENTIALS_JSON, uso no GitHub Actions
— evita ter que gravar um arquivo de secret manualmente no workflow).
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "src" / "data" / "ofertas.json"

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

WORKSHEETS = {
    "amazon": os.getenv("GOOGLE_WORKSHEET_AMAZON", "Amazon"),
    "shopee": os.getenv("GOOGLE_WORKSHEET_SHOPEE", "Shopee"),
    "mercadolivre": os.getenv("GOOGLE_WORKSHEET_ML", "MercadoLivre"),
    "magalu": os.getenv("GOOGLE_WORKSHEET_MAGALU", "Magalu"),
}

# Segunda linha de defesa: mesmo que HISTORY_RETENTION_DAYS mude no outro repositório,
# o site nunca mostra oferta com mais de N dias.
MAX_AGE_DAYS = int(os.getenv("OFERTAS_MAX_AGE_DAYS", "7"))

NUMERIC_FIELDS = ["price", "original_price", "discount_percent", "rating"]


def _resolve_credentials_path():
    if GOOGLE_CREDENTIALS_JSON:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(GOOGLE_CREDENTIALS_JSON)
        return path
    return GOOGLE_CREDENTIALS_FILE


def _to_number(value):
    # o coletor grava com vírgula decimal ("1199,9"), não ponto.
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _clean_review_count(value):
    # vem como "(93)" ou "(10 mil)" — texto pronto pra exibir, não um número puro.
    if not value:
        return None
    return value.strip().strip("()").replace("\xa0", " ") or None


def _read_worksheet(sheet, platform, worksheet_name):
    try:
        worksheet = sheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        print(f"  aba '{worksheet_name}' não existe ainda — pulando {platform}.")
        return []

    rows = worksheet.get_all_values()
    if not rows:
        return []

    header, data_rows = rows[0], rows[1:]
    items = []
    for row in data_rows:
        item = dict(zip(header, row))
        if not item.get("affiliate_url") or not item.get("title") or not item.get("asin"):
            continue
        for field in NUMERIC_FIELDS:
            item[field] = _to_number(item.get(field))
        if item["price"] is None:
            continue  # sem preço não dá pra mostrar uma oferta de verdade
        item["review_count"] = _clean_review_count(item.get("review_count"))
        item["platform"] = platform
        items.append(item)
    return items


def _dedup_keep_latest(items):
    """Mesma oferta pode ter sido salva em rodadas diferentes dentro da janela de
    retenção — mantém só a linha mais recente por (platform, asin)."""
    latest = {}
    for item in items:
        key = (item["platform"], item["asin"])
        current = latest.get(key)
        if current is None or (item.get("collected_at") or "") > (current.get("collected_at") or ""):
            latest[key] = item
    return list(latest.values())


def _within_max_age(item, cutoff):
    collected_at = item.get("collected_at") or ""
    return collected_at >= cutoff or not collected_at


def main():
    if not GOOGLE_SHEET_ID:
        raise SystemExit("GOOGLE_SHEET_ID não configurado.")

    credentials_path = _resolve_credentials_path()
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)

    all_items = []
    for platform, worksheet_name in WORKSHEETS.items():
        print(f"Lendo aba '{worksheet_name}' ({platform}) ...")
        items = _read_worksheet(sheet, platform, worksheet_name)
        print(f"  {len(items)} linhas.")
        all_items.extend(items)

    deduped = _dedup_keep_latest(all_items)

    cutoff = (datetime.now() - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    fresh = [item for item in deduped if _within_max_age(item, cutoff)]
    fresh.sort(key=lambda item: item.get("collected_at") or "", reverse=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8")

    by_platform = {}
    for item in fresh:
        by_platform[item["platform"]] = by_platform.get(item["platform"], 0) + 1
    print(f"\n{len(fresh)} ofertas exportadas ({len(all_items) - len(deduped)} duplicatas removidas): {by_platform}")
    print(f"-> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
