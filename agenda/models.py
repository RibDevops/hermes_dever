"""
Models da aplicação Agenda
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

from .managers import EventManager


class TelegramUser(models.Model):
    """Usuário vinculado ao Telegram"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='telegram_profile',
        verbose_name='Usuário'
    )
    telegram_id = models.BigIntegerField('ID Telegram', unique=True)
    username = models.CharField('Username', max_length=255, null=True, blank=True)
    first_name = models.CharField('Nome', max_length=255, null=True, blank=True)
    last_name = models.CharField('Sobrenome', max_length=255, null=True, blank=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Usuário Telegram'
        verbose_name_plural = 'Usuários Telegram'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} ({self.telegram_id})"
    
    @property
    def full_name(self):
        """Retorna nome completo"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)


class Event(models.Model):
    """Evento de calendário"""
    
    PRIORITY_CHOICES = [
        ('low', 'Baixa'),
        ('medium', 'Média'),
        ('high', 'Alta'),
    ]
    
    # Campos principais
    title = models.CharField('Título', max_length=255)
    description = models.TextField('Descrição', blank=True)
    start_date = models.DateTimeField('Data/Hora Início')
    end_date = models.DateTimeField('Data/Hora Fim', null=True, blank=True)
    location = models.CharField('Local', max_length=500, blank=True)
    priority = models.CharField(
        'Prioridade', 
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium'
    )
    
    # Relacionamentos
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='events_created',
        verbose_name='Criado por'
    )
    
    # Integração externa
    bernoulli_id = models.CharField(
        'ID Bernoulli', 
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True,
        db_index=True
    )
    telegram_message_id = models.BigIntegerField(
        'ID Mensagem Telegram', 
        null=True, 
        blank=True
    )
    
    # Metadados
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    is_active = models.BooleanField('Ativo', default=True, db_index=True)
    
    # Manager customizado
    objects = EventManager()
    
    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['start_date']
        indexes = [
            models.Index(fields=['start_date', 'is_active']),
            models.Index(fields=['created_by', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_date.strftime('%d/%m/%Y %H:%M')}"
    
    def clean(self):
        """Validações customizadas"""
        super().clean()
        
        # Validar datas
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    'end_date': 'A data de término deve ser posterior à data de início.'
                })
        
        # Validar título
        if self.title and len(self.title.strip()) < 3:
            raise ValidationError({
                'title': 'O título deve ter pelo menos 3 caracteres.'
            })
    
    def save(self, *args, **kwargs):
        """Override save para executar validações"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_past(self):
        """Verifica se o evento já passou"""
        return self.start_date < timezone.now()
    
    @property
    def is_today(self):
        """Verifica se o evento é hoje"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timezone.timedelta(days=1)
        return today_start <= self.start_date < today_end
    
    @property
    def duration(self):
        """Retorna duração do evento"""
        if self.end_date:
            return self.end_date - self.start_date
        return None
    
    @property
    def duration_hours(self):
        """Retorna duração em horas"""
        if self.duration:
            return self.duration.total_seconds() / 3600
        return None
    
    @property
    def priority_display(self):
        """Retorna prioridade formatada"""
        return dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)
    
    @property
    def priority_color(self):
        """Retorna cor CSS para prioridade"""
        colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'error',
        }
        return colors.get(self.priority, 'info')


class EventAttachment(models.Model):
    """Anexo de evento"""
    
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE, 
        related_name='attachments',
        verbose_name='Evento'
    )
    file = models.FileField(
        'Arquivo', 
        upload_to='attachments/%Y/%m/',
        max_length=500
    )
    file_name = models.CharField('Nome do Arquivo', max_length=255)
    file_size = models.IntegerField('Tamanho (bytes)', null=True, blank=True)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='uploaded_files',
        verbose_name='Enviado por'
    )
    uploaded_at = models.DateTimeField('Enviado em', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.event.title})"
    
    def clean(self):
        """Validações customizadas"""
        super().clean()
        
        # Validar tamanho do arquivo (máximo 10MB)
        if self.file:
            max_size = 10 * 1024 * 1024  # 10MB em bytes
            if self.file.size > max_size:
                raise ValidationError({
                    'file': f'O arquivo excede o tamanho máximo de 10MB.'
                })
    
    def save(self, *args, **kwargs):
        """Override save para preencher metadados"""
        if self.file and not self.file_name:
            self.file_name = self.file.name
        
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def file_size_mb(self):
        """Retorna tamanho em MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    @property
    def file_extension(self):
        """Retorna extensão do arquivo"""
        if self.file_name:
            return self.file_name.split('.')[-1].lower()
        return None