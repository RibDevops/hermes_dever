#!/usr/bin/env python3
"""
extract_details.py

Extrai eventos da API de calendário do Bernoulli.

Características:
    • Consulta a API por dia.
    • Trata corretamente a paginação de cada dia.
    • Reinicia page=1 para cada nova data.
    • Busca todas as páginas até não haver mais eventos.
    • Agrupa os eventos por data.
    • Converte YYYY-MM-DD para dd/mm/aaaa no JSON final.
    • Ordena as datas cronologicamente.
    • Evita eventos duplicados.
    • Faz novas tentativas em caso de erro de rede/API.
    • Trata HTTP 401, 403, 429 e erros 5xx.
    • Grava o JSON de forma atômica.
    • Registra todo o processo em cron.log.
    • Marca a tarefa como concluída via hermes_tools.
    • Executa a notificação do Telegram ao final.

Saída:
    /home/vboxuser/agenda/agenda_events_by_date.json

Log:
    /home/vboxuser/agenda/cron.log
"""

import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from collections import defaultdict

import requests
from tqdm import tqdm


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_URL = "https://api.bernoulli.com.br/api/calendario/events"

# Pode manter o token aqui.
# Recomenda-se, entretanto, usar variável de ambiente:
# export BERNOULLI_TOKEN="seu_token"
TOKEN = os.getenv("BERNOULLI_TOKEN", "***")

PAGE_SIZE = 100

# Segurança contra loop infinito da API.
MAX_PAGES = 50

# Número de tentativas para erros temporários.
MAX_RETRIES = 3

# Tempo inicial entre tentativas.
RETRY_DELAY = 3

OUTPUT_JSON = pathlib.Path(
    "/home/vboxuser/agenda/agenda_events_by_date.json"
)

LOG_FILE = pathlib.Path(
    "/home/vboxuser/agenda/cron.log"
)

# Intervalo desejado.
START_DATE = "2026-06-20"
END_DATE = "2026-10-05"


# ============================================================
# PREPARAÇÃO
# ============================================================

OUTPUT_JSON.parent.mkdir(
    parents=True,
    exist_ok=True
)

LOG_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOG
# ============================================================

def log(msg: str) -> None:
    """Grava uma mensagem no arquivo de log com timestamp."""

    ts = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:
        with open(
            LOG_FILE,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                f"=== {ts} - {msg}\n"
            )
    except Exception as exc:
        print(
            f"[ERRO LOG] {exc}",
            file=sys.stderr
        )


# ============================================================
# HEADERS
# ============================================================

def get_headers() -> dict:
    """Monta os headers utilizados pela API."""

    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Plataforma": "2",
        "Front-Version": "4.25.97",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://mb4.bernoulli.com.br/",
        "Origin": "https://mb4.bernoulli.com.br/",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/150.0.0.0 "
            "Safari/537.36"
        ),
        "Accept-Language": (
            "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        ),
        "Priority": "u=1, i",
    }


# ============================================================
# REQUISIÇÃO À API
# ============================================================

