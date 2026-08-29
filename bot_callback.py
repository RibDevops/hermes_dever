#!/usr/bin/env python3
"""
Bot de callback do Telegram (long polling).
Fica rodando em background recebendo cliques no botão "✅ Concluir"
e persiste no SQLite.

Como rodar:
    nohup python3 bot_callback.py > bot.log 2>&1 &
    # ou use systemd, screen, tmux
"""

import os
import sys
import time
import json
from datetime import datetime

import requests
from dotenv import load_dotenv

import database

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TIMEOUT = 30
POLL_INTERVAL = 2  # segundos entre polls


def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)


def api_method(method: str, payload: dict = None) -> dict:
    url = f"{API_URL}/{method}"
    try:
        resp = requests.post(url, json=payload or {}, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        log(f"Erro API {method}: {exc}")
        return {"ok": False}


def answer_callback(query_id: str, text: str = "Concluído!"):
    """Mostra o toast "Concluído!" no Telegram."""
    api_method("answerCallbackQuery", {
        "callback_query_id": query_id,
        "text": text,
        "show_alert": False,
    })


def edit_button_to_done(chat_id: int, message_id: int):
    """Atualiza o botão para mostrar '✅ Já concluído' (desabilitado)."""
    api_method("editMessageReplyMarkup", {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": json.dumps({
            "inline_keyboard": [
                [{"text": "✅ Já concluído", "callback_data": "done"}]
            ]
        }),
    })


def process_update(update: dict):
    callback = update.get("callback_query")
    if not callback:
        return

    query_id = callback["id"]
    event_id = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not event_id or event_id == "done":
        answer_callback(query_id, "Já registrado.")
        return

    if database.is_completed(event_id):
        answer_callback(query_id, "Já estava concluído.")
        if chat_id and message_id:
            edit_button_to_done(chat_id, message_id)
        return

    if database.mark_completed(event_id):
        log(f"Evento concluído: {event_id}")
        answer_callback(query_id, "✅ Marcado como concluído!")
        if chat_id and message_id:
            edit_button_to_done(chat_id, message_id)
    else:
        answer_callback(query_id, "Já estava concluído.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        log("ERRO: TELEGRAM_BOT_TOKEN não definido.")
        sys.exit(1)

    database.init_db()
    log("Bot de callback iniciado. Aguardando cliques…")

    offset = 0
    while True:
        try:
            result = api_method("getUpdates", {
                "offset": offset,
                "limit": 100,
                "timeout": 10,
            })

            if not result.get("ok"):
                time.sleep(POLL_INTERVAL)
                continue

            updates = result.get("result", [])
            for up in updates:
                offset = max(offset, up["update_id"] + 1)
                process_update(up)

        except KeyboardInterrupt:
            log("Encerrando bot…")
            break
        except Exception as exc:
            log(f"Erro inesperado: {exc}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
