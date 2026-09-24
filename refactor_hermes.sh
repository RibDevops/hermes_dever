#!/bin/bash

# ============================================
# SCRIPT DE REFATORAÇÃO DO PROJETO HERMES
# ============================================
# Execução: bash refactor_hermes.sh
# ============================================

set -e  # Parar em caso de erro

echo "🚀 Iniciando refatoração do projeto Hermes..."
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# FASE 1 — BACKUP
# ============================================

echo -e "${BLUE}📦 FASE 1 — Criando backup...${NC}"

if [ ! -d "../hermes_backup_$(date +%Y%m%d_%H%M%S)" ]; then
    cp -r . "../hermes_backup_$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓ Backup criado em ../hermes_backup_$(date +%Y%m%d_%H%M%S)${NC}"
else
    echo -e "${YELLOW}⚠ Backup já existe${NC}"
fi

echo ""

# ============================================
# FASE 2 — LIMPEZA DE ARQUIVOS DESNECESSÁRIOS
# ============================================

echo -e "${BLUE}🧹 FASE 2 — Limpando arquivos desnecessários...${NC}"

# Remover __pycache__
echo "Removendo __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ __pycache__ removidos${NC}"

# Remover .pyc, .pyo
echo "Removendo arquivos .pyc e .pyo..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Bytecode Python removido${NC}"

# Remover arquivos de sistema
echo "Removendo arquivos de sistema..."
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
find . -type f -name "Thumbs.db" -delete 2>/dev/null || true
find . -type f -name "desktop.ini" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Arquivos de sistema removidos${NC}"

# Remover staticfiles/ (se existir)
if [ -d "staticfiles" ]; then
    echo "Removendo staticfiles/..."
    rm -rf staticfiles
    echo -e "${GREEN}✓ staticfiles/ removido${NC}"
fi

# Remover arquivos legados
echo "Removendo arquivos legados..."

# CSS legado
if [ -f "agenda/static/agenda/css/old_style.css" ]; then
    rm agenda/static/agenda/css/old_style.css
    echo -e "${GREEN}✓ old_style.css removido${NC}"
fi

# JS legado
if [ -f "agenda/static/agenda/js/old_scripts.js" ]; then
    rm agenda/static/agenda/js/old_scripts.js
    echo -e "${GREEN}✓ old_scripts.js removido${NC}"
fi

# jQuery local (usar CDN)
if [ -f "agenda/static/agenda/js/jquery.min.js" ]; then
    rm agenda/static/agenda/js/jquery.min.js
    echo -e "${GREEN}✓ jquery.min.js removido (usar CDN)${NC}"
fi

# Templates de backup
echo "Removendo templates de backup..."
find agenda/templates/agenda -type f -name "old_*.html" -delete 2>/dev/null || true
find agenda/templates/agenda -type f -name "backup_*.html" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Templates legados removidos${NC}"

# Imagens temporárias
echo "Removendo imagens temporárias..."
find agenda/static/agenda/images -type f -name "temp_*" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Imagens temporárias removidas${NC}"

echo ""

# ============================================
# FASE 3 — REMOVER DO GIT (mas manter local)
# ============================================

echo -e "${BLUE}🔒 FASE 3 — Removendo arquivos sensíveis do Git...${NC}"

# Remover db.sqlite3 do Git (mas manter localmente)
if [ -f "db.sqlite3" ]; then
    git rm --cached db.sqlite3 2>/dev/null || true
    echo -e "${GREEN}✓ db.sqlite3 removido do Git (mantido localmente)${NC}"
fi

# Remover media/ do Git
if [ -d "media" ]; then
    git rm -r --cached media 2>/dev/null || true
    echo -e "${GREEN}✓ media/ removido do Git${NC}"
fi

# Remover staticfiles/ do Git
git rm -r --cached staticfiles 2>/dev/null || true

# Remover venv/ se existir
if [ -d "venv" ]; then
    git rm -r --cached venv 2>/dev/null || true
    echo -e "${GREEN}✓ venv/ removido do Git${NC}"
fi

