#!/usr/bin/env bash
set -e
ROOT="agenda_v2"
mkdir -p $ROOT/{config,logs,agenda_app/{management/commands,templates/agenda_app}}
touch $ROOT/config/__init__.py $ROOT/agenda_app/__init__.py \
      $ROOT/agenda_app/management/__init__.py \
      $ROOT/agenda_app/management/commands/__init__.py $ROOT/logs/.gitkeep

# ---------- manage.py ----------
cat > $ROOT/manage.py <<'EOF'
#!/usr/bin/env python
import os, sys
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
EOF

# ---------- requirements.txt ----------
cat > $ROOT/requirements.txt <<'EOF'
Django>=5.0
requests
python-dotenv
EOF

# ---------- .env.example ----------
cat > $ROOT/.env.example <<'EOF'
SECRET_KEY=troque-por-uma-chave-aleatoria
DEBUG=True
TELEGRAM_BOT_TOKEN=SEU_TOKEN_NOVO_DO_BOTFATHER
TURMA_PADRAO_NOME=Turma 01
RIBEIRO_SENHA=defina_uma_senha_forte
BERNOULLI_LOGIN_URL=http://api.bernoulli.com.br/api/autenticado/parametros
BERNOULLI_API_URL=http://api.bernoulli.com.br/api/calendario/events
BERNOULLI_LOGIN_FIELD_USER=login
BERNOULLI_LOGIN_FIELD_PASS=senha
DIAS_INTERVALO=89
EOF

# ---------- config/settings.py ----------
cat > $ROOT/config/settings.py <<'EOF'
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "agenda_app",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = True
STATIC_URL = "static/"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "handlers": {
        "file": {"class": "logging.FileHandler",
                 "filename": BASE_DIR / "logs" / "import.log"},
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {"import_agenda": {"handlers": ["file", "console"], "level": "INFO"}},
}
EOF

# ---------- config/urls.py + wsgi.py ----------
cat > $ROOT/config/urls.py <<'EOF'
from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), path("", include("agenda_app.urls"))]
EOF
cat > $ROOT/config/wsgi.py <<'EOF'
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
EOF

# ---------- agenda_app/apps.py ----------
cat > $ROOT/agenda_app/apps.py <<'EOF'
from django.apps import AppConfig
class AgendaAppConfig(AppConfig):
    name = "agenda_app"
EOF

# ---------- agenda_app/models.py ----------
cat > $ROOT/agenda_app/models.py <<'EOF'
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Turma(models.Model):
    nome = models.CharField("Nome", max_length=100, unique=True)
    grade = models.CharField("Grade", max_length=10, default="12")
    class_id = models.CharField("Class ID", max_length=20, default="109576")
    profile = models.CharField("Profile", max_length=20, default="13")
    school = models.CharField("School", max_length=20, default="1846")
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def __str__(self):
        return self.nome


class PortalCredential(models.Model):
    turma = models.OneToOneField(Turma, on_delete=models.CASCADE, related_name="portal")
    usuario_portal = models.CharField("Usuário no portal", max_length=150)
    senha_portal = models.CharField("Senha no portal", max_length=255)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usuário do Portal"
        verbose_name_plural = "Usuários do Portal"

    def __str__(self):
        return f"{self.turma.nome} → {self.usuario_portal}"


class TelegramGroup(models.Model):
    turma = models.OneToOneField(Turma, on_delete=models.CASCADE, related_name="telegram")
    chat_id = models.CharField("Chat ID", max_length=50)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Grupo Telegram"
        verbose_name_plural = "Grupos Telegram"

    def __str__(self):
        return f"Telegram {self.turma.nome}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name="alunos")
    nome_completo = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def __str__(self):
        return f"{self.user.username} ({self.turma.nome})"


class AgendaItem(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE,
                              related_name="itens", null=True)
    external_id = models.CharField(max_length=100, unique=True)
    date = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    download_url = models.URLField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "title"]

    def __str__(self):
        return f"{self.date} — {self.title}"


