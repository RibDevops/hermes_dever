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
