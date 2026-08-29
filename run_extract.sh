#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="/home/vboxuser/agenda/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="cron.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Iniciando pipeline…" >> "$LOG_FILE"

source "$VENV_PATH/bin/activate"

# 1) Extração (já filtra concluídos automaticamente)
echo "[$TIMESTAMP] Executando extract_details.py…" >> "$LOG_FILE"
if python3 extract_details.py >> "$LOG_FILE" 2>&1; then
    echo "[$TIMESTAMP] Extração OK." >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] ERRO na extração. Abortando." >> "$LOG_FILE"
    exit 1
fi

# 2) Notificação
echo "[$TIMESTAMP] Executando notify_telegram.py…" >> "$LOG_FILE"
if python3 notify_telegram.py >> "$LOG_FILE" 2>&1; then
    echo "[$TIMESTAMP] Notificação OK." >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] ERRO no envio Telegram." >> "$LOG_FILE"
    exit 1
fi

echo "[$TIMESTAMP] Pipeline concluído com sucesso." >> "$LOG_FILE"