class Conclusao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="conclusoes")
    item = models.ForeignKey(AgendaItem, on_delete=models.CASCADE,
                             related_name="conclusoes")
    concluida = models.BooleanField(default=False)
    concluida_em = models.DateTimeField(null=True, blank=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("usuario", "item")

    def __str__(self):
        return f"{self.usuario.username} → #{self.item_id}: {self.concluida}"
EOF

# ---------- agenda_app/admin.py ----------
cat > $ROOT/agenda_app/admin.py <<'EOF'
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (AgendaItem, Conclusao, PortalCredential, TelegramGroup,
                     Turma, UserProfile)


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome", "grade", "class_id", "ativa")
    list_filter = ("ativa",)


@admin.register(PortalCredential)
class PortalAdmin(admin.ModelAdmin):
    list_display = ("turma", "usuario_portal", "atualizada_em")


@admin.register(TelegramGroup)
class TelegramAdmin(admin.ModelAdmin):
    list_display = ("turma", "chat_id", "ativo")


@admin.register(UserProfile)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("user", "turma")
    list_filter = ("turma",)


@admin.register(AgendaItem)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("date", "title", "turma")
    list_filter = ("turma",)


@admin.register(Conclusao)
class ConclusaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "item", "concluida", "concluida_em")
    list_filter = ("concluida",)


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdminWithTurma(UserAdmin):
    inlines = (ProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdminWithTurma)
EOF

# ---------- agenda_app/views.py ----------
cat > $ROOT/agenda_app/views.py <<'EOF'
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AgendaItem, Conclusao


def _itens_do_usuario(user):
    concluida_subq = Conclusao.objects.filter(
        usuario=user, item=OuterRef("pk"), concluida=True)
    return (AgendaItem.objects.filter(turma=user.profile.turma)
            .annotate(concluida=Exists(concluida_subq)))


def _contagens(user):
    total = AgendaItem.objects.filter(turma=user.profile.turma).count()
    conc = _itens_do_usuario(user).filter(concluida=True).count()
    return total, conc, total - conc


@login_required
def dashboard(request, status="todas"):
    if not hasattr(request.user, "profile"):
        return render(request, "agenda_app/sem_turma.html", status=403)
    itens = _itens_do_usuario(request.user)
    if status == "pendentes":
        itens = itens.filter(concluida=False)
    elif status == "concluidas":
        itens = itens.filter(concluida=True)
    total, conc, pend = _contagens(request.user)
    return render(request, "agenda_app/dashboard.html", {
        "itens": itens, "status": status, "total": total,
        "qtd_concluidas": conc, "qtd_pendentes": pend,
        "turma": request.user.profile.turma})


@login_required
def calendario(request):
    if not hasattr(request.user, "profile"):
        return render(request, "agenda_app/sem_turma.html", status=403)
    return render(request, "agenda_app/calendario.html", {
        "itens": _itens_do_usuario(request.user),
        "turma": request.user.profile.turma})


@login_required
@require_POST
def toggle_item(request, pk):
    if not hasattr(request.user, "profile"):
        return JsonResponse({"ok": False}, status=403)
    item = get_object_or_404(AgendaItem, pk=pk,
                             turma=request.user.profile.turma)
    conclusao, _ = Conclusao.objects.get_or_create(usuario=request.user, item=item)
    conclusao.concluida = not conclusao.concluida
    conclusao.concluida_em = timezone.now() if conclusao.concluida else None
    conclusao.save()
    return JsonResponse({"ok": True, "concluida": conclusao.concluida})


class LoginView(auth_views.LoginView):
    template_name = "agenda_app/login.html"
    redirect_authenticated_user = True
EOF

# ---------- agenda_app/urls.py ----------
cat > $ROOT/agenda_app/urls.py <<'EOF'
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pendentes/", views.dashboard, {"status": "pendentes"}, name="pendentes"),
    path("concluidas/", views.dashboard, {"status": "concluidas"}, name="concluidas"),
    path("calendario/", views.calendario, name="calendario"),
    path("toggle/<int:pk>/", views.toggle_item, name="toggle_item"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
EOF

# ---------- comando import_agenda (multi-turma, JWT real) ----------
cat > $ROOT/agenda_app/management/commands/import_agenda.py <<'EOF'
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
                    "http://api.bernoulli.com.br/api/calendario/events")
