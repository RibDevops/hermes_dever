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
