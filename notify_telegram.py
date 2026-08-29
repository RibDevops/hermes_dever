#!/usr/bin/env python3
"""
Lê agenda_events_by_date.json e envia uma mensagem por dia
ao Telegram com botão "✅ Concluir" para cada dever.
"""

import os
import sys
import json
import re
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

MAX_MSG_LEN = 3800
TIMEOUT = 30


def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)


def escape_md(text: str) -> str:
    return re.sub(r"([_\*\[\]\(\)~`>\#\+\-=|{}\.!])", r"\\\1", str(text))


def truncate(text: str, max_len: int = 600) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + " …"


def format_event(ev: dict, idx: int) -> tuple[str, dict]:
    """Retorna (texto_markdown, reply_markup_inline)."""
    title = escape_md(ev["title"])
    time_ = escape_md(ev["time"])
    ev_type = escape_md(ev["type"].upper())
    author = escape_md(ev["author"])
    desc = escape_md(truncate(ev["description"], 500))
    eid = ev["id"]

    lines = [
        f"*🕐 {time_}*  \|  _{ev_type}_",
        f"*{title}*",
    ]
    if desc:
        lines.append(f"{desc}")
    lines.append(f"👤 {author}")

    if ev["links"]:
        for i, link in enumerate(ev["links"][:3], 1):
            lines.append(f"📎 [Anexo {i}]({link})")

    text = "\n".join(lines)

    # Botão inline para marcar como concluído
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ Concluir", "callback_data": eid}]
        ]
    }

    return text, reply_markup


def format_day(date_str: str, events: list[dict]) -> tuple[str, list[dict]]:
    """Retorna (texto_cabeçalho, lista_de_eventos_formatados)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][dt.weekday()]
    header = f"📅 *{escape_md(weekday)}, {dt.strftime('%d/%m/%Y')}*\n\n"
    return header, events


def send_message(text: str, reply_markup: dict = None) -> dict:
    """Envia mensagem. Retorna dict da resposta do Telegram."""
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        log(f"Falha ao enviar: {exc}")
        return {"ok": False}


def split_events(events: list[dict], header: str) -> list[tuple[str, list[dict]]]:
    """Divide eventos em partes que caibam no limite de caracteres."""
    parts = []
    current_text = header
    current_events = []

    for ev in events:
        ev_text, markup = format_event(ev, 0)
        block = ev_text + "\n\n"
        if len(current_text) + len(block) > MAX_MSG_LEN and current_events:
            parts.append((current_text, current_events))
            current_text = header + block
            current_events = [(ev_text, markup)]
        else:
            current_text += block
            current_events.append((ev_text, markup))

    if current_events:
        parts.append((current_text, current_events))

    return parts


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
    sent_days = 0
    total_msgs = 0

    for date_str in sorted(agenda.keys()):
        events = agenda[date_str]
        header, ev_list = format_day(date_str, events)

        # Envia cabeçalho do dia
        send_message(header)

        # Envia cada evento como mensagem separada (melhor para botões inline)
        for ev in ev_list:
            ev_text, markup = format_event(ev, 0)
            result = send_message(ev_text, reply_markup=markup)
            if result.get("ok"):
                total_msgs += 1
            else:
                log(f"Falha ao enviar evento {ev['id']}")

        sent_days += 1

    log(f"Concluído. {sent_days}/{total_days} dias, {total_msgs} mensagens enviadas.")


if __name__ == "__main__":
    main()
