from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path('', views.index, name='index'),
    path('<int:area>/', views.area, name='area'),
    path('<int:area>/<int:week>/', views.week, name='week'),
    path('<int:area>/<int:week>/<str:color>/', views.color, name='color'),
    path('<int:area>/<int:week>/<str:color>/png', views.color_png, name='color_png'),
]