LOGIN_URL = os.getenv("BERNOULLI_LOGIN_URL",
                      "http://api.bernoulli.com.br/api/autenticado/parametros")
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
    """Faz login no portal e devolve sessão com Bearer JWT."""
    s = requests.Session()
    s.headers.update(BASE_HEADERS)
    r = s.post(LOGIN_URL, json={FIELD_USER: cred.usuario_portal,
                                FIELD_PASS: cred.senha_portal}, timeout=30)
    r.raise_for_status()
    data = r.json()
    token = (data.get("token") or data.get("access_token")
             or data.get("accessToken") or data.get("jwt"))
    if not token:
        raise ValueError(f"Token não encontrado na resposta do login: "
                         f"chaves={list(data.keys())[:10]}")
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def listar_eventos(s):
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
    return listar_eventos(s)


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
            anexos = (ev.get("attachments") or ev.get("anexos")
                      or ev.get("files") or [])
            url = next((a.get("url") or a.get("downloadUrl", "")
                        for a in anexos
                        if str(a.get("url", a.get("downloadUrl", "")))
                        .lower().endswith(".pdf")), "")
            _, created = AgendaItem.objects.update_or_create(
                external_id=eid,
                defaults={
                    "turma": turma,
                    "date": str(ev.get("startDate") or ev.get("date", ""))[:10],
                    "title": ev.get("title") or ev.get("titulo", ""),
                    "description": ev.get("description") or ev.get("descricao", ""),
                    "download_url": url or "",
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
EOF

# ---------- comando migrate_v1_to_v2 ----------
cat > $ROOT/agenda_app/management/commands/migrate_v1_to_v2.py <<'EOF'
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from agenda_app.models import AgendaItem, Conclusao, Turma, UserProfile


class Command(BaseCommand):
    help = "Cria turma padrão, usuário ribeiro e converte dados v1"

    def handle(self, *args, **options):
        turma, c = Turma.objects.get_or_create(
            nome=os.getenv("TURMA_PADRAO_NOME", "Turma 01"),
            defaults={"grade": os.getenv("GRADE", "12"),
                      "class_id": os.getenv("CLASS_ID", "109576"),
                      "profile": os.getenv("PROFILE", "13"),
                      "school": os.getenv("SCHOOL", "1846")})
        self.stdout.write(f"Turma {turma.nome}: "
                          f"{'criada' if c else 'já existia'}")
        user, uc = User.objects.get_or_create(username="ribeiro")
        user.set_password(os.getenv("RIBEIRO_SENHA", "troque123"))
        user.save()
        UserProfile.objects.get_or_create(user=user,
                                          defaults={"turma": turma})
        convertidos = 0
        for item in AgendaItem.objects.filter(turma__isnull=True):
            item.turma = turma
            item.save()
            if getattr(item, "completed", False):
                Conclusao.objects.get_or_create(
                    usuario=user, item=item,
                    defaults={"concluida": True,
                              "concluida_em": timezone.now()})
                convertidos += 1
        self.stdout.write(self.style.SUCCESS(
            f"OK — {convertidos} conclusões → ribeiro"))
EOF

# ---------- templates ----------
cat > $ROOT/agenda_app/templates/agenda_app/base.html <<'EOF'
<!DOCTYPE html>
<html lang="pt-br" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agenda — {{ turma.nome|default:"" }}</title>
<style>
:root{--bg:#0d0d0f;--surface:#17171b;--border:#26262c;--text:#e8e8ea;
--muted:#9a9aa3;--accent:#4f8cff;--green:#22c55e;--yellow:#eab308;--sidebar:#000}
[data-theme="light"]{--bg:#f4f5f7;--surface:#fff;--border:#e2e4e9;--text:#17171b;
--muted:#6b6b74;--sidebar:#111114}
*{margin:0;box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:var(--bg);color:var(--text);display:flex;min-height:100vh}
.sidebar{width:240px;background:var(--sidebar);color:#e8e8ea;padding:16px 0;
position:fixed;height:100vh;overflow-y:auto;z-index:50;transition:transform .25s}
.sidebar .brand{padding:8px 20px 18px;font-weight:700;font-size:1.05rem;
border-bottom:1px solid #1d1d22}
.sidebar .turma-badge{display:block;margin:12px 20px 4px;padding:8px 12px;
background:#1b1b20;border-radius:8px;font-size:.8rem;color:#9a9aa3}
.sidebar .turma-badge b{display:block;color:#e8e8ea;font-size:.95rem}
.sidebar a{display:flex;align-items:center;gap:10px;padding:10px 20px;
color:#c9c9d1;text-decoration:none;font-size:.92rem}
.sidebar a:hover,.sidebar a.active{background:#1b1b20;color:#fff;
border-left:3px solid var(--accent)}
.sidebar .section{padding:16px 20px 6px;font-size:.7rem;letter-spacing:.12em;
text-transform:uppercase;color:#6f6f78}
.sidebar form{padding:6px 20px}
.sidebar button.sair{width:100%;background:none;border:none;color:#f87171;
cursor:pointer;padding:10px 0;text-align:left;font-size:.92rem}
.content{margin-left:240px;flex:1;padding:20px 28px;width:calc(100% - 240px)}
.topbar{display:flex;align-items:center;gap:14px;margin-bottom:20px}
.hamburger{display:none;background:none;border:1px solid var(--border);
color:var(--text);border-radius:8px;padding:8px 12px;cursor:pointer;font-size:1.1rem}
.theme-btn{margin-left:auto;background:var(--surface);border:1px solid var(--border);
color:var(--text);border-radius:8px;padding:8px 12px;cursor:pointer}
.filters{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.filters a{padding:7px 16px;border-radius:999px;text-decoration:none;
font-size:.85rem;background:var(--surface);color:var(--muted);
border:1px solid var(--border)}
.filters a.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;
padding:16px;margin-bottom:12px;display:flex;gap:14px;align-items:flex-start}
.card h3{font-size:.98rem;margin-bottom:4px}
.card .data{font-size:.8rem;color:var(--muted)}
.card .desc{font-size:.88rem;color:var(--muted);margin-top:6px;max-height:90px;
overflow:hidden}
.badge{font-size:.7rem;font-weight:700;padding:3px 10px;border-radius:999px}
.badge.ok{background:rgba(34,197,94,.15);color:var(--green)}
.badge.pend{background:rgba(234,179,8,.15);color:var(--yellow)}
.toggle-btn{margin-left:auto;flex-shrink:0;background:none;
border:1px solid var(--border);border-radius:8px;padding:8px 14px;cursor:pointer;
color:var(--text);font-size:.85rem}
.toggle-btn.on{background:var(--green);border-color:var(--green);color:#04120a;
font-weight:700}
@media(max-width:768px){.sidebar{transform:translateX(-100%)}
.sidebar.open{transform:translateX(0)}
.content{margin-left:0;width:100%;padding:14px}.hamburger{display:block}}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:40}
.overlay.show{display:block}
</style>
</head>
<body>
<div class="overlay" id="ov" onclick="toggleMenu()"></div>
<aside class="sidebar" id="sb">
  <div class="brand">🗓️ Agenda</div>
  {% if turma %}<div class="turma-badge">Turma<b>{{ turma.nome }}</b></div>{% endif %}
  <a href="/" class="{% if status|default:'' == 'todas' or status|default:'' == '' %}active{% endif %}">📋 Dashboard</a>
  <a href="{% url 'pendentes' %}" class="{% if status == 'pendentes' %}active{% endif %}">⏳ Pendentes</a>
  <a href="{% url 'concluidas' %}" class="{% if status == 'concluidas' %}active{% endif %}">✅ Concluídas</a>
  <a href="{% url 'calendario' %}" class="{% if request.resolver_match.url_name == 'calendario' %}active{% endif %}">📅 Calendário</a>
  {% if user.is_superuser %}
  <div class="section">Gerenciamento</div>
  <a href="/admin/agenda_app/turma/">🏫 Turmas</a>
  <a href="/admin/agenda_app/userprofile/">👨‍🎓 Alunos</a>
  <a href="/admin/agenda_app/portalcredential/">🔑 Usuários do Portal</a>
  <a href="/admin/agenda_app/telegramgroup/">📢 Grupos Telegram</a>
  <a href="/admin/">⚙️ Admin</a>
  {% endif %}
  <div class="section">Conta</div>
  <div style="padding:4px 20px;font-size:.85rem;color:#9a9aa3">{{ user.username }}</div>
  <form method="post" action="{% url 'logout' %}">{% csrf_token %}
    <button class="sair">🚪 Sair</button>
  </form>
</aside>
<main class="content">
  <div class="topbar">
    <button class="hamburger" onclick="toggleMenu()">☰</button>
    <button class="theme-btn" onclick="toggleTheme()">🌙 / ☀️</button>
  </div>
  {% block content %}{% endblock %}
</main>
<script>
function toggleMenu(){document.getElementById('sb').classList.toggle('open');
document.getElementById('ov').classList.toggle('show')}
function toggleTheme(){const h=document.documentElement;
const n=h.dataset.theme==='light'?'dark':'light';
h.dataset.theme=n;localStorage.setItem('theme',n)}
document.documentElement.dataset.theme=localStorage.getItem('theme')||'dark';
async function toggleItem(pk,btn){
const r=await fetch('/toggle/'+pk+'/',{method:'POST',
headers:{'X-CSRFToken':'{{ csrf_token }}'}});
const d=await r.json();
btn.classList.toggle('on',d.concluida);
btn.textContent=d.concluida?'✓ Concluído':'Marcar concluído';
btn.closest('.card').querySelector('.badge').outerHTML=
d.concluida?'<span class="badge ok">Concluído</span>'
:'<span class="badge pend">Pendente</span>'}
</script>
</body>
</html>
EOF

cat > $ROOT/agenda_app/templates/agenda_app/dashboard.html <<'EOF'
{% extends "agenda_app/base.html" %}
{% block content %}
<div class="filters">
  <a href="/" class="{% if status == 'todas' %}active{% endif %}">Todas ({{ total }})</a>
  <a href="{% url 'pendentes' %}" class="{% if status == 'pendentes' %}active{% endif %}">Pendentes ({{ qtd_pendentes }})</a>
  <a href="{% url 'concluidas' %}" class="{% if status == 'concluidas' %}active{% endif %}">Concluídas ({{ qtd_concluidas }})</a>
</div>
{% for item in itens %}
<div class="card">
  <div style="flex:1">
    <h3>{{ item.title }}</h3>
    <div class="data">📅 {{ item.date }}
      {% if item.download_url %} · <a href="{{ item.download_url }}" target="_blank">📄 PDF</a>{% endif %}
    </div>
    <div class="desc">{{ item.description|striptags|truncatechars:200 }}</div>
  </div>
  {% if item.concluida %}<span class="badge ok">Concluído</span>
  {% else %}<span class="badge pend">Pendente</span>{% endif %}
  <button class="toggle-btn {% if item.concluida %}on{% endif %}"
    onclick="toggleItem({{ item.pk }}, this)">
    {% if item.concluida %}✓ Concluído{% else %}Marcar concluído{% endif %}
  </button>
</div>
{% empty %}<p style="color:var(--muted)">Nenhuma tarefa neste filtro.</p>
{% endfor %}
{% endblock %}
EOF

cat > $ROOT/agenda_app/templates/agenda_app/login.html <<'EOF'
<!DOCTYPE html>
<html lang="pt-br" data-theme="dark"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Login</title>
<style>
:root{--bg:#0d0d0f;--surface:#17171b;--border:#26262c;--text:#e8e8ea;--accent:#4f8cff}
body{background:var(--bg);color:var(--text);font-family:system-ui;display:flex;
justify-content:center;align-items:center;min-height:100vh;margin:0}
form{background:var(--surface);border:1px solid var(--border);border-radius:14px;
padding:32px;width:min(360px,92vw)}
h1{font-size:1.3rem;margin-bottom:20px;text-align:center}
input{width:100%;padding:12px;margin-bottom:12px;border-radius:8px;
border:1px solid var(--border);background:var(--bg);color:var(--text);
box-sizing:border-box}
button{width:100%;padding:12px;border:none;border-radius:8px;background:var(--accent);
color:#fff;font-weight:700;cursor:pointer}
.err{color:#f87171;font-size:.85rem;margin-bottom:12px;text-align:center}
</style></head><body>
<form method="post">{% csrf_token %}
  <h1>🗓️ Agenda Escolar</h1>
  {% if form.errors %}<div class="err">Usuário ou senha inválidos.</div>{% endif %}
  <input type="text" name="username" placeholder="Usuário" required autofocus>
  <input type="password" name="password" placeholder="Senha" required>
  <button>Entrar</button>
</form></body></html>
EOF

cat > $ROOT/agenda_app/templates/agenda_app/sem_turma.html <<'EOF'
{% extends "agenda_app/base.html" %}
{% block content %}
<p style="color:var(--muted)">Seu usuário não está vinculado a nenhuma turma.
Solicite ao administrador.</p>
{% endblock %}
EOF

cat > $ROOT/agenda_app/templates/agenda_app/calendario.html <<'EOF'
{% extends "agenda_app/base.html" %}
{% block content %}
<h2 style="margin-bottom:16px">📅 Calendário — {{ turma.nome }}</h2>
{% regroup itens by date as por_data %}
{% for grupo in por_data %}
  <div class="section" style="color:var(--muted);margin:18px 0 8px">📅 {{ grupo.grouper }}</div>
  {% for item in grupo.list %}
  <div class="card">
    <div style="flex:1"><h3>{{ item.title }}</h3>
      {% if item.download_url %}<div class="data"><a href="{{ item.download_url }}" target="_blank">📄 PDF</a></div>{% endif %}
    </div>
    {% if item.concluida %}<span class="badge ok">✓</span>{% else %}<span class="badge pend">⏳</span>{% endif %}
  </div>
  {% endfor %}
{% endfor %}
{% endblock %}
EOF

# ---------- README ----------
cat > $ROOT/README.md <<'EOF'
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
EOF

# ---------- venv + migrações + zip ----------
cd $ROOT
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python manage.py makemigrations
python manage.py migrate
echo ""
echo "✅ Projeto criado em ./$ROOT"
echo "→ cp .env.example .env e edite"
echo "→ python manage.py createsuperuser"
echo "→ python manage.py migrate_v1_to_v2"
cd ..
# zip -r agenda_v2.zip $ROOT -x "$ROOT/.venv/*" "$ROOT/db.sqlite3"
# echo "📦 ZIP gerado: agenda_v2.zip"