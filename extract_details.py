#!/usr/bin/env python3
"""
Extrator de eventos do calendário Bernoulli (La Salle).
Consulta a API por intervalo de datas com paginação real,
filtra eventos já concluídos, agrupa por data e salva em JSON.
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

import database  # ← persistência

load_dotenv()

# ── Config ──────────────────────────────────────────────────
BERNOULLI_TOKEN = os.getenv("BERNOULLI_TOKEN", "").strip()

API_BASE = "https://mb4.bernoulli.com.br"
ENDPOINT = f"{API_BASE}/api/calendario/events"

FILTERS = {
    "range": "week",
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


def iso_date(d: datetime) -> str:
    return d.astimezone(BR_TZ).strftime("%Y-%m-%d")


def parse_api_datetime(iso_str: str) -> datetime:
    iso_str = iso_str.replace("Z", "+00:00")
    return datetime.fromisoformat(iso_str)


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
        "User-Agent": "HermesBot/2.0",
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

        log(f"  → {len(data)} eventos recebidos (total {total_items}, páginas {total_pages})")
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

    log(f"Total único de eventos: {len(unique)}")
    return unique


def transform_event(ev: dict) -> dict:
    start_dt = parse_api_datetime(ev.get("startDate", ""))
    date_br = iso_date(start_dt)

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
            links.append(f"{API_BASE}/api/storage/download/{blob}")

    return {
        "id": ev.get("id"),
        "date": date_br,
        "time": time_str,
        "title": ev.get("title", "Sem título"),
        "type": ev.get("type", "event"),
        "description": clean_html(ev.get("description", "")),
        "author": author,
        "links": links,
    }


def build_agenda(events: list[dict]) -> dict:
    by_date = defaultdict(list)
    for ev in events:
        by_date[ev["date"]].append(ev)

    sorted_dates = sorted(by_date.keys())
    agenda = {}
    for d in sorted_dates:
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

    # ── FILTRA CONCLUÍDOS ───────────────────────────────────
    skipped = 0
    transformed = []
    for ev in raw_events:
        eid = ev.get("id")
        if database.is_completed(eid):
            skipped += 1
            continue
        transformed.append(transform_event(ev))

    log(f"Eventos filtrados (já concluídos): {skipped}")

    agenda = build_agenda(transformed)

    out_file = "agenda_events_by_date.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

    total_events = sum(len(v) for v in agenda.values())
    log(f"Agenda salva em '{out_file}': {len(agenda)} dias, {total_events} eventos pendentes.")


if __name__ == "__main__":
    main()
