from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from agenda_app.models import PortalSecure, Turma

@login_required
@staff_member_required
def crud_portal(request):
    itens = PortalSecure.objects.select_related('turma').all()
    return render(request, 'agenda_app/portalsecure/list.html', {'itens': itens})

@login_required
@staff_member_required
def crud_portal_create(request):
    if request.method == 'POST':
        turma = get_object_or_404(Turma, id=request.POST.get('turma'))
        ps, _ = PortalSecure.objects.get_or_create(turma=turma)
        ps.usuario_portal = request.POST.get('usuario_portal')
        if request.POST.get('senha'):
            ps.set_password(request.POST.get('senha'))
        ps.save()
        messages.success(request, 'Credencial salva (senha criptografada).')
        return redirect('crud_portal')
    turmas = Turma.objects.all()
    return render(request, 'agenda_app/portalsecure/form.html', {'turmas': turmas})
