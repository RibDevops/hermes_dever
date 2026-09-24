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
