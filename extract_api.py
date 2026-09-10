#!/usr/bin/env python3
"""
Script de extração de agenda usando API REST do Bernoulli.
- Extrai eventos da API api.bernoulli.com.br
- Salva em agenda_details.json com campos: date, title, description, download_url
- Adiciona campo 'completed' (True se tiver link PDF)
- Inicia dashboard Flask no navegador
- Envia notificação no Telegram ao concluir
"""

import json
import os
import re
import sys
import threading
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path  # ADICIONADO

import requests
from flask import Flask, render_template, jsonify

# ===================== CONFIGURAÇÕES =====================

# Base da API
API_BASE = "https://api.bernoulli.com.br"
ENDPOINT = f"{API_BASE}/api/calendario/events"

# Filtros
FILTERS = {
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

# Telegram config (seus dados)
TELEGRAM_BOT_TOKEN = "8982897650:AAGaTtKqDQb-3AGzE2Ejrj82hGFGf5y64l0"
TELEGRAM_CHAT_ID = "-5380461608"

# Output file
OUTPUT_FILE = "agenda_details.json"

# Flask dashboard
app = Flask(__name__)
app.config["RESULTADOS"] = []
app.config["STATUS_EVENTOS"] = {}  # Armazena {id_evento: completed}
# Carregar status persistente ao iniciar
status_file = Path("status_eventos.json")
if status_file.is_file():
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            app.config["STATUS_EVENTOS"] = json.load(f)
        log(f"✅ Status persistente carregado: {len(app.config['STATUS_EVENTOS'])} eventos")
    except Exception as e:
        log(f"⚠️  Erro ao carregar status persistente: {e}")


# ===================== HELPERS =====================

def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}", flush=True)


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_api_datetime(iso_str: str) -> datetime:
    iso_str = iso_str.replace("Z", "+00:00")
    return datetime.fromisoformat(iso_str)


def to_br_date(d: datetime) -> str:
    return d.astimezone(BR_TZ).strftime("%Y-%m-%d")


def get_bernielli_token() -> str:
    """Lê token do .env ou variável de ambiente, com sistema de fallback."""
    # Lista de nomes de tokens para tentar (em ordem de prioridade)
    token_configs = [
        {"name": "BERNOULLI_TOKEN", "from_file": True},
        {"name": "BERNOULLI_TOKEN_BACKUP", "from_file": True},
        {"name": "BERNOULLI_TOKEN_2", "from_env": True},
    ]
    
    for config in token_configs:
        token = None
        
        # Tentar de variável de ambiente primeiro (se especificado)
        if config.get("from_env"):
            token = os.getenv(config["name"])
        
        # Se não tem em env, tentar ler do .env
        if not token and config.get("from_file"):
            try:
                with open("/home/vboxuser/agenda/.env", "r") as f:
                    for line in f:
                        if line.startswith(f"{config['name']}="):
                            token = line.strip().split("=", 1)[1].strip('"').strip("'")
                            break
            except FileNotFoundError:
                pass
        
        if token:
            log(f"✅ Token carregado via {config['name']}")
            return token
    
    log("⚠️  Nenhum token encontrado nas configurações!")
    log("   Configure um token em BERNOULLI_TOKEN no .env ou variáveis de ambiente")
    sys.exit(1)


