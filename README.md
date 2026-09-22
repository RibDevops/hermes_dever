# Agenda v2 — Multi-turma

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env           # Windows: copy .env.example .env
```

O projeto já possui migrações versionadas. Em uma instalação nova, **não execute `makemigrations` como etapa de instalação**; aplique as migrações existentes:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Se existir uma base v1 com itens de agenda sem turma, execute a conversão depois de aplicar as migrações:

```bash
python manage.py migrate_v1_to_v2
```

A conversão cria a turma padrão e o usuário `ribeiro`; defina `RIBEIRO_SENHA` no `.env` antes de executá-la.

## Correção do conflito de migrações

O repositório já continha duas migrações chamadas `0001` para `agenda_app`: uma migração v1 antiga (`0001_initial.py`) e a migração v2 (`0001_add_portalsecure.py`). Elas não formavam uma cadeia de dependências; por isso `makemigrations --merge` falhava com `Could not find common ancestor`.

A correção mantém a migração v2, que corresponde aos modelos atuais, e remove somente a migração v1 duplicada. Em uma base ainda não migrada, use:

```bash
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py check
```

Se uma instalação antiga já tiver aplicado manualmente a migração v1, faça backup do banco e não apague registros da tabela `django_migrations` sem comparar o esquema. Nesse caso, a recuperação deve ser feita com um plano de dados específico para o estado real da base.

Se o banco já tiver as tabelas v2, mas ainda não tiver o registro da migração inicial, faça um backup e use:

```bash
python manage.py migrate --fake-initial
python manage.py migrate
```

O `--fake-initial` só deve ser usado quando a estrutura existente tiver sido conferida; ele registra a migração como aplicada sem recriar tabelas. Não use `--fake` para esconder diferenças de esquema.

## Banco local e dados extraídos

O arquivo `db.sqlite3` armazena dados recebidos pelo robô, incluindo agenda, turmas, credenciais do portal e conclusões. Ele é local, está no `.gitignore` e **não deve ser enviado ao GitHub**. Faça backup antes de limpar a base.

Para recriar uma base local vazia:

```powershell
# PowerShell — use somente se aceitar perder os dados locais
Copy-Item .\db.sqlite3 .\db.sqlite3.backup -ErrorAction SilentlyContinue
Remove-Item .\db.sqlite3 -Force -ErrorAction SilentlyContinue
python manage.py migrate
```

Depois da recriação, configure as credenciais no `.env` e execute `python manage.py import_agenda` para buscar novamente os dados do portal. A remoção da base local não apaga os dados do site de origem, mas elimina os dados armazenados localmente pelo robô.

## Operação

```bash
python manage.py import_agenda      # importar eventos manualmente
python manage.py runserver
```

## Cron

```cron
0 6,12,18 * * * cd CAMINHO/hermes_dever && .venv/bin/python manage.py import_agenda >> logs/cron.log 2>&1
```

## Endpoints Bernoulli

- Login: `POST $BERNOULLI_LOGIN_URL`
- Eventos: `GET $BERNOULLI_API_URL` com Bearer JWT e paginação `page/limit`

Nunca grave tokens, senhas ou arquivos `.env` no Git. Use `.env.example` apenas como modelo.
