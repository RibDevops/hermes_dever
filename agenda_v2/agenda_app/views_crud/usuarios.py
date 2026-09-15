from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from agenda_app.models import UserProfile, Turma

@login_required
def crud_usuario(request):
    usuarios = User.objects.select_related('profile').all()
    turmas = Turma.objects.filter(ativa=True)
    if request.method == 'POST':
        u = User.objects.create_user(
            username=request.POST.get('username'),
            email=request.POST.get('email',''),
            password=request.POST.get('password')
        )
        turma = Turma.objects.get(id=request.POST.get('turma'))
        UserProfile.objects.create(user=u, turma=turma)
        return redirect('crud_usuario')
    return render(request, 'agenda_app/cruds/usuario_list.html', {'usuarios': usuarios, 'turmas': turmas})
