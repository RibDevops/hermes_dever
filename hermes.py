import requests
import json
import re
from datetime import datetime, timedelta

# ========== CONFIGURAÇÕES ==========
# DICA: Use python-dotenv para carregar de um arquivo .env
TOKEN = "SEU_TOKEN_JWT_AQUI"  # <-- Substitua pelo seu token!

BASE_URL = "https://api.bernoulli.com.br/api/calendario/events"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Origin": "https://mb4.bernoulli.com.br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

# Filtros do seu perfil (ajuste conforme necessário)
MINHA_TURMA = "109576"   # 8º ano turma A
MEU_PERFIL = "13"        # Estudante

# ========== FUNÇÕES ==========
def buscar_eventos(inicio, fim):
    """Faz a requisição para a API do calendário."""
    params = {
        "startDate": inicio,
        "endDate": fim,
        "page": 1,
        "limit": 100,
        "status": "published",
        "sortBy": "startDate",
        "sortOrder": "asc"
    }

    resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def filtrar_meus_eventos(eventos):
    """Filtra apenas os eventos da minha turma e perfil."""
    meus = []
    for ev in eventos:
        segs = ev.get("segmentation", [])
        for seg in segs:
            turmas = seg.get("class", [])
            perfis = seg.get("profiles", [])
            if MINHA_TURMA in turmas and MEU_PERFIL in perfis:
                meus.append(ev)
                break
    return meus

def limpar_html(texto):
    """Remove tags HTML e entidades."""
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = texto.replace('&nbsp;', ' ')
    texto = texto.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    texto = texto.replace('\n', '\n')
    return texto.strip()

def mostrar_deveres(eventos):
    """Exibe os deveres no terminal de forma organizada."""
    print(f"\n📚 Total de deveres encontrados: {len(eventos)}\n")
    print("=" * 60)

    for ev in eventos:
        titulo = ev.get("title", "Sem título")
        data = ev.get("startDate", "")[:10]
        tipo = ev.get("type", "desconhecido")
        prof = ev.get("contact", {}).get("name", "Desconhecido")
        desc = limpar_html(ev.get("description", ""))
        anexos = ev.get("attachments", [])

        tipo_emoji = {
            "task": "📝",
            "event": "📅",
            "assignment": "📋",
            "assessment": "📝",
            "online_class": "💻"
        }.get(tipo, "📌")

        print(f"{tipo_emoji} {data} | {tipo.upper()}")
        print(f"   Título: {titulo}")
        print(f"   Professor(a): {prof}")

        if desc:
            # Mostra só as primeiras 3 linhas da descrição
            linhas = desc.split("\n")[:3]
            preview = " ".join(linhas)
            print(f"   Descrição: {preview[:150]}{'...' if len(preview) > 150 else ''}")

        if anexos:
            print(f"   📎 Anexos: {len(anexos)} arquivo(s)")
            for anexo in anexos:
                print(f"      - {anexo.get('fileName', 'arquivo')}")

        print("-" * 60)

def salvar_json(eventos, nome_arquivo="deveres.json"):
    """Salva os deveres em um arquivo JSON."""
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(eventos, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Deveres salvos em: {nome_arquivo}")

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    # Define o período: mês atual + 30 dias
    hoje = datetime.now()
    inicio = hoje.strftime("%Y-%m-01")
    fim = (hoje + timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"🔍 Buscando deveres de {inicio} até {fim}...")

    try:
        dados = buscar_eventos(inicio, fim)
        todos = dados.get("data", [])
        meta = dados.get("meta", {})

        print(f"📊 Total geral na API: {meta.get('total', len(todos))} eventos")

        meus = filtrar_meus_eventos(todos)
        mostrar_deveres(meus)
        salvar_json(meus)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Token expirado ou inválido! Você precisa renovar o JWT.")
        else:
            print(f"❌ Erro HTTP: {e}")
    except Exception as e:
        print(f"❌ Erro: {e}")
