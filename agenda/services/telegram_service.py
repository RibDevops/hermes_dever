"""
Serviço para operações do Telegram
"""
from django.utils import timezone
from datetime import timedelta

from agenda.models import Event, TelegramUser


class TelegramService:
    """Serviço para lógica do bot Telegram"""
    
    @staticmethod
    def get_or_create_telegram_user(telegram_id, user_data):
        """
        Busca ou cria usuário Telegram
        
        Args:
            telegram_id: ID do Telegram
            user_data: dict com dados do usuário (username, first_name, last_name)
            
        Returns:
            tuple: (TelegramUser, created)
        """
        return TelegramUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults=user_data
        )
    
    @staticmethod
    def get_upcoming_events(telegram_user, days=7):
        """
        Retorna eventos futuros do usuário
        
        Args:
            telegram_user: Instância TelegramUser
            days: Número de dias à frente (padrão: 7)
            
        Returns:
            QuerySet: Eventos futuros
        """
        django_user = telegram_user.user
        now = timezone.now()
        end_date = now + timedelta(days=days)
        
        return (
            Event.objects
            .active()
            .for_user(django_user)
            .in_range(now, end_date)
            .with_relations()
            .order_by('start_date')
        )
    
    @staticmethod
    def get_today_events(telegram_user):
        """
        Retorna eventos de hoje
        
        Args:
            telegram_user: Instância TelegramUser
            
        Returns:
            QuerySet: Eventos de hoje
        """
        django_user = telegram_user.user
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        return (
            Event.objects
            .active()
            .for_user(django_user)
            .in_range(today_start, today_end)
            .with_relations()
            .order_by('start_date')
        )
    
    @staticmethod
    def format_event_message(event, include_description=True):
        """
        Formata evento para mensagem Telegram
        
        Args:
            event: Instância Event
            include_description: Incluir descrição (padrão: True)
            
        Returns:
            str: Mensagem formatada
        """
        # Emoji de prioridade
        priority_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴'
        }.get(event.priority, '⚪')
        
        # Data formatada
        date_str = event.start_date.strftime('%d/%m/%Y %H:%M')
        
        # Construir mensagem
        message = f"{priority_emoji} *{event.title}*\n"
        message += f"📆 {date_str}\n"
        
        if event.location:
            message += f"📍 {event.location}\n"
        
        if include_description and event.description:
            desc = event.description[:100] + '...' if len(event.description) > 100 else event.description
            message += f"📝 {desc}\n"
        
        return message
    
    @staticmethod
    def format_events_list(events, title="Eventos"):
        """
        Formata lista de eventos para Telegram
        
        Args:
            events: QuerySet ou lista de eventos
            title: Título da lista
            
        Returns:
            str: Mensagem formatada
        """
        if not events:
            return f"Você não tem {title.lower()}."
        
        message = f"📅 *{title} ({len(events)}):*\n\n"
        
        for event in events:
            message += TelegramService.format_event_message(event, include_description=True)
            message += "\n"
        
        return message