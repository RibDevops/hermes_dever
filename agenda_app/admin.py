from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (AgendaItem, Conclusao, PortalCredential, TelegramGroup,
                     Turma, UserProfile)


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome", "grade", "class_id", "ativa")
    list_filter = ("ativa",)


@admin.register(PortalCredential)
class PortalAdmin(admin.ModelAdmin):
    list_display = ("turma", "usuario_portal", "atualizada_em")


@admin.register(TelegramGroup)
class TelegramAdmin(admin.ModelAdmin):
    list_display = ("turma", "chat_id", "ativo")


@admin.register(UserProfile)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("user", "turma")
    list_filter = ("turma",)


@admin.register(AgendaItem)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("date", "title", "turma", "type", "author")
    list_filter = ("turma", "type")


@admin.register(Conclusao)
class ConclusaoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "item", "concluida", "concluida_em")
    list_filter = ("concluida",)


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdminWithTurma(UserAdmin):
    inlines = (ProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdminWithTurma)