if [ -d ".venv" ]; then
    git rm -r --cached .venv 2>/dev/null || true
    echo -e "${GREEN}✓ .venv/ removido do Git${NC}"
fi

echo ""

# ============================================
# FASE 4 — ATUALIZAR .gitignore
# ============================================

echo -e "${BLUE}📝 FASE 4 — Atualizando .gitignore...${NC}"

cat > .gitignore << 'EOF'
# Python
*.py[cod]
*$py.class
__pycache__/
*.so
.Python
env/
venv/
.venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/media
/staticfiles
/static_collected

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.project
.pydevproject
.settings/

# OS
.DS_Store
Thumbs.db
desktop.ini

# Coverage
htmlcov/
.tox/
.coverage
.coverage.*
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Jupyter
.ipynb_checkpoints

# Temporary
*.bak
*.tmp
*.temp
*~

# Logs
*.log
logs/
EOF

echo -e "${GREEN}✓ .gitignore atualizado${NC}"
echo ""

# ============================================
# FASE 5 — CRIAR ESTRUTURA DE PASTAS
# ============================================

echo -e "${BLUE}📁 FASE 5 — Criando nova estrutura de pastas...${NC}"

# Services
mkdir -p agenda/services
touch agenda/services/__init__.py
echo -e "${GREEN}✓ agenda/services/ criado${NC}"

# Managers
mkdir -p agenda/managers
touch agenda/managers/__init__.py
echo -e "${GREEN}✓ agenda/managers/ criado${NC}"

# Template tags
mkdir -p agenda/templatetags
touch agenda/templatetags/__init__.py
echo -e "${GREEN}✓ agenda/templatetags/ criado${NC}"

# Reorganizar testes
if [ -f "agenda/tests.py" ]; then
    mkdir -p agenda/tests
    mv agenda/tests.py agenda/tests/test_views.py 2>/dev/null || true
    touch agenda/tests/__init__.py
    touch agenda/tests/test_models.py
    touch agenda/tests/test_forms.py
    touch agenda/tests/test_services.py
    echo -e "${GREEN}✓ Testes reorganizados em agenda/tests/${NC}"
fi

echo ""

# ============================================
# FASE 6 — CRIAR ARQUIVOS DE SERVICES
# ============================================

echo -e "${BLUE}⚙️  FASE 6 — Criando Services...${NC}"

# Event Service
cat > agenda/services/event_service.py << 'EOF'
"""
Service layer para lógica de negócio relacionada a eventos
"""
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from ..models import Event


