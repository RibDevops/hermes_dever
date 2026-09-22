from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AgendaItem, Conclusao


def _itens_do_usuario(user):
    concluida_subq = Conclusao.objects.filter(
        usuario=user, item=OuterRef("pk"), concluida=True)
    return (AgendaItem.objects.filter(turma=user.profile.turma)
            .annotate(concluida=Exists(concluida_subq)))


def _contagens(user):
    total = AgendaItem.objects.filter(turma=user.profile.turma).count()
    conc = _itens_do_usuario(user).filter(concluida=True).count()
    return total, conc, total - conc


@login_required
def dashboard(request, status="todas"):
    if not hasattr(request.user, "profile"):
        return render(request, "agenda_app/sem_turma.html", status=403)
    itens = _itens_do_usuario(request.user)
    if status == "pendentes":
        itens = itens.filter(concluida=False)
    elif status == "concluidas":
        itens = itens.filter(concluida=True)
    total, conc, pend = _contagens(request.user)
    return render(request, "agenda_app/dashboard.html", {
        "itens": itens, "status": status, "total": total,
        "qtd_concluidas": conc, "qtd_pendentes": pend,
        "turma": request.user.profile.turma})


@login_required
def calendario(request):
    if not hasattr(request.user, "profile"):
        return render(request, "agenda_app/sem_turma.html", status=403)
    return render(request, "agenda_app/calendario.html", {
        "itens": _itens_do_usuario(request.user),
        "turma": request.user.profile.turma})


@login_required
@require_POST
def toggle_item(request, pk):
    if not hasattr(request.user, "profile"):
        return JsonResponse({"ok": False}, status=403)
    item = get_object_or_404(AgendaItem, pk=pk,
                             turma=request.user.profile.turma)
    conclusao, _ = Conclusao.objects.get_or_create(usuario=request.user, item=item)
    conclusao.concluida = not conclusao.concluida
    conclusao.concluida_em = timezone.now() if conclusao.concluida else None
    conclusao.save()
    return JsonResponse({"ok": True, "concluida": conclusao.concluida})


class LoginView(auth_views.LoginView):
    template_name = "agenda_app/login.html"
    redirect_authenticated_user = True
