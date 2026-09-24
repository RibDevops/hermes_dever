"""
Custom managers para queries otimizadas
"""
from django.db import models
from django.utils import timezone


class EventQuerySet(models.QuerySet):
    """QuerySet customizado para Event com métodos otimizados"""
    
    def active(self):
        """Apenas eventos ativos"""
        return self.filter(is_active=True)
    
    def with_relations(self):
        """Carrega relações para evitar N+1"""
        return self.select_related('created_by').prefetch_related('attachments')
    
    def for_user(self, user):
        """Eventos de um usuário específico"""
        return self.filter(created_by=user)
    
    def upcoming(self):
        """Eventos futuros"""
        return self.filter(start_date__gte=timezone.now())
    
    def past(self):
        """Eventos passados"""
        return self.filter(start_date__lt=timezone.now())
    
    def in_range(self, start_date, end_date):
        """Eventos em um intervalo de datas"""
        return self.filter(start_date__gte=start_date, start_date__lte=end_date)
    
    def this_week(self):
        """Eventos desta semana"""
        now = timezone.now()
        week_start = now - timezone.timedelta(days=now.weekday())
        week_end = week_start + timezone.timedelta(days=7)
        return self.in_range(week_start, week_end)
    
    def this_month(self):
        """Eventos deste mês"""
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Próximo mês
        if now.month == 12:
            month_end = month_start.replace(year=now.year + 1, month=1)
        else:
            month_end = month_start.replace(month=now.month + 1)
        
        return self.in_range(month_start, month_end)
    
    def by_priority(self, priority):
        """Filtrar por prioridade"""
        return self.filter(priority=priority)
    
    def search(self, query):
        """Busca por título ou descrição"""
        return self.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query)
        )


class EventManager(models.Manager):
    """Manager customizado para Event"""
    
    def get_queryset(self):
        return EventQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def with_relations(self):
        return self.get_queryset().with_relations()
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def upcoming(self):
        return self.get_queryset().upcoming()
    
    def past(self):
        return self.get_queryset().past()
    
    def in_range(self, start_date, end_date):
        return self.get_queryset().in_range(start_date, end_date)
    
    def this_week(self):
        return self.get_queryset().this_week()
    
    def this_month(self):
        return self.get_queryset().this_month()
    
    def by_priority(self, priority):
        return self.get_queryset().by_priority(priority)
    
    def search(self, query):
        return self.get_queryset().search(query)