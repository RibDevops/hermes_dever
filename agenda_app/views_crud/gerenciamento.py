from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.urls import reverse
from urllib.parse import urlencode

from agenda_app.models import Turma, PortalSecure, UserProfile, AgendaItem, Conclusao
from django.contrib.auth.models import User

TAB_URLS = {
    'turmas': 'gerenciamento_turmas',
    'usuarios': 'gerenciamento_usuarios',
    'credenciais': 'gerenciamento_credenciais',
    'tarefas': 'gerenciamento_tarefas',
    'conclusoes': 'gerenciamento_conclusoes',
}
ALLOWED_TABS = set(TAB_URLS)


def _redirect_canonical(tab, acao=None, obj_id=None):
    url = reverse(TAB_URLS[tab])
    params = {}
    if acao:
        params['acao'] = acao
    if obj_id:
        params['id'] = obj_id
    if params:
        url += '?' + urlencode(params)
    return redirect(url)


@login_required
def gerenciamento(request, tab_url=None):
    # Apenas staff/superuser
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden('Acesso restrito.')

    tab = tab_url or request.GET.get('tab') or request.POST.get('tab') or 'turmas'
    if tab not in ALLOWED_TABS:
        return redirect(reverse('gerenciamento_turmas'))

    # Canonicalizar: /gerenciamento/ ou /gerenciamento/?tab=X -> /gerenciamento/<tab>/
    if not tab_url:
        return _redirect_canonical(
            tab,
            acao=request.POST.get('acao') or request.GET.get('acao'),
            obj_id=request.POST.get('id') or request.GET.get('id'),
        )

    acao = request.POST.get('acao') or request.GET.get('acao')
    obj_id = request.POST.get('id') or request.GET.get('id')

    # ---------- POST: criar / salvar / excluir ----------
    if request.method == 'POST' and acao:
        if tab == 'turmas' and acao in ('criar', 'salvar'):
            if acao == 'criar':
                Turma.objects.create(
                    nome=request.POST['nome'], grade=request.POST.get('grade', '12'),
                    class_id=request.POST.get('class_id', ''), profile=request.POST.get('profile', '13'),
                    school=request.POST.get('school', '1846'), ativa=bool(request.POST.get('ativa')))
            else:
                t = get_object_or_404(Turma, id=obj_id)
                t.nome = request.POST['nome']
                t.grade = request.POST.get('grade', '12')
                t.class_id = request.POST.get('class_id', t.class_id)
                t.profile = request.POST.get('profile', t.profile)
                t.school = request.POST.get('school', t.school)
                t.ativa = bool(request.POST.get('ativa'))
                t.save()
            messages.success(request, 'Turma salva.')
            return redirect(reverse('gerenciamento_turmas'))
        if tab == 'turmas' and acao == 'excluir_confirmado':
            t = get_object_or_404(Turma, id=obj_id)
            t.delete()
            messages.success(request, 'Turma excluída.')
            return redirect(reverse('gerenciamento_turmas'))

        if tab == 'usuarios' and acao in ('criar', 'salvar'):
            if acao == 'criar':
                u = User.objects.create_user(
                    username=request.POST.get('username'),
                    email=request.POST.get('email', ''),
                    password=request.POST.get('password') or None,
                )
                turma = get_object_or_404(Turma, id=request.POST.get('turma'))
                UserProfile.objects.create(
                    user=u, turma=turma,
                    nome_completo=request.POST.get('nome_completo', ''))
            else:
                u = get_object_or_404(User, id=obj_id)
                u.username = request.POST.get('username', u.username)
                u.email = request.POST.get('email', u.email)
                if request.POST.get('password'):
                    u.set_password(request.POST.get('password'))
                u.save()
                turma_id = request.POST.get('turma')
                if turma_id:
                    profile, _ = UserProfile.objects.get_or_create(
                        user=u, defaults={'turma_id': turma_id})
                    profile.turma = get_object_or_404(Turma, id=turma_id)
                    profile.nome_completo = request.POST.get(
                        'nome_completo', profile.nome_completo)
                    profile.save()
            messages.success(request, 'Usuário salvo.')
            return redirect(reverse('gerenciamento_usuarios'))
        if tab == 'usuarios' and acao == 'excluir_confirmado':
            u = get_object_or_404(User, id=obj_id)
            u.delete()
            messages.success(request, 'Usuário excluído.')
            return redirect(reverse('gerenciamento_usuarios'))

        if tab == 'credenciais' and acao in ('criar', 'salvar'):
            turma = get_object_or_404(Turma, id=request.POST.get('turma'))
            ps, _ = PortalSecure.objects.get_or_create(turma=turma)
            ps.usuario_portal = request.POST.get('usuario_portal', ps.usuario_portal)
            if request.POST.get('senha'):
                ps.set_password(request.POST.get('senha'))
            ps.save()
            messages.success(request, 'Credencial salva (senha criptografada).')
            return redirect(reverse('gerenciamento_credenciais'))
        if tab == 'credenciais' and acao == 'excluir_confirmado':
            ps = get_object_or_404(PortalSecure, id=obj_id)
            ps.delete()
            messages.success(request, 'Credencial excluída.')
            return redirect(reverse('gerenciamento_credenciais'))

    # ---------- Telas de criar / editar / excluir ----------
    if acao == 'criar' or (acao == 'editar' and obj_id):
        if tab == 'turmas':
            obj = get_object_or_404(Turma, id=obj_id) if acao == 'editar' and obj_id else None
            return render(request, 'agenda_app/gerenciamento/turma_form.html', {'obj': obj, 'tab': tab})
        if tab == 'usuarios':
            obj = get_object_or_404(User, id=obj_id) if acao == 'editar' and obj_id else None
            turmas = Turma.objects.filter(ativa=True)
            return render(request, 'agenda_app/gerenciamento/usuario_form.html',
                          {'obj': obj, 'tab': tab, 'turmas': turmas})
        if tab == 'credenciais':
            obj = get_object_or_404(PortalSecure, id=obj_id) if acao == 'editar' and obj_id else None
            turmas = Turma.objects.filter(ativa=True)
            return render(request, 'agenda_app/gerenciamento/credencial_form.html',
                          {'obj': obj, 'tab': tab, 'turmas': turmas})
        # tarefas / conclusoes sao somente leitura
        return _redirect_canonical(tab)

    if acao == 'excluir' and obj_id:
        if tab == 'turmas':
            obj = get_object_or_404(Turma, id=obj_id)
            return render(request, 'agenda_app/gerenciamento/turma_confirmar_excluir.html', {'obj': obj, 'tab': tab})
        if tab == 'usuarios':
            obj = get_object_or_404(User, id=obj_id)
            return render(request, 'agenda_app/gerenciamento/usuario_confirmar_excluir.html', {'obj': obj, 'tab': tab})
        if tab == 'credenciais':
            obj = get_object_or_404(PortalSecure, id=obj_id)
            return render(request, 'agenda_app/gerenciamento/credencial_confirmar_excluir.html', {'obj': obj, 'tab': tab})
        return _redirect_canonical(tab)

    # ---------- Listas ----------
    contexto = {'tab': tab}
    if tab == 'turmas':
        contexto['turmas'] = Turma.objects.all()
        return render(request, 'agenda_app/gerenciamento/turma_list.html', contexto)
    if tab == 'usuarios':
        contexto['usuarios'] = User.objects.select_related('profile').all()
        contexto['turmas'] = Turma.objects.filter(ativa=True)
        return render(request, 'agenda_app/gerenciamento/usuario_list.html', contexto)
    if tab == 'credenciais':
        contexto['portais'] = PortalSecure.objects.select_related('turma').all()
        return render(request, 'agenda_app/gerenciamento/credencial_list.html', contexto)
    if tab == 'tarefas':
        contexto['tarefas'] = AgendaItem.objects.select_related('turma').all()[:100]
        return render(request, 'agenda_app/gerenciamento/tarefa_list.html', contexto)
    if tab == 'conclusoes':
        contexto['conclusoes'] = Conclusao.objects.select_related('usuario', 'item').all()[:100]
        return render(request, 'agenda_app/gerenciamento/conclusao_list.html', contexto)

    return redirect(reverse('gerenciamento_turmas'))
