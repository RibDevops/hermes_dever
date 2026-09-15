from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .views_crud.gerenciamento import gerenciamento
from .views_crud.portalsecure import crud_portal

from .views_crud.turmas import crud_turma
from .views_crud.usuarios import crud_usuario
urlpatterns = [
    path("turmas/", crud_turma, name="crud_turma"),
    path("usuarios/", crud_usuario, name="crud_usuario"),
    path("", views.dashboard, name="dashboard"),
    path("pendentes/", views.dashboard, {"status": "pendentes"}, name="pendentes"),
    path("concluidas/", views.dashboard, {"status": "concluidas"}, name="concluidas"),
    path("calendario/", views.calendario, name="calendario"),
    path("toggle/<int:pk>/", views.toggle_item, name="toggle_item"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("gerenciamento/", gerenciamento, name="gerenciamento"),
    path("portalsecure/", crud_portal, name="crud_portal"),
]
