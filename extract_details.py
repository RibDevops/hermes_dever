#!/usr/bin/env python3
"""
Extrator de eventos do calendário Bernoulli (La Salle).
CORREÇÕES:
  1. API_BASE = api.bernoulli.com.br
  2. Remove range=week que filtrava resultados
  3. EXPANDE eventos recorrentes/longos para TODOS os dias entre startDate e endDate
  4. Agrupa corretamente por data local (Brasília)
"""

import os
import sys
import json
import re
import html
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import requests
from dotenv import load_dotenv

import database

load_dotenv()

BERNOULLI_TOKEN = os.getenv("BERNOULLI_TOKEN", "").strip()
API_BASE = "https://api.bernoulli.com.br"
ENDPOINT = f"{API_BASE}/api/calendario/events"
PORTAL_BASE = "https://mb4.bernoulli.com.br"

FILTERS = {
    # REMOVIDO: "range": "week"  — estava filtrando resultados!
    "status": "published",
    "grade": "12",
    "class": "109576",
    "profile": "13",
    "school": "1846",
    "ignoreAudience": "false",
    "sortBy": "startDate",
    "sortOrder": "asc",
}

LIMIT = 100
TIMEOUT = 30
BR_TZ = timezone(timedelta(hours=-3))


def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)


def parse_api_datetime(iso_str: str) -> datetime:
    iso_str = iso_str.replace("Z", "+00:00")
    return datetime.fromisoformat(iso_str)


def to_br_date(d: datetime) -> str:
    """Converte datetime aware para string YYYY-MM-DD em Brasília."""
    return d.astimezone(BR_TZ).strftime("%Y-%m-%d")


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_all_events(start_date: str, end_date: str) -> list[dict]:
    if not BERNOULLI_TOKEN:
        log("ERRO: BERNOULLI_TOKEN não definido no .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {BERNOULLI_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Origin": PORTAL_BASE,
        "Referer": f"{PORTAL_BASE}/",
    }

    all_events = []
    page = 1

    while True:
        params = {
            **FILTERS,
            "startDate": start_date,
            "endDate": end_date,
            "page": page,
            "limit": LIMIT,
        }

        log(f"Buscando página {page} ({start_date} → {end_date}) …")
        try:
            resp = requests.get(ENDPOINT, headers=headers, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log(f"ERRO na requisição: {exc}")
            sys.exit(1)

        payload = resp.json()
        data = payload.get("data", [])
        meta = payload.get("meta", {})
        total_pages = meta.get("totalPages", 1)
        total_items = meta.get("total", 0)

        log(f"  → {len(data)} eventos (total {total_items}, páginas {total_pages})")
        all_events.extend(data)

        if page >= total_pages or not data:
            break
        page += 1

    # Remove duplicados por id
    seen = set()
    unique = []
    for ev in all_events:
        eid = ev.get("id")
        if eid and eid not in seen:
            seen.add(eid)
            unique.append(ev)

    log(f"Total único de eventos da API: {len(unique)}")
    return unique


def transform_event(ev: dict) -> dict:
    """Extrai dados úteis de um evento da API."""
    start_time = ev.get("startTime", "")[:5]
    end_time = ev.get("endTime", "")[:5]
    time_str = f"{start_time} – {end_time}" if end_time and end_time != start_time else start_time

    contact = ev.get("contact", {})
    author = contact.get("name", "Desconhecido")

    attachments = ev.get("attachments", [])
    links = []
    for att in attachments:
        blob = att.get("blobName", "")
        if blob:
            links.append(f"{PORTAL_BASE}/api/storage/download/{blob}")

    return {
        "id": ev.get("id"),
        "title": ev.get("title", "Sem título"),
        "type": ev.get("type", "event"),
        "description": clean_html(ev.get("description", "")),
        "author": author,
        "links": links,
        "time": time_str,
        # Guardamos as datas brutas para expansão
        "_start_dt": parse_api_datetime(ev.get("startDate", "")),
        "_end_dt": parse_api_datetime(ev.get("endDate", "")),
    }


def expand_event_to_days(ev: dict, query_start: str, query_end: str) -> list[tuple[str, dict]]:
    """
    Expande um evento para todos os dias entre startDate e endDate
    que caem dentro do intervalo de busca.
    Retorna lista de (data_str, evento_copia).
    """
    start_dt = ev["_start_dt"]
    end_dt = ev["_end_dt"]
    q_start = datetime.strptime(query_start, "%Y-%m-%d").replace(tzinfo=BR_TZ)
    q_end = datetime.strptime(query_end, "%Y-%m-%d").replace(tzinfo=BR_TZ) + timedelta(days=1)

    # Limita o range do evento ao intervalo de busca
    effective_start = max(start_dt, q_start)
    effective_end = min(end_dt, q_end)

    if effective_start > effective_end:
        return []

    results = []
    current = effective_start
    while current <= effective_end:
        date_str = to_br_date(current)
        # Cria cópia sem os campos internos
        copy = {k: v for k, v in ev.items() if not k.startswith("_")}
        copy["date"] = date_str
        results.append((date_str, copy))
        current += timedelta(days=1)

    return results


def build_agenda(expanded_events: list[tuple[str, dict]]) -> dict:
    """Agrupa eventos por data, remove duplicatas por ID no mesmo dia, ordena."""
    by_date = defaultdict(list)
    seen_per_day = defaultdict(set)

    for date_str, ev in expanded_events:
        eid = ev["id"]
        if eid in seen_per_day[date_str]:
            continue  # evita duplicata no mesmo dia
        seen_per_day[date_str].add(eid)
        by_date[date_str].append(ev)

    sorted_dates = sorted(by_date.keys())
    agenda = {}
    for d in sorted_dates:
        # Ordena por horário dentro do dia
        day_events = sorted(by_date[d], key=lambda x: x["time"])
        agenda[d] = day_events
    return agenda


def main():
    today = datetime.now(BR_TZ)
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=60)).strftime("%Y-%m-%d")

    log(f"Iniciando extração: {start} → {end}")
    raw_events = fetch_all_events(start, end)

    if not raw_events:
        log("Nenhum evento encontrado no intervalo.")
        with open("agenda_events_by_date.json", "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return

    # ── TRANSFORMA E EXPANDE ──────────────────────────────────
    skipped_completed = 0
    expanded = []

    for ev in raw_events:
        eid = ev.get("id")
        if database.is_completed(eid):
            skipped_completed += 1
            continue

        transformed = transform_event(ev)
        day_entries = expand_event_to_days(transformed, start, end)
        expanded.extend(day_entries)

    log(f"Eventos concluídos (filtrados): {skipped_completed}")
    log(f"Eventos expandidos em entradas de dia: {len(expanded)}")

    agenda = build_agenda(expanded)

    # Log de resumo por dia
    for d in sorted(agenda.keys()):
        log(f"  {d}: {len(agenda[d])} evento(s)")

    out_file = "agenda_events_by_date.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

    total_events = sum(len(v) for v in agenda.values())
    log(f"Agenda salva: {len(agenda)} dias, {total_events} eventos pendentes.")


if __name__ == "__main__":
    main()
