# 🚀 Guia do Projeto Hermes - Extrator de Deveres (Bernoulli)

> **Aviso de segurança:** O token JWT que você compartilhou é uma credencial viva.  
> **NUNCA** commite tokens no GitHub. Use variáveis de ambiente (`.env`).

---

## 1. O que você descobriu?

Você encontrou a API REST do calendário do **Meu Bernoulli**:

```
GET https://api.bernoulli.com.br/api/calendario/events
```

### Parâmetros da URL (query string):
| Parâmetro | Exemplo | O que faz |
|-----------|---------|-----------|
| `startDate` | `2026-07-27` | Data inicial do filtro |
| `endDate` | `2026-10-11` | Data final do filtro |
| `page` | `1` | Página de resultados |
| `limit` | `100` | Quantidade por página |
| `status` | `published` | Só trazer publicados |
| `sortBy` | `startDate` | Ordenar por data |
| `sortOrder` | `asc` | Ordem crescente |

### Headers obrigatórios:
```
Authorization: Bearer <SEU_TOKEN_JWT>
Accept: application/json
Origin: https://mb4.bernoulli.com.br
```

### Filtros internos (no corpo da resposta JSON):
A API retorna **todos** os eventos da escola, mas o frontend filtra por:
- `grade` (série): `"12"` = 8º ano
- `class` (turma): `"109576"`, `"109577"`
- `profile` (perfil): `"13"` = Estudante
- `school` (escola): `"1846"`

---

## 2. Como testar no terminal (cURL)

```bash
curl -X GET "https://api.bernoulli.com.br/api/calendario/events?startDate=2026-09-01&endDate=2026-09-30&page=1&limit=100&status=published&sortBy=startDate&sortOrder=asc" \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Accept: application/json" \
  -H "Origin: https://mb4.bernoulli.com.br"
```

---

## 3. Script Python básico (`hermes.py`)

```python
import requests
import json
from datetime import datetime, timedelta

# ========== CONFIGURAÇÕES ==========
TOKEN = "SEU_TOKEN_JWT_AQUI"  # <-- NUNCA deixe isso no código! Use .env
BASE_URL = "https://api.bernoulli.com.br/api/calendario/events"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Origin": "https://mb4.bernoulli.com.br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

# Filtros do seu perfil (8º ano, turma 109576)
MINHA_TURMA = "109576"
MEU_PERFIL = "13"

# ========== FUNÇÕES ==========
def buscar_eventos(inicio, fim):
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
    # Remove tags HTML básicas
    import re
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = texto.replace('&nbsp;', ' ').replace('&amp;', '&')
    return texto.strip()

def mostrar_deveres(eventos):
    print(f"\n📚 Total de deveres encontrados: {len(eventos)}\n")
    for ev in eventos:
        titulo = ev.get("title", "Sem título")
        data = ev.get("startDate", "")[:10]
        tipo = ev.get("type", "")
        prof = ev.get("contact", {}).get("name", "Desconhecido")
        desc = limpar_html(ev.get("description", ""))

        print(f"📅 {data} | {tipo.upper()}")
        print(f"📝 {titulo}")
        print(f"👨‍🏫 {prof}")
        if desc:
            print(f"📖 {desc[:200]}{'...' if len(desc) > 200 else ''}")
        print("-" * 50)

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    # Busca do mês atual
    hoje = datetime.now()
    inicio = hoje.strftime("%Y-%m-01")
    fim = (hoje + timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"🔍 Buscando deveres de {inicio} até {fim}...")

    try:
        dados = buscar_eventos(inicio, fim)
        todos = dados.get("data", [])
        meus = filtrar_meus_eventos(todos)
        mostrar_deveres(meus)
    except Exception as e:
        print(f"❌ Erro: {e}")
```

---

## 4. Como usar com segurança (`.env`)

1. Instale a biblioteca:
```bash
pip install python-dotenv requests
```

2. Crie um arquivo `.env`:
```
BERNOULLI_TOKEN=seu_token_aqui
```

3. Adicione no topo do script:
```python
from dotenv import load_dotenv
import os
load_dotenv()
TOKEN = os.getenv("BERNOULLI_TOKEN")
```

4. Adicione `.env` no `.gitignore`:
```
.env
__pycache__/
```

---

## 5. Dicas de Burp Suite (para iniciantes)

Como você mencionou "buro suit", aqui vai um passo a passo:

### 5.1 Configurar proxy no Burp:
1. Abra o Burp Suite → aba **Proxy** → **Options**
2. Veja qual porta está configurada (geralmente `127.0.0.1:8080`)
3. No navegador, instale a extensão **FoxyProxy** ou configure manualmente
4. Aponte o proxy para `127.0.0.1:8080`

### 5.2 Interceptar o tráfego:
1. No Burp, ligue o **Intercept** (botão "Intercept is on")
2. Acesse o calendário no Meu Bernoulli
3. O Burp vai parar na requisição → clique **Forward** para ir passando
4. Quando aparecer a requisição para `/api/calendario/events`, clique com o botão direito → **Send to Repeater**

### 5.3 Repeater (testar a API):
1. Vá na aba **Repeater**
2. Você verá a requisição completa
3. Clique **Send** para reenviar
4. Edite datas, tokens, etc. e veja a resposta

### 5.4 Descobrir filtros:
1. Vá na aba **Target** → **Site map**
2. Expanda `api.bernoulli.com.br`
3. Clique com direito em qualquer requisição → **Copy as cURL command**
4. Cole no terminal para testar

---

## 6. Próximos passos para o projeto

1. **Autenticação automática**: O token JWT expira. Você precisa descobrir como renová-lo (provavelmente via `/api/autenticado/parametros` ou login).
2. **Salvar em arquivo**: Exporte os deveres para `.txt`, `.json` ou `.ics` (calendário Google).
3. **Notificações**: Use `notify2` (Linux) ou envie para Telegram/Discord.
4. **Agendamento**: Use `cron` no Linux para rodar diariamente.

---

## 7. Estrutura recomendada do repositório

```
hermes_dever/
├── .env                 # NUNCA commite isso!
├── .gitignore
├── hermes.py            # Script principal
├── requirements.txt     # pip install -r requirements.txt
└── README.md
```

**`requirements.txt`:**
```
requests
python-dotenv
```

---

Boa sorte no projeto! 🎯
