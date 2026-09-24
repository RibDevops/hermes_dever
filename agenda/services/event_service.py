"""
Camada de serviço para lógica de negócio de eventos
"""
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

from agenda.models import Event, EventAttachment


class EventService:
    """Serviço para operações de eventos"""
    
    @staticmethod
    def get_dashboard_data(user):
        """
        Retorna dados do dashboard para um usuário
        
        Args:
            user: Usuário autenticado
            
        Returns:
            dict: Dados do dashboard (eventos e estatísticas)
        """
        now = timezone.now()
        
        # Eventos (com relações carregadas)
        upcoming_events = (
            Event.objects
            .active()
            .for_user(user)
            .upcoming()
            .with_relations()
            .order_by('start_date')[:5]
        )
        
        past_events = (
            Event.objects
            .active()
            .for_user(user)
            .past()
            .with_relations()
            .order_by('-start_date')[:5]
        )
        
        # Estatísticas
        total_events = Event.objects.active().for_user(user).count()
        events_this_week = Event.objects.active().for_user(user).this_week().count()
        events_this_month = Event.objects.active().for_user(user).this_month().count()
        
        return {
            'upcoming_events': upcoming_events,
            'past_events': past_events,
            'stats': {
                'total': total_events,
                'this_week': events_this_week,
                'this_month': events_this_month,
            }
        }
    
    @staticmethod
    def get_filtered_events(user, filters):
        """
        Retorna eventos filtrados
        
        Args:
            user: Usuário autenticado
            filters: dict com filtros (search, start_date, end_date, priority)
            
        Returns:
            QuerySet: Eventos filtrados
        """
        queryset = Event.objects.active().for_user(user).with_relations()
        
        # Filtro de busca
        search = filters.get('search')
        if search:
            queryset = queryset.search(search)
        
        # Filtro de data inicial
        start_date = filters.get('start_date')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        
        # Filtro de data final
        end_date = filters.get('end_date')
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        
        # Filtro de prioridade
        priority = filters.get('priority')
        if priority:
            queryset = queryset.by_priority(priority)
        
        return queryset.order_by('-start_date')
    
    @staticmethod
    @transaction.atomic
    def create_event(user, event_data, files=None):
        """
        Cria um novo evento com anexos (transação atômica)
        
        Args:
            user: Usuário criador
            event_data: dict com dados do evento
            files: Lista de arquivos anexos (opcional)
            
        Returns:
            Event: Evento criado
        """
        # Criar evento
        event = Event.objects.create(
            created_by=user,
            **event_data
        )
        
        # Upload de anexos (se houver)
        if files:
            for file in files:
                EventAttachment.objects.create(
                    event=event,
                    file=file,
                    uploaded_by=user
                )
        
        return event
    
    @staticmethod
    @transaction.atomic
    def update_event(event, event_data, files=None):
        """
        Atualiza um evento existente
        
        Args:
            event: Instância do evento
            event_data: dict com dados atualizados
            files: Lista de novos arquivos anexos (opcional)
            
        Returns:
            Event: Evento atualizado
        """
        # Atualizar campos
        for key, value in event_data.items():
            setattr(event, key, value)
        
        event.save()
        
        # Upload de novos anexos (se houver)
        if files:
            for file in files:
                EventAttachment.objects.create(
                    event=event,
                    file=file,
                    uploaded_by=event.created_by
                )
        
        return event
    
    @staticmethod
    def soft_delete_event(event):
        """
        Soft delete de evento
        
        Args:
            event: Instância do evento
            
        Returns:
            Event: Evento desativado
        """
        event.is_active = False
        event.save()
        return event
    
    @staticmethod
    def delete_attachment(attachment):
        """
        Remove anexo de um evento
        
        Args:
            attachment: Instância do anexo
        """
        attachment.delete()
    
    @staticmethod
    def get_calendar_events(user, start_date=None, end_date=None):
        """
        Retorna eventos formatados para calendário
        
        Args:
            user: Usuário autenticado
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            
        Returns:
            list: Lista de eventos formatados para JSON
        """
        queryset = Event.objects.active().for_user(user)
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        
        # Mapear cores por prioridade
        priority_colors = {
            'low': '#34C759',    # Verde
            'medium': '#FF9500', # Laranja
            'high': '#FF3B30',   # Vermelho
        }
        
        events_data = []
        for event in queryset:
            events_data.append({
                'id': event.id,
                'title': event.title,
                'start': event.start_date.isoformat(),
                'end': event.end_date.isoformat() if event.end_date else event.start_date.isoformat(),
                'color': priority_colors.get(event.priority, '#007AFF'),
                'url': f'/agenda/events/{event.id}/',
            })
        
        return events_data