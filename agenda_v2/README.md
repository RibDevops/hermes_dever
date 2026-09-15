# Agenda v2 — Multi-turma

## Setup
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env  # edite com seus valores
    python manage.py makemigrations && python manage.py migrate
    python manage.py createsuperuser
    python manage.py migrate_v1_to_v2   # se tiver db v1
    python manage.py import_agenda      # teste manual
    python manage.py runserver

## Cron
    0 6,12,18 * * * cd CAMINHO/agenda_v2 && .venv/bin/python manage.py import_agenda >> logs/cron.log 2>&1

## Endpoints Bernoulli
- Login (payload a confirmar): POST $BERNOULLI_LOGIN_URL
- Eventos: GET $BERNOULLI_API_URL (Bearer JWT, paginação page/limit)
