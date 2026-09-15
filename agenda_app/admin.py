from django.contrib import admin
from .models import AgendaItem

@admin.register(AgendaItem)
class AgendaItemAdmin(admin.ModelAdmin):
    list_display = ('date', 'title', 'completed', 'created_at')
    list_filter = ('completed', 'date')
    search_fields = ('title', 'description')
