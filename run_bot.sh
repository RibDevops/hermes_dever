#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="/home/vboxuser/agenda/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source "$VENV_PATH/bin/activate"

LOG_FILE="bot.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Iniciando bot_callback.py…" >> "$LOG_FILE"
nohup python3 bot_callback.py >> "$LOG_FILE" 2>&1 &
echo $! > bot.pid

echo "Bot iniciado em background (PID: $(cat bot.pid))"
echo "Logs: tail -f $SCRIPT_DIR/bot.log"
