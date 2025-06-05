from django.urls import path
from . import views

app_name = 'fire_detector'

urlpatterns = [
    path('', views.home, name='home'),
    path('detect/', views.detect_fire, name='detect_fire'),
    path('results/<str:file_id>/', views.results, name='results'),
]