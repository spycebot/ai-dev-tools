from django.urls import path
from . import views

urlpatterns = [
    path('', views.chore_list, name='chore_list'),
    path('add/', views.add_chore, name='add_chore'),
    path('<int:pk>/complete/', views.complete_chore, name='complete_chore'),
]
