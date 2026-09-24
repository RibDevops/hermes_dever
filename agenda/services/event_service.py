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
