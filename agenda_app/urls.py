from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('toggle/<int:pk>/', views.toggle_complete, name='toggle_complete'),
]