def fetch_all_events(start_date: str, end_date: str) -> list[dict]:
    token = get_bernielli_token()
    if not token:
        log("⚠️  BERNOULLI_TOKEN não encontrado em ambiente nem em .env")
        log("   Defina a variável de ambiente BERNOULLI_TOKEN ou preencha o .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Origin": "https://mb4.bernoulli.com.br",
        "Referer": "https://mb4.bernoulli.com.br/",
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

        log(f"Buscando página {page} …")
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

    seen = set()
    unique = []
    for ev in all_events:
        eid = ev.get("id")
        if eid and eid not in seen:
            seen.add(eid)
            unique.append(ev)

    log(f"Total único de eventos da API: {len(unique)}")
    return unique


def find_pdf_attachment(event: dict) -> str | None:
    attachments = event.get("attachments", [])
    for att in attachments:
        blob_name = att.get("blobName", "")
        file_type = att.get("fileType", "")
        file_name = att.get("fileName", "")

        is_pdf = False
        if file_type and "pdf" in file_type.lower():
            is_pdf = True
        if blob_name and ".pdf" in blob_name.lower():
            is_pdf = True
        if file_name and ".pdf" in file_name.lower():
            is_pdf = True

        if is_pdf:
            base_download = "https://prodgestaoacademica.blob.core.windows.net/calendar/"
            download_url = base_download + blob_name
            return download_url

    return None


def transform_event(ev: dict) -> dict:
    start_dt = parse_api_datetime(ev.get("startDate", ""))
    end_dt = parse_api_datetime(ev.get("endDate", ""))
    date_str = to_br_date(start_dt)
    title = ev.get("title", "Sem título")
    description = clean_html(ev.get("description", ""))
    download_url = find_pdf_attachment(ev)

    return {
        "id": ev.get("id"),
        "date": date_str,
        "title": title,
        "description": description,
        "download_url": download_url or "",
        "completed": bool(download_url),  # True se tem PDF
        "_start_dt": start_dt,
        "_end_dt": end_dt,
    }


# ===================== PROCESSAMENTO =====================

def salvar_json(resultado: dict):
    """Salva JSON e atualiza dashboard."""
    resultado_ordenado = dict(sorted(resultado.items(), key=lambda x: x[1]["date"]))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(resultado_ordenado, f, ensure_ascii=False, indent=2)

    # Atualizar dashboard
    app.config["RESULTADOS"] = list(resultado_ordenado.values())
    log(f"JSON salvo: {OUTPUT_FILE} ({len(resultado_ordenado)} eventos)")


def enviar_telegram(mensagem: str):
    """Envia mensagem via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown",
    }

    try:
        requests.post(url, json=payload, timeout=15)
        log("📱 Notificação Telegram enviada")
    except Exception as e:
        log(f"⚠️  Erro ao enviar Telegram: {e}")


# ===================== FLASK DASHBOARD =====================

@app.route("/")
def index():
    resultados = app.config.get("RESULTADOS", [])
    resultados_ordenados = sorted(resultados, key=lambda x: x.get("date", ""))
    total = len(resultados_ordenados)
    completos = sum(1 for r in resultados_ordenados if r.get("completed"))
    pendentes = total - completos
    return render_template(
        "dashboard.html",
        resultados=resultados_ordenados,
        total=total,
        completos=completos,
        pendentes=pendentes,
    )


@ app.route("/api/status")
def api_status():
    resultados = app.config.get("RESULTADOS", [])
    total = len(resultados)
    completos = sum(1 for r in resultados if r.get("completed"))
    return jsonify({"total": total, "completos": completos, "pendentes": total - completos})


# NOVO ENDPOINT: Marcar evento como concluído
@app.route("/api/marcar-como-feito", methods=["POST"])
def marcar_comofeito():
    dados = request.get_json()
    evento_id = dados.get("id") if dados else None
    status = dados.get("status", False) if dados else False

    if not evento_id:
        return jsonify({"erro": "ID do evento não fornecido"}), 400

    # Atualizar status na configuração Flask (persistente enquanto o servidor roda)
    app.config["STATUS_EVENTOS"][evento_id] = status

    # Salvar em arquivo JSON para persistência entre reinicializações
    try:
        with open("status_eventos.json", "w", encoding="utf-8") as f:
            json.dump(app.config["STATUS_EVENTOS"], f, ensure_ascii=False, indent=2)
        log(f"💾 Status salvo em status_eventos.json: {evento_id} = {status}")
    except Exception as e:
        log(f"⚠️  Erro ao salvar status: {e}")

    # Retornar status atualizado
    status_atual = app.config["STATUS_EVENTOS"].get(evento_id, False)
    return jsonify({
        "sucesso": True,
        "evento_id": evento_id,
        "status": status_atual,
        "mensagem": "Evento marcado como concluído" if status_atual else "Evento marcado como pendente"
    })


# ===================== RODAR ====================

def main():
    log("=== Iniciando extração de agenda ===")

    today = datetime.now(BR_TZ)
    start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=60)).strftime("%Y-%m-%d")

    log(f"Intervalo: {start} → {end}")

    raw_events = fetch_all_events(start, end)

    if not raw_events:
        log("Nenhum evento encontrado.")
        salvar_json({})
        # Enviar Telegram mesmo sem eventos
        enviar_telegram("✅ Extração da agenda conclúida! Nenhum novo evento encontrado no intervalo.")
        return

    # Transformar eventos
    expanded = [transform_event(ev) for ev in raw_events]

    # Agrupar por data e remover duplicatas
    by_date = defaultdict(list)
    seen_per_day = defaultdict(set)

    for ev in expanded:
        date_str = ev["date"]
        eid = ev.get("id")
        if eid in seen_per_day[date_str]:
            continue
        seen_per_day[date_str].add(eid)
        by_date[date_str].append(ev)

    # Preparar resultado final
    resultado = {}
    for d in sorted(by_date.keys()):
        for ev in sorted(by_date[d], key=lambda x: x.get("_start_dt", datetime.min)):
            key = ev["id"]
            if key not in resultado:
                resultado[key] = {
                    "date": ev["date"],
                    "title": ev["title"],
                    "description": ev["description"],
                    "download_url": ev["download_url"],
                    "completed": ev["completed"],
                }

    # Salvar JSON
    salvar_json(resultado)

    # Contar completos/pendentes
    total_completos = sum(1 for v in resultado.values() if v.get("completed"))
    total_pendentes = len(resultado) - total_completos

    # Enviar notificação Telegram
    msg = (f"✅ Extração concluída! {len(resultado)} eventos encontrados.\n"
           f"📎 {total_completos} têm links PDF disponíveis.\n"
           f"⏳ {total_pendentes} sem link PDF direto.")
    enviar_telegram(msg)

    log(f"=== Extração finalizada: {len(resultado)} eventos em {OUTPUT_FILE} ===")


if __name__ == "__main__":
    # 1. Executar extração
    main()

    # 2. Iniciar dashboard Flask em thread separada
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False), daemon=True)
    flask_thread.start()

    print("\n🌐 Dashboard disponível em: http://localhost:5000")
    print("📊 Pressione Ctrl+C para sair (o dashboard continuará rodando).")

    # Manter processo vivo
    try:
        while True:
            import time
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        log("Encerrando script...")
        sys.exit(0)