class EventService:
    """Service para operações com eventos"""
    
    @staticmethod
    def get_user_events(user, active_only=True):
        """Retorna eventos do usuário"""
        queryset = Event.objects.filter(created_by=user)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return queryset.select_related('created_by').prefetch_related('attachments')
    
    @staticmethod
    def get_upcoming_events(user, days=7, limit=None):
        """Retorna próximos eventos do usuário"""
        now = timezone.now()
        queryset = Event.objects.filter(
            created_by=user,
            start_date__gte=now,
            start_date__lte=now + timedelta(days=days),
            is_active=True
        ).select_related('created_by').order_by('start_date')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @staticmethod
    def get_past_events(user, days=30, limit=None):
        """Retorna eventos passados do usuário"""
        now = timezone.now()
        queryset = Event.objects.filter(
            created_by=user,
            start_date__lt=now,
            start_date__gte=now - timedelta(days=days),
            is_active=True
        ).select_related('created_by').order_by('-start_date')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @staticmethod
    def get_today_events(user):
        """Retorna eventos de hoje"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        return Event.objects.filter(
            created_by=user,
            start_date__gte=today_start,
            start_date__lt=today_end,
            is_active=True
        ).select_related('created_by').order_by('start_date')
    
    @staticmethod
    def get_event_statistics(user):
        """Retorna estatísticas de eventos do usuário"""
        now = timezone.now()
        
        # Total de eventos
        total_events = Event.objects.filter(
            created_by=user,
            is_active=True
        ).count()
        
        # Eventos esta semana
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        events_this_week = Event.objects.filter(
            created_by=user,
            start_date__gte=week_start,
            start_date__lt=week_end,
            is_active=True
        ).count()
        
        # Eventos este mês
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = month_start.replace(year=now.year + 1, month=1)
        else:
            month_end = month_start.replace(month=now.month + 1)
        
        events_this_month = Event.objects.filter(
            created_by=user,
            start_date__gte=month_start,
            start_date__lt=month_end,
            is_active=True
        ).count()
        
        # Eventos por prioridade
        events_by_priority = Event.objects.filter(
            created_by=user,
            is_active=True
        ).values('priority').annotate(count=Count('id'))
        
        priority_counts = {item['priority']: item['count'] for item in events_by_priority}
        
        return {
            'total_events': total_events,
            'events_this_week': events_this_week,
            'events_this_month': events_this_month,
            'priority_counts': priority_counts,
        }
    
    @staticmethod
    def search_events(user, query):
        """Busca eventos por título ou descrição"""
        return Event.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query),
            created_by=user,
            is_active=True
        ).select_related('created_by').order_by('-start_date')
    
    @staticmethod
    def soft_delete_event(event):
        """Soft delete de um evento"""
        event.is_active = False
        event.save(update_fields=['is_active'])
        return event
EOF

echo -e "${GREEN}✓ event_service.py criado${NC}"

# Telegram Service
cat > agenda/services/telegram_service.py << 'EOF'
"""
Service layer para integração com Telegram
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Service para operações do Telegram"""
    
    @staticmethod
    def format_event_message(event):
        """Formata evento para mensagem Telegram"""
        priority_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }.get(event.priority, '⚪')
        
        data_formatada = event.start_date.strftime('%d/%m/%Y %H:%M')
        
        mensagem = f"{priority_emoji} *{event.title}*\n"
        mensagem += f"📆 {data_formatada}\n"
        
        if event.location:
            mensagem += f"📍 {event.location}\n"
        
        if event.description:
            desc_curta = event.description[:150] + '...' if len(event.description) > 150 else event.description
            mensagem += f"📝 {desc_curta}\n"
        
        return mensagem
    
    @staticmethod
    def format_events_list(events, title="Eventos"):
        """Formata lista de eventos para Telegram"""
        if not events:
            return f"Você não tem {title.lower()}."
        
        mensagem = f"📅 *{title} ({len(events)}):*\n\n"
        
        for evento in events:
            mensagem += TelegramService.format_event_message(evento)
            mensagem += "\n"
        
        return mensagem
EOF

echo -e "${GREEN}✓ telegram_service.py criado${NC}"

# __init__.py para services
cat > agenda/services/__init__.py << 'EOF'
from .event_service import EventService
from .telegram_service import TelegramService

__all__ = ['EventService', 'TelegramService']
EOF

echo ""

# ============================================
# FASE 7 — CRIAR MANAGERS CUSTOMIZADOS
# ============================================

echo -e "${BLUE}🔧 FASE 7 — Criando Managers customizados...${NC}"

cat > agenda/managers/event_manager.py << 'EOF'
"""
Managers customizados para o model Event
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta


class EventQuerySet(models.QuerySet):
    """QuerySet customizado para Event"""
    
    def active(self):
        """Retorna apenas eventos ativos"""
        return self.filter(is_active=True)
    
    def for_user(self, user):
        """Retorna eventos de um usuário"""
        return self.filter(created_by=user)
    
    def upcoming(self, days=7):
        """Retorna eventos futuros"""
        now = timezone.now()
        return self.filter(
            start_date__gte=now,
            start_date__lte=now + timedelta(days=days)
        )
    
    def past(self):
        """Retorna eventos passados"""
        return self.filter(start_date__lt=timezone.now())
    
    def by_priority(self, priority):
        """Filtra por prioridade"""
        return self.filter(priority=priority)
    
    def with_related(self):
        """Otimiza queries com relacionamentos"""
        return self.select_related('created_by').prefetch_related('attachments')


class EventManager(models.Manager):
    """Manager customizado para Event"""
    
    def get_queryset(self):
        """Retorna queryset customizado"""
        return EventQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def upcoming(self, days=7):
        return self.get_queryset().upcoming(days)
    
    def past(self):
        return self.get_queryset().past()
