
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from agenda_app.models import Turma, PortalSecure, UserProfile, AgendaItem, Conclusao
from django.contrib.auth.models import User

@login_required
def gerenciamento(request):
    tab = request.GET.get('tab') or 'turmas'
    acao = request.POST.get('acao') or request.GET.get('acao')
    obj_id = request.POST.get('id') or request.GET.get('id')
    
    # POST: criar/editar/excluir
    if request.method == 'POST' and acao:
        if tab == 'turmas' and acao in ('criar','salvar'):
            if acao == 'criar':
                Turma.objects.create(
                    nome=request.POST['nome'], grade=request.POST.get('grade','12'),
                    class_id=request.POST.get('class_id',''), profile=request.POST.get('profile','13'),
                    school=request.POST.get('school','1846'), ativa=bool(request.POST.get('ativa')))
            else:
                t = get_object_or_404(Turma, id=obj_id)
                t.nome = request.POST['nome']
                t.grade = request.POST.get('grade','12')
                t.save()
            messages.success(request, 'Turma salva.')
            return redirect('/gerenciamento/?tab=turmas')
        if tab == 'turmas' and acao == 'excluir_confirmado':
            t = get_object_or_404(Turma, id=obj_id)
            t.delete()
            messages.success(request, 'Turma excluída.')
            return redirect('/gerenciamento/?tab=turmas')
    
    # Renderizar telas específicas (não admin Django)
    if acao == 'criar' or (acao == 'editar' and obj_id):
        obj = get_object_or_404(Turma, id=obj_id) if acao == 'editar' and obj_id else None
        return render(request, 'agenda_app/gerenciamento/turma_form.html', {'obj': obj, 'tab': tab})
    
    if acao == 'excluir' and obj_id:
        obj = get_object_or_404(Turma, id=obj_id)
        return render(request, 'agenda_app/gerenciamento/turma_confirmar_excluir.html', {'obj': obj, 'tab': tab})
    
    # Padrão: listar
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
    # Fallback
    contexto['turmas'] = Turma.objects.all()
    contexto['usuarios'] = User.objects.select_related('profile').all()
    contexto['portais'] = PortalSecure.objects.select_related('turma').all()
    contexto['tarefas'] = AgendaItem.objects.select_related('turma').all()[:50]
    contexto['conclusoes'] = Conclusao.objects.select_related('usuario','item').all()[:50]
    return render(request, 'agenda_app/gerenciamento/index.html', contexto)
