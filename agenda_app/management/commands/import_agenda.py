import logging
import os
import random
import time
from datetime import date, timedelta

import requests
from django.core.management.base import BaseCommand

from agenda_app.models import AgendaItem, PortalCredential, Turma

logger = logging.getLogger("import_agenda")
API_URL = os.getenv("BERNOULLI_API_URL",
                    "https://api.bernoulli.com.br/api/calendario/events")
LOGIN_URL = os.getenv("BERNOULLI_LOGIN_URL",
                      "https://api.bernoulli.com.br/api/autenticacao/login")
DIAS = int(os.getenv("DIAS_INTERVALO", "89"))
FIELD_USER = os.getenv("BERNOULLI_LOGIN_FIELD_USER", "login")
FIELD_PASS = os.getenv("BERNOULLI_LOGIN_FIELD_PASS", "senha")

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Plataforma": "2",
    "Origin": "https://mb4.bernoulli.com.br",
    "Referer": "https://mb4.bernoulli.com.br/",
    "Front-Version": "4.25.103",
}


def autenticar(cred):
    s = requests.Session()
    s.headers.update(BASE_HEADERS)
    r = s.post(LOGIN_URL, json={"email": cred.usuario_portal, "password": cred.senha_portal}, timeout=30)
    r.raise_for_status()
    data = r.json()
    token = (data.get("token") or data.get("access_token")
             or data.get("accessToken") or data.get("jwt"))
    if not token:
        raise ValueError(f"Token não encontrado: chaves={list(data.keys())[:10]}")
    s.headers["Authorization"] = f"Bearer {token}"
    return s

