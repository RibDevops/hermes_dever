#!/usr/bin/env python3
"""
notify_telegram.py
    • Lê o arquivo agenda_events_by_date.json (gerado por extract_details.py)
    • Para cada dia cria uma mensagem contendo:
        – Data (dd/mm/aaaa)
        – Lista de eventos com: título, horário, descrição e link de download (se houver)
    • Envia cada mensagem separadamente ao Telegram usando o Bot Token e Chat ID
      que estão armazenados em telegram_cfg.json (formato:
        {
            "token": "8982897650:AAGaTtKqDQb-3AGzE2Ejrj82hGFGf5y64l0",
            "chat_id": -5380461608
        })
    • Usa a API HTTP do Telegram (método sendMessage) – não depende de
      nenhum módulo externos além do stdlib.
"""

import json
import pathlib
import sys
import urllib.request

# ---------- Carrega credenciais do Telegram ----------
CONFIG_PATH = pathlib.Path("/home/vboxuser/agenda/telegram_cfg.json")
if not CONFIG_PATH.is_file():
    sys.stderr.write("Arquivo de configuração telegram_cfg.json não encontrado.\n")
    sys.exit(1)

try:
    cfg_content = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    BOT_TOKEN = cfg_content["token"]
    CHAT_ID   = str(cfg_content["chat_id"])   # Telegram aceita string numérica
except (KeyError, json.JSONDecodeError) as e:
    sys.stderr.write(f"Configuração inválida em telegram_cfg.json: {e}\n")
    sys.exit(1)

# ---------- Função para enviar mensagem ----------
def telegram_send(text: str) -> None:
    """
    Envia *text* para o chat especificado via método HTTP simples.
    O Telegram aceita mensagens até 4096 caracteres; se o texto for maior,
    ele será dividido em blocos menores.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Telegram permite parse_mode=MarkdownV2 ou HTML – aqui usamos MarkdownV2
    payload = {
        "chat_id": CHAT_ID,
        "text":    text,
        "parse_mode": "MarkdownV2"
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Telegram API returned status {resp.status}")
    except Exception as exc:
        sys.stderr.write(f"Erro ao enviar mensagem ao Telegram: {exc}\n")

# ---------- Monta a mensagem por dia ----------
def build_daily_message(date: str, events: list[dict]) -> str:
    """
    Recebe a data já formatada (dd/mm/aaaa) e a lista de eventos.
    Retorna uma string pronta para ser enviada ao Telegram usando MarkdownV2.
    """
    lines = [f"*{date}*", ""]  # título da data em negrito

    for ev in events:
        title   = ev.get("title", "Sem título")
        time    = ev.get("time", "")
        desc    = ev.get("description", "")
        dl_url  = ev.get("download_url")

        # Construção da linha do evento
        line = f"{time} – *{title}*"
        if desc:
            line += f": {desc}"
        if dl_url:
            # Marca o link como clickable no MarkdownV2 (escapando pontos e parênteses)
            esc_url = dl_url.replace(".", r"\.").replace("(", r"\(").replace(")", r"\)")
            line += f" [🔗]({esc_url})"
        lines.append(line)

    # Garante que não excedamos 4096 caracteres (limite do Telegram)
    full_msg = "\n".join(lines)
    if len(full_msg) > 4096:
        # Divide em blocos de até 4000 caracteres (um pouco de margem)
        chunks = [full_msg[i:i+4000] for i in range(0, len(full_msg), 4000)]
        for chunk in chunks:
            telegram_send(chunk + "\n")   # newline garante que o Telegram trate como continuação
    else:
        telegram_send(full_msg)

# ---------- Main ----------
def main() -> None:
    json_path = pathlib.Path("/home/vboxuser/agenda/agenda_events_by_date.json")
    if not json_path.is_file():
        sys.stderr.write("agenda_events_by_date.json não encontrado – nada a enviar.\n")
        sys.exit(1)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Falha ao ler agenda_events_by_date.json: {e}\n")
        sys.exit(1)

    # O JSON gerado tem a estrutura:
    # [
    #   {"date": "23/03/2026", "events": [{...}, {...}, ...]},
    #   {"date": "24/03/2026", "events": [...]},
    #   ...
    # ]
    for entry in data:
        date   = entry.get("date", "Data desconhecida")
        events = entry.get("events", [])
        if not events:
            continue          # ignora dias sem eventos
        message = build_daily_message(date, events)
        telegram_send(message)

if __name__ == "__main__":
    main()