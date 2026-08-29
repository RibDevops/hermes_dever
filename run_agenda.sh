#!/usr/bin/env bash
# run_agenda.sh – gera agenda.json a partir do HTML salvo

HTML_FILE="/home/vboxuser/Downloads/agenda/calendario.html"
OUT_FILE="/home/vboxuser/agenda/agenda.json"

# Ativa o virtualenv que contém as dependências
source "$HOME/.hermes/venv/bin/activate"

# Executa o parser e grava o JSON
python "$HOME/agenda/parse_agenda.py" "$HTML_FILE" > "$OUT_FILE"

# Registra a execução
echo "$(date '+%Y-%m-%d %H:%M:%S') – agenda gerada" >> "$HOME/agenda/cron.log"

# Desativa o virtualenv
deactivate