EOF

cat > agenda/managers/__init__.py << 'EOF'
from .event_manager import EventManager, EventQuerySet

__all__ = ['EventManager', 'EventQuerySet']
EOF

echo -e "${GREEN}✓ Managers criados${NC}"
echo ""

# ============================================
# FASE 8 — CRIAR TEMPLATE TAGS
# ============================================

echo -e "${BLUE}🏷️  FASE 8 — Criando Template Tags...${NC}"

cat > agenda/templatetags/agenda_tags.py << 'EOF'
"""
Template tags customizados para agenda
"""
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def priority_badge(priority):
    """Retorna classe CSS para badge de prioridade"""
    badges = {
        'low': 'badge-success',
        'medium': 'badge-warning',
        'high': 'badge-danger',
    }
    return badges.get(priority, 'badge-secondary')


@register.filter
def priority_emoji(priority):
    """Retorna emoji para prioridade"""
    emojis = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🔴',
    }
    return emojis.get(priority, '⚪')


@register.filter
def is_past(event):
    """Verifica se evento já passou"""
    return event.start_date < timezone.now()


@register.filter
def is_today(event):
    """Verifica se evento é hoje"""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    return today_start <= event.start_date < today_end


@register.simple_tag
def event_count(user, filter_type='all'):
    """Conta eventos do usuário"""
    from agenda.models import Event
    
    queryset = Event.objects.filter(created_by=user, is_active=True)
    
    if filter_type == 'upcoming':
        queryset = queryset.filter(start_date__gte=timezone.now())
    elif filter_type == 'past':
        queryset = queryset.filter(start_date__lt=timezone.now())
    
    return queryset.count()
EOF

echo -e "${GREEN}✓ Template tags criados${NC}"
echo ""

# ============================================
# FASE 9 — ATUALIZAR REQUIREMENTS.TXT
# ============================================

echo -e "${BLUE}📦 FASE 9 — Atualizando requirements.txt...${NC}"

cat > requirements.txt << 'EOF'
# Django
Django==4.2.7

# Environment
python-decouple==3.8

# Telegram Bot
python-telegram-bot==20.7

# HTTP Requests
requests==2.31.0

# Images
Pillow==10.1.0

# Timezone
pytz==2023.3

# Development (opcional)
# pytest==7.4.3
# pytest-django==4.7.0
# coverage==7.3.2
EOF

echo -e "${GREEN}✓ requirements.txt atualizado${NC}"
echo ""

# ============================================
# FASE 10 — COMMIT DAS ALTERAÇÕES
# ============================================

echo -e "${BLUE}💾 FASE 10 — Preparando commit...${NC}"

git add .
echo -e "${GREEN}✓ Arquivos adicionados ao stage${NC}"

echo ""
echo -e "${YELLOW}⚠️  PRONTO PARA COMMIT${NC}"
echo ""
echo "Execute manualmente:"
echo -e "${BLUE}git commit -m 'refactor: limpeza profunda e reorganização da arquitetura'${NC}"
echo -e "${BLUE}git push origin refactoring-2024${NC}"
echo ""

# ============================================
# RESUMO FINAL
# ============================================

echo -e "${GREEN}✅ REFATORAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo ""
echo -e "${BLUE}📊 RESUMO:${NC}"
echo "✓ Arquivos desnecessários removidos"
echo "✓ __pycache__ e bytecode limpos"
echo "✓ .gitignore atualizado"
echo "✓ Estrutura de services criada"
echo "✓ Managers customizados criados"
echo "✓ Template tags criados"
echo "✓ Testes reorganizados"
echo "✓ requirements.txt atualizado"
echo ""
echo -e "${YELLOW}⚠️  PRÓXIMOS PASSOS:${NC}"
echo "1. Revisar as alterações: git status"
echo "2. Testar localmente: python manage.py test"
echo "3. Commitar: git commit -m 'refactor: limpeza profunda'"
echo "4. Push: git push origin refactoring-2024"
echo ""