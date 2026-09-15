from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from agenda_app.models import Turma

@login_required
def crud_turma(request):
    turmas = Turma.objects.all()
    if request.method == 'POST':
        from django.utils import timezone
        Turma.objects.create(
            nome=request.POST.get('nome'),
            grade=request.POST.get('grade','12'),
            class_id=request.POST.get('class_id',''),
            profile=request.POST.get('profile','13'),
            school=request.POST.get('school','1846'),
            ativa=bool(request.POST.get('ativa'))
        )
        return redirect('crud_turma')
    return render(request, 'agenda_app/cruds/turma_list.html', {'turmas': turmas})