def listar_eventos(s):
    if "Authorization" not in s.headers:
        raise ValueError("Sessão sem Authorization; token nao definido")
    """Busca eventos paginados (page/limit)."""
    hoje = date.today()
    params = {"startDate": hoje.isoformat(),
              "endDate": (hoje + timedelta(days=DIAS)).isoformat(),
              "status": "published", "sortBy": "startDate",
              "sortOrder": "asc", "limit": 100}
    eventos, page = [], 1
    while True:
        params["page"] = page
        r = s.get(API_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        lote = data if isinstance(data, list) else next(
            (data[k] for k in ("results", "data", "items", "events")
             if k in data), [])
        eventos.extend(lote)
        if isinstance(data, list) or len(lote) < 100:
            break
        page += 1
    return eventos


def extrair_turma(turma):
    cred = turma.portal
    s = autenticar(cred)
    eventos = listar_eventos(s)
    # Se nenhum evento e pode ser expiraçao? Nao assume; retry apenas se 401 no listar
    return eventos


def notificar_telegram(turma, criados, com_pdf):
    grupo = getattr(turma, "telegram", None)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not grupo or not grupo.ativo or not token or criados == 0:
        return
    msg = (f"🗓️ Nova agenda de {turma.nome}: {criados} novo(s) evento(s). "
           f"✅ {com_pdf} com PDF.")
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": grupo.chat_id, "text": msg}, timeout=15)
    except Exception as e:
        logger.error(f"[{turma.nome}] Falha Telegram: {e}")




def verificar_token_expirado(s):
    """Verifica se token ainda valido via chamada leve; retorna True se expirado/invalidado."""
    try:
        r = s.get(API_URL, params={"limit":1,"status":"published"}, timeout=10)
        if r.status_code in (401, 403):
            return True
        return False
    except Exception:
        return True  # assume expirado se falhar completamente


PORTAL_DOWNLOAD_BASE = "https://mb4.bernoulli.com.br/api/storage/download"


def _extrair_author(ev):
    contact = ev.get("contact") or {}
    if isinstance(contact, dict):
        name = contact.get("name") or ""
        if isinstance(name, str) and name.strip():
            return name.strip()[:150]
    for chave in ("author", "autor"):
        valor = ev.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()[:150]
    return ""


def _extrair_time(ev):
    direto = ev.get("time")
    if isinstance(direto, str) and direto.strip():
        return direto.strip()[:30]
    inicio = str(ev.get("startTime") or ev.get("start_time") or "")[:5]
    fim = str(ev.get("endTime") or ev.get("end_time") or "")[:5]
    if inicio and fim and fim != inicio:
        return f"{inicio} – {fim}"[:30]
    return (inicio or "")[:30]


def _extrair_type(ev):
    tipo = str(ev.get("type") or ev.get("tipo") or "event").strip()[:20]
    return tipo or "event"


def _coletar_links(ev):
    links = []

    def _add(url):
        if isinstance(url, str) and url.strip().startswith("http"):
            url = url.strip()
            if url not in links:
                links.append(url)

    for valor in (ev.get("links") or []):
        if isinstance(valor, str):
            _add(valor)
        elif isinstance(valor, dict):
            _add(valor.get("url") or valor.get("downloadUrl")
                 or valor.get("download_url") or valor.get("href"))

    anexos = (ev.get("attachments") or ev.get("anexos")
              or ev.get("files") or [])
    if isinstance(anexos, dict):
        anexos = [anexos]
    for anexo in anexos:
        if isinstance(anexo, str):
            _add(anexo)
            continue
        if not isinstance(anexo, dict):
            continue
        url = (anexo.get("url") or anexo.get("downloadUrl")
               or anexo.get("download_url") or anexo.get("href") or "")
        blob = (anexo.get("blobName") or anexo.get("blob_name") or "")
        if blob and not url:
            url = f"{PORTAL_DOWNLOAD_BASE}/{blob}"
        _add(url)

    _add(ev.get("download_url"))
    return links

class Command(BaseCommand):
    help = "Extrai e importa a agenda de todas as turmas ativas"

    def handle(self, *args, **opts):
        turmas = Turma.objects.filter(ativa=True)
        logger.info(f"Iniciando importação de {turmas.count()} turma(s)")
        for i, turma in enumerate(turmas):
            if i > 0:
                pausa = random.randint(180, 420)
                logger.info(f"Aguardando {pausa}s antes de {turma.nome}")
                time.sleep(pausa)
            try:
                eventos = extrair_turma(turma)
                criados, com_pdf = self.importar(turma, eventos)
                notificar_telegram(turma, criados, com_pdf)
                logger.info(f"[{turma.nome}] OK — {criados} novos, "
                            f"{com_pdf} com PDF")
            except PortalCredential.DoesNotExist:
                logger.error(f"[{turma.nome}] SEM credencial de portal")
            except Exception as e:
                logger.exception(f"[{turma.nome}] FALHOU: {e}")

    def importar(self, turma, eventos):
        criados = com_pdf = 0
        ids_api = set()
        for ev in eventos:
            eid = str(ev.get("id") or ev.get("externalId") or ev.get("uuid") or "")
            if not eid:
                continue
            ids_api.add(eid)
            links = _coletar_links(ev)
            url = next((u for u in links
                        if u.lower().split("?")[0].endswith(".pdf")), "")
            _, created = AgendaItem.objects.update_or_create(
                external_id=eid,
                defaults={
                    "turma": turma,
                    "date": str(ev.get("startDate") or ev.get("date", ""))[:10],
                    "title": ev.get("title") or ev.get("titulo", ""),
                    "description": ev.get("description") or ev.get("descricao", ""),
                    "download_url": url or "",
                    "author": _extrair_author(ev),
                    "time": _extrair_time(ev),
                    "type": _extrair_type(ev),
                    "links": links,
                })
            if created:
                criados += 1
            if url:
                com_pdf += 1
        removidos, _ = (AgendaItem.objects.filter(turma=turma)
                        .exclude(external_id__in=ids_api).delete())
        if removidos:
            logger.info(f"[{turma.nome}] {removidos} itens removidos")
        return criados, com_pdf
