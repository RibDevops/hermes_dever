#!/usr/bin/env python3
"""
Lê agenda_events_by_date.json e envia UM resumo por dia ao Telegram.
Cada dia é uma única mensagem HTML com botões inline para concluir.
Rate limiting + retry com backoff para evitar 429.
"""

import os
import sys
import json
import re
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

TIMEOUT = 30
RATE_LIMIT_DELAY = 1.2       # segundos entre mensagens (um pouco mais seguro)
MAX_RETRIES = 5
BASE_RETRY_DELAY = 3
MAX_MSG_LEN = 3800           # limite seguro do Telegram
MAX_BUTTONS_PER_MSG = 10     # máximo de botões inline por mensagem


def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)


def escape_html(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + " …"


def format_event_inline(ev: dict, idx: int) -> str:
    """Formata um evento como linha de texto HTML (sem botão, só lista)."""
    title = escape_html(ev["title"])
    time_ = escape_html(ev["time"])
    ev_type = escape_html(ev["type"].upper())
    author = escape_html(ev["author"])
    desc = escape_html(truncate(ev["description"], 350))

    emoji = {"task": "📝", "assignment": "📚", "assessment": "📝",
             "event": "📅", "online_class": "💻"}.get(ev["type"], "📌")

    lines = [f"<b>{idx}. {emoji} {title}</b>  <code>{time_}</code>  <i>({ev_type})</i>"]
    if desc:
        lines.append(f"   {desc}")
    lines.append(f"   👤 <i>{author}</i>")

    if ev["links"]:
        links_str = "  ".join(
            f'<a href="{l}">📎{i+1}</a>'
            for i, l in enumerate(ev["links"][:3])
        )
        lines.append(f"   {links_str}")

    return "\n".join(lines)


def format_day_message(date_str: str, events: list[dict], start_idx: int = 1) -> tuple[str, list]:
    """
    Formata uma mensagem de dia. Retorna (texto_html, lista_de_botoes).
    start_idx: número inicial dos eventos (para quando divide em partes).
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    weekday = weekdays[dt.weekday()]

    header = f"📅 <b>{weekday}, {dt.strftime('%d/%m/%Y')}</b>\n"
    header += f"<i>{len(events)} tarefa(s) para hoje</i>\n\n"

    body_parts = []
    buttons = []

    for i, ev in enumerate(events, start=start_idx):
        body_parts.append(format_event_inline(ev, i))
        # Botão para concluir este evento
        buttons.append({
            "text": f"✅ {i}. Concluir",
            "callback_data": ev["id"]
        })

    body = "\n\n".join(body_parts)
    full_text = header + body

    return full_text, buttons


def split_day(date_str: str, events: list[dict]) -> list[tuple[str, list]]:
    """
    Divide os eventos de um dia em partes que caibam no limite de chars
    e no limite de botões por mensagem.
    """
    parts = []
    current_events = []
    current_text = ""
    current_buttons = []
    idx = 1

    for ev in events:
        ev_text = format_event_inline(ev, idx)
        # Estimativa: texto do evento + botão
        estimated_len = len(ev_text) + 50

        if (len(current_text) + estimated_len > MAX_MSG_LEN or
                len(current_buttons) >= MAX_BUTTONS_PER_MSG):
            if current_events:
                text, _ = format_day_message(date_str, current_events, start_idx=idx - len(current_events))
                parts.append((text, current_buttons))
            current_events = [ev]
            current_buttons = [{"text": f"✅ {idx}. Concluir", "callback_data": ev["id"]}]
            current_text = ev_text
        else:
            current_events.append(ev)
            current_buttons.append({"text": f"✅ {idx}. Concluir", "callback_data": ev["id"]})
            current_text += ev_text

        idx += 1

    if current_events:
        text, _ = format_day_message(date_str, current_events, start_idx=idx - len(current_events))
        parts.append((text, current_buttons))

    return parts


def send_message(text: str, reply_markup: dict = None, retries: int = 0) -> dict:
    """Envia mensagem com retry e backoff para 429."""
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)

        if resp.status_code == 429:
            if retries < MAX_RETRIES:
                retry_after = int(resp.headers.get("Retry-After", BASE_RETRY_DELAY * (2 ** retries)))
                delay = max(retry_after, BASE_RETRY_DELAY * (2 ** retries))
                log(f"Rate limit (429). Aguardando {delay}s… retry {retries+1}/{MAX_RETRIES}")
                time.sleep(delay)
                return send_message(text, reply_markup, retries + 1)
            else:
                log(f"Rate limit persistente após {MAX_RETRIES} tentativas.")
                return {"ok": False, "error": "Max retries exceeded"}

        resp.raise_for_status()
        return resp.json()

    except requests.HTTPError as exc:
        if resp.status_code == 400:
            log(f"Bad Request (400). Texto: {text[:400]}…")
        log(f"HTTP Error {resp.status_code}: {exc}")
        return {"ok": False, "error": str(exc)}
    except requests.RequestException as exc:
        log(f"Falha de rede: {exc}")
        return {"ok": False, "error": str(exc)}


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("ERRO: credenciais Telegram não definidas.")
        sys.exit(1)

    if not os.path.exists("agenda_events_by_date.json"):
        log("ERRO: agenda_events_by_date.json não encontrado.")
        sys.exit(1)

    with open("agenda_events_by_date.json", "r", encoding="utf-8") as f:
        agenda = json.load(f)

    if not agenda:
        log("Agenda vazia. Nada a enviar.")
        return

    total_days = len(agenda)
    sent_msgs = 0
    failed_msgs = 0

    for date_str in sorted(agenda.keys()):
        events = agenda[date_str]

        # Divide o dia em partes se necessário
        parts = split_day(date_str, events)

        for part_text, buttons in parts:
            reply_markup = {"inline_keyboard": [[b] for b in buttons]}  # um botão por linha
            result = send_message(part_text, reply_markup=reply_markup)
            if result.get("ok"):
                sent_msgs += 1
            else:
                log(f"Falha ao enviar parte do dia {date_str}")
                failed_msgs += 1
            time.sleep(RATE_LIMIT_DELAY)

    log(f"Concluído. {sent_msgs} mensagem(ns) enviada(s), {failed_msgs} falha(s). {total_days} dia(s).")

    if failed_msgs > 0:
        log("DICA: Se ainda houver falhas 429, aumente RATE_LIMIT_DELAY para 2.0 ou mais.")


if __name__ == "__main__":
    main()