def fetch_page(
    session: requests.Session,
    page: int,
    start_date: str,
    end_date: str
):
    """
    Busca uma página da API.

    Retorna:
        dict/list do JSON em caso de sucesso.

    Retorna None em caso de falha definitiva.
    """

    params = {
        "startDate": start_date,
        "endDate": end_date,
        "page": page,
        "limit": PAGE_SIZE,
        "status": "published",
        "sortBy": "startDate",
        "sortOrder": "asc",
    }

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            log(
                f"Consultando página {page} "
                f"({start_date} até {end_date}) "
                f"- tentativa {attempt}/{MAX_RETRIES}"
            )

            response = session.get(
                BASE_URL,
                headers=get_headers(),
                params=params,
                timeout=30
            )

            status = response.status_code

            # ------------------------------------------------
            # SUCESSO
            # ------------------------------------------------

            if status == 200:

                try:
                    return response.json()

                except ValueError as exc:

                    log(
                        f"JSON inválido na página {page}: {exc}"
                    )

                    if attempt < MAX_RETRIES:
                        time.sleep(
                            RETRY_DELAY * attempt
                        )
                        continue

                    return None

            # ------------------------------------------------
            # NÃO AUTORIZADO
            # ------------------------------------------------

            if status == 401:

                log(
                    "HTTP 401 - token inválido ou expirado."
                )

                print(
                    "\nERRO: HTTP 401 - "
                    "token inválido ou expirado.",
                    file=sys.stderr
                )

                return None

            # ------------------------------------------------
            # PROIBIDO
            # ------------------------------------------------

            if status == 403:

                log(
                    "HTTP 403 - acesso proibido."
                )

                print(
                    "\nERRO: HTTP 403 - acesso proibido.",
                    file=sys.stderr
                )

                return None

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if status == 429:

                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:
                    wait_time = int(retry_after)
                except (
                    TypeError,
                    ValueError
                ):
                    wait_time = RETRY_DELAY * attempt

                log(
                    f"HTTP 429 - limite da API atingido. "
                    f"Aguardando {wait_time}s."
                )

                if attempt < MAX_RETRIES:
                    time.sleep(wait_time)
                    continue

                return None

            # ------------------------------------------------
            # ERROS TEMPORÁRIOS DO SERVIDOR
            # ------------------------------------------------

            if 500 <= status <= 599:

                log(
                    f"HTTP {status} - erro temporário "
                    f"do servidor."
                )

                if attempt < MAX_RETRIES:

                    wait_time = (
                        RETRY_DELAY * attempt
                    )

                    time.sleep(wait_time)
                    continue

                return None

            # ------------------------------------------------
            # OUTROS ERROS HTTP
            # ------------------------------------------------

            log(
                f"HTTP {status} ao buscar página {page}. "
                f"Resposta: {response.text[:500]}"
            )

            return None

        # ----------------------------------------------------
        # ERRO DE CONEXÃO
        # ----------------------------------------------------

        except requests.exceptions.Timeout as exc:

            log(
                f"Timeout na página {page}: {exc}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )
                continue

            return None

        except requests.exceptions.ConnectionError as exc:

            log(
                f"Erro de conexão na página {page}: {exc}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )
                continue

            return None

        except requests.exceptions.RequestException as exc:

            log(
                f"Erro HTTP na página {page}: {exc}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )
                continue

            return None

        except Exception as exc:

            log(
                f"Erro inesperado na página {page}: "
                f"{type(exc).__name__}: {exc}"
            )

            return None

    return None


# ============================================================
# EXTRAÇÃO DA LISTA DE EVENTOS
# ============================================================

def extract_events(page_json):
    """
    Extrai a lista de eventos de diferentes formatos possíveis
    de resposta da API.

    Formato esperado normalmente:
        {
            "data": [...]
        }

    Também aceita:
        [...]
    """

    if isinstance(page_json, list):
        return page_json

    if not isinstance(page_json, dict):
        log(
            "Resposta da API possui formato inesperado."
        )
        return []

    data = page_json.get("data")

    if isinstance(data, list):
        return data

    # Algumas APIs utilizam outros nomes.
    for key in (
        "events",
        "items",
        "results"
    ):

        value = page_json.get(key)

        if isinstance(value, list):
            return value

    log(
        "Não foi encontrada uma lista de eventos "
        "na resposta da API."
    )

    return []


# ============================================================
# NORMALIZAÇÃO DE DATA
# ============================================================

def normalize_date(iso_date: str) -> str:
    """
    Converte:

        YYYY-MM-DD
        YYYY-MM-DDTHH:MM:SS

    para:

        dd/mm/aaaa
    """

    if not iso_date:
        return ""

    value = str(iso_date).strip()

    # Remove horário.
    date_part = value.split("T")[0]

    try:

        dt = datetime.datetime.strptime(
            date_part,
            "%Y-%m-%d"
        )

        return dt.strftime("%d/%m/%Y")

    except ValueError:

        # Caso já esteja em dd/mm/aaaa.
        try:

            datetime.datetime.strptime(
                date_part,
                "%d/%m/%Y"
            )

            return date_part

        except ValueError:
            return value


# ============================================================
# DATA PARA ORDENAÇÃO
# ============================================================

def date_sort_key(date_string: str):
    """
    Converte dd/mm/aaaa para objeto datetime
    para permitir ordenação cronológica real.
    """

    try:

        return datetime.datetime.strptime(
            date_string,
            "%d/%m/%Y"
        )

    except ValueError:

        # Datas inválidas vão para o final.
        return datetime.datetime.max


# ============================================================
# IDENTIFICADOR DO EVENTO
# ============================================================

def event_fingerprint(event: dict) -> str:
    """
    Cria uma assinatura para identificar eventos duplicados.

    Se existir ID, ele é usado preferencialmente.
    Caso contrário, combina os principais campos.
    """

    event_id = (
        event.get("id")
        or event.get("_id")
        or event.get("eventId")
    )

    if event_id is not None:

        return f"id:{event_id}"

    raw = "|".join(
        str(event.get(field, ""))
        for field in (
            "title",
            "startDate",
            "time",
            "description",
            "download_url",
            "url"
        )
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# NORMALIZAÇÃO DO EVENTO
# ============================================================

def normalize_event(item: dict) -> dict | None:
    """
    Converte o evento original da API para o formato
    utilizado no JSON final.
    """

    if not isinstance(item, dict):
        return None

    start_iso = (
        item.get("startDate")
        or item.get("start_date")
        or ""
    )

    if not start_iso:
        return None

    download_url = (
        item.get("download_url")
        or item.get("downloadUrl")
        or ""
    )

    # Algumas APIs podem fornecer URL em "url".
    if not download_url:
        possible_url = item.get("url", "")

        if isinstance(possible_url, str):
            download_url = possible_url

    if not isinstance(download_url, str):
        download_url = ""

    event = {
        "title": item.get(
            "title",
            ""
        ),

        "time": item.get(
            "time",
            ""
        ),

        "description": item.get(
            "description",
            ""
        ),

        "download_url": download_url,

        "link_ok": (
            download_url.startswith("http://")
            or download_url.startswith("https://")
        ),
    }

    return event


# ============================================================
# BUSCAR TODAS AS PÁGINAS DE UM DIA
# ============================================================

def fetch_all_events_for_day(
    session: requests.Session,
    current_date: str
) -> list[dict]:
    """
    Busca TODAS as páginas referentes a um único dia.

    IMPORTANTE:
        A paginação começa novamente em page=1 para
        cada nova data.

    Exemplo:

        20/06:
            page 1
            page 2
            page 3

        21/06:
            page 1
            page 2

    e assim por diante.
    """

    all_events = []

    seen = set()

    page = 1

    while page <= MAX_PAGES:

        page_json = fetch_page(
            session=session,
            page=page,
            start_date=current_date,
            end_date=current_date
        )

        if page_json is None:

            raise RuntimeError(
                f"Falha ao consultar "
                f"{current_date}, página {page}."
            )

        raw_events = extract_events(
            page_json
        )

        number_of_events = len(
            raw_events
        )

        log(
            f"{current_date} - "
            f"página {page}: "
            f"{number_of_events} eventos."
        )

        # ----------------------------------------------------
        # Não existem mais eventos.
        # ----------------------------------------------------

        if number_of_events == 0:
            break

        # ----------------------------------------------------
        # Processa os eventos.
        # ----------------------------------------------------

        new_events = 0

        for item in raw_events:

            event = normalize_event(item)

            if event is None:
                continue

            fingerprint = event_fingerprint(
                {
                    **event,
                    "startDate": item.get(
                        "startDate",
                        ""
                    )
                }
            )

            if fingerprint in seen:
                continue

            seen.add(fingerprint)

            all_events.append(event)

            new_events += 1

        log(
            f"{current_date} - "
            f"página {page}: "
            f"{new_events} eventos novos."
        )

        # ----------------------------------------------------
        # Se retornou menos que PAGE_SIZE, normalmente
        # chegamos à última página.
        #
        # Mesmo assim, fazemos isso somente como otimização.
        # Se retornar exatamente PAGE_SIZE, obrigatoriamente
        # continuamos para a próxima página.
        # ----------------------------------------------------

        if number_of_events < PAGE_SIZE:
            break

        page += 1

    # --------------------------------------------------------
    # Proteção contra loop de paginação.
    # --------------------------------------------------------

    if page > MAX_PAGES:

        log(
            f"ATENÇÃO: {current_date} atingiu "
            f"MAX_PAGES={MAX_PAGES}."
        )

        raise RuntimeError(
            f"A API ultrapassou o limite de "
            f"{MAX_PAGES} páginas em {current_date}."
        )

    return all_events


# ============================================================
# DATA INICIAL E FINAL
# ============================================================

def generate_dates(
    start_date: str,
    end_date: str
):
    """
    Gera todas as datas do intervalo.
    """

    start = datetime.datetime.strptime(
        start_date,
        "%Y-%m-%d"
    ).date()

    end = datetime.datetime.strptime(
        end_date,
        "%Y-%m-%d"
    ).date()

    if start > end:

        raise ValueError(
            "START_DATE não pode ser maior que END_DATE."
        )

    current = start

    while current <= end:

        yield current

        current += datetime.timedelta(days=1)


# ============================================================
# GRAVAÇÃO ATÔMICA
# ============================================================

def save_json_atomic(
    data,
    output_path: pathlib.Path
):
    """
    Grava o JSON em arquivo temporário e depois substitui
    o arquivo definitivo.

    Isso evita deixar o JSON principal corrompido caso
    o processo seja interrompido durante a gravação.
    """

    temporary_path = output_path.with_suffix(
        ".tmp"
    )

    with open(
        temporary_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")

    temporary_path.replace(
        output_path
    )


# ============================================================
# TODO
# ============================================================

def mark_todo_completed():
    """
    Marca a tarefa como concluída no Hermes.
    """

    todo_payload = {
        "merge": True,
        "todos": [
            {
                "id": "extract_agenda",
                "content": "Extrair agenda diária (API)",
                "status": "completed"
            }
        ]
    }

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import json, sys; "
                    "payload=json.load(sys.stdin); "
                    "from hermes_tools import todo; "
                    "todo(**payload)"
                )
            ],
            input=json.dumps(
                todo_payload
            ).encode("utf-8"),

            capture_output=True,

            timeout=30
        )

        if result.returncode != 0:

            log(
                "Erro ao marcar TODO como concluído: "
                + result.stderr.decode(
                    "utf-8",
                    errors="replace"
                )
            )

        else:

            log(
                "TODO extract_agenda marcado como completed."
            )

    except Exception as exc:

        log(
            f"Erro executando hermes_tools: {exc}"
        )


# ============================================================
# TELEGRAM
# ============================================================

def notify_telegram():
    """
    Executa o script de notificação do Telegram.
    """

    telegram_script = (
        pathlib.Path(__file__).parent
        / "notify_telegram.py"
    )

    if not telegram_script.exists():

        log(
            f"notify_telegram.py não encontrado: "
            f"{telegram_script}"
        )

        return

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(telegram_script)
            ],
            check=False,
            timeout=60
        )

        if result.returncode == 0:

            log(
                "Notificação Telegram executada."
            )

        else:

            log(
                f"Telegram retornou código "
                f"{result.returncode}."
            )

    except Exception as exc:

        log(
            f"Erro executando Telegram: {exc}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = datetime.datetime.now()

    log(
        "================================================"
    )

    log(
        "INÍCIO DA EXTRAÇÃO DA AGENDA"
    )

    log(
        f"Intervalo: {START_DATE} até {END_DATE}"
    )

    log(
        f"PAGE_SIZE={PAGE_SIZE}, "
        f"MAX_PAGES={MAX_PAGES}, "
        f"MAX_RETRIES={MAX_RETRIES}"
    )

    # --------------------------------------------------------
    # Verificação do token.
    # --------------------------------------------------------

    if not TOKEN or TOKEN == "***":

        log(
            "ERRO: TOKEN não configurado."
        )

        print(
            "ERRO: configure o TOKEN antes de executar.",
            file=sys.stderr
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Estrutura final.
    # --------------------------------------------------------

    all_grouped_events = defaultdict(list)

    total_events = 0
    total_pages = 0
    failed_days = []

    # --------------------------------------------------------
    # Sessão HTTP reutilizável.
    # --------------------------------------------------------

    session = requests.Session()

    # --------------------------------------------------------
    # Gera datas.
    # --------------------------------------------------------

    dates = list(
        generate_dates(
            START_DATE,
            END_DATE
        )
    )

    log(
        f"Total de dias a consultar: {len(dates)}"
    )

    # --------------------------------------------------------
    # Barra de progresso.
    # --------------------------------------------------------

    with tqdm(
        dates,
        desc="Dias processados",
        unit="dia"
    ) as pbar:

        for current_date in pbar:

            date_iso = current_date.strftime(
                "%Y-%m-%d"
            )

            date_ddmmyyyy = current_date.strftime(
                "%d/%m/%Y"
            )

            pbar.set_postfix(
                data=date_ddmmyyyy
            )

            try:

                events = fetch_all_events_for_day(
                    session=session,
                    current_date=date_iso
                )

                all_grouped_events[
                    date_ddmmyyyy
                ].extend(events)

                total_events += len(events)

                # Estimativa apenas para log/progresso.
                # A contagem real de páginas é registrada
                # pelos logs da API.
                log(
                    f"{date_iso}: "
                    f"{len(events)} eventos encontrados."
                )

            except Exception as exc:

                failed_days.append(
                    date_iso
                )

                log(
                    f"ERRO no dia {date_iso}: "
                    f"{type(exc).__name__}: {exc}"
                )

                # Não interrompe todo o processo.
                # Continua para o próximo dia.
                continue

    session.close()

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    # Remove possíveis duplicidades entre páginas/dias.
    for date_key in all_grouped_events:

        unique_events = []

        seen = set()

        for event in all_grouped_events[
            date_key
        ]:

            fingerprint = event_fingerprint(
                event
            )

            if fingerprint in seen:
                continue

            seen.add(fingerprint)

            unique_events.append(
                event
            )

        # Ordena os eventos do dia pelo horário.
        unique_events.sort(
            key=lambda event: (
                str(
                    event.get(
                        "time",
                        ""
                    )
                )
            )
        )

        all_grouped_events[
            date_key
        ] = unique_events

    # --------------------------------------------------------
    # Ordena as datas cronologicamente.
    # --------------------------------------------------------

    ordered_dates = sorted(
        all_grouped_events.keys(),
        key=date_sort_key
    )

    # --------------------------------------------------------
    # Monta JSON final.
    # --------------------------------------------------------

    final_result = []

    for date_string in ordered_dates:

        final_result.append(
            {
                "date": date_string,
                "events": all_grouped_events[
                    date_string
                ]
            }
        )

    # ========================================================
    # SALVAR
    # ========================================================

    try:

        save_json_atomic(
            final_result,
            OUTPUT_JSON
        )

        log(
            f"JSON salvo com sucesso: "
            f"{OUTPUT_JSON}"
        )

    except Exception as exc:

        log(
            f"ERRO ao salvar JSON: {exc}"
        )

        print(
            f"ERRO ao salvar JSON: {exc}",
            file=sys.stderr
        )

        sys.exit(1)

    # ========================================================
    # RESUMO
    # ========================================================

    elapsed = (
        datetime.datetime.now()
        - start_time
    )

    log(
        f"Dias com eventos: "
        f"{len(final_result)}"
    )

    log(
        f"Total de eventos: "
        f"{total_events}"
    )

    log(
        f"Dias com falha: "
        f"{len(failed_days)}"
    )

    if failed_days:

        log(
            "Datas com falha: "
            + ", ".join(failed_days)
        )

    log(
        f"Tempo total: {elapsed}"
    )

    # ========================================================
    # TODO
    # ========================================================

    # Só marca como concluído se não houve falhas.
    if not failed_days:

        mark_todo_completed()

    else:

        log(
            "TODO NÃO foi marcado como concluído "
            "porque existem dias com falha."
        )

    # ========================================================
    # TELEGRAM
    # ========================================================

    notify_telegram()

    # ========================================================
    # FINAL
    # ========================================================

    log(
        "FIM DA EXECUÇÃO"
    )

    log(
        "================================================"
    )

    print()
    print(
        "Processamento concluído."
    )
    print(
        f"Dias com eventos: {len(final_result)}"
    )
    print(
        f"Total de eventos: {total_events}"
    )
    print(
        f"Dias com erro: {len(failed_days)}"
    )
    print(
        f"JSON: {OUTPUT_JSON}"
    )

    if failed_days:

        print()
        print(
            "ATENÇÃO: algumas datas apresentaram erro:"
        )

        for date in failed_days:
            print(
                f"  - {date}"
            )

        # Retorna código de erro para cron/systemd.
        sys.exit(2)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
