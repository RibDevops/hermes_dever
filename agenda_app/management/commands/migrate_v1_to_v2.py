import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from agenda_app.models import AgendaItem, Conclusao, Turma, UserProfile


class Command(BaseCommand):
    help = "Cria turma padrão, usuário ribeiro e converte dados v1"

    def handle(self, *args, **options):
        turma, c = Turma.objects.get_or_create(
            nome=os.getenv("TURMA_PADRAO_NOME", "Turma 01"),
            defaults={"grade": os.getenv("GRADE", "12"),
                      "class_id": os.getenv("CLASS_ID", "109576"),
                      "profile": os.getenv("PROFILE", "13"),
                      "school": os.getenv("SCHOOL", "1846")})
        self.stdout.write(f"Turma {turma.nome}: "
                          f"{'criada' if c else 'já existia'}")
        user, uc = User.objects.get_or_create(username="ribeiro")
        user.set_password(os.getenv("RIBEIRO_SENHA", "troque123"))
        user.save()
        UserProfile.objects.get_or_create(user=user,
                                          defaults={"turma": turma})
        convertidos = 0
        for item in AgendaItem.objects.filter(turma__isnull=True):
            item.turma = turma
            item.save()
            if getattr(item, "completed", False):
                Conclusao.objects.get_or_create(
                    usuario=user, item=item,
                    defaults={"concluida": True,
                              "concluida_em": timezone.now()})
                convertidos += 1
        self.stdout.write(self.style.SUCCESS(
            f"OK — {convertidos} conclusões → ribeiro"))
