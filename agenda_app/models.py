from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


class Turma(models.Model):
    nome = models.CharField("Nome", max_length=100, unique=True)
    grade = models.CharField("Grade", max_length=10, default="12")
    class_id = models.CharField("Class ID", max_length=20, default="109576")
    profile = models.CharField("Profile", max_length=20, default="13")
    school = models.CharField("School", max_length=20, default="1846")
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def __str__(self):
        return self.nome


class PortalCredential(models.Model):
    turma = models.OneToOneField(Turma, on_delete=models.CASCADE, related_name="portal")
    usuario_portal = models.CharField("Usuário no portal", max_length=150)
    senha_portal = models.CharField("Senha no portal", max_length=255)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usuário do Portal"
        verbose_name_plural = "Usuários do Portal"

    def __str__(self):
        return f"{self.turma.nome} → {self.usuario_portal}"


class TelegramGroup(models.Model):
    turma = models.OneToOneField(Turma, on_delete=models.CASCADE, related_name="telegram")
    chat_id = models.CharField("Chat ID", max_length=50)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Grupo Telegram"
        verbose_name_plural = "Grupos Telegram"

    def __str__(self):
        return f"Telegram {self.turma.nome}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name="alunos")
    nome_completo = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def __str__(self):
        return f"{self.user.username} ({self.turma.nome})"


class AgendaItem(models.Model):
    TIPO_CHOICES = [
        ("task", "Tarefa"),
        ("event", "Evento"),
        ("assignment", "Atividade"),
        ("assessment", "Avaliação"),
        ("online_class", "Aula online"),
    ]
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE,
                              related_name="itens", null=True)
    external_id = models.CharField(max_length=100, unique=True)
    date = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    download_url = models.URLField(blank=True, default="")
    author = models.CharField(max_length=150, blank=True, default="")
    time = models.CharField(max_length=30, blank=True, default="")
    type = models.CharField(max_length=20, blank=True, default="event",
                            choices=TIPO_CHOICES)
    links = models.JSONField(blank=True, default=list)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "title"]

    def __str__(self):
        return f"{self.date} — {self.title}"


class Conclusao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="conclusoes")
    item = models.ForeignKey(AgendaItem, on_delete=models.CASCADE,
                             related_name="conclusoes")
    concluida = models.BooleanField(default=False)
    concluida_em = models.DateTimeField(null=True, blank=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("usuario", "item")

    def __str__(self):
        return f"{self.usuario.username} → #{self.item_id}: {self.concluida}"

# ====== MODELOS SEGURANÇA + CRIPTOGRAFIA ======
from cryptography.fernet import Fernet
from django.conf import settings
import hashlib, base64

def get_fernet():
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

class PortalSecure(models.Model):
    turma = models.OneToOneField('Turma', on_delete=models.CASCADE, related_name='portal_secure')
    usuario_portal = models.CharField(max_length=150)
    senha_criptografada = models.TextField()
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def set_password(self, plain):
        f = get_fernet()
        self.senha_criptografada = f.encrypt(plain.encode()).decode()
    
    def get_password(self):
        f = get_fernet()
        return f.decrypt(self.senha_criptografada.encode()).decode()
