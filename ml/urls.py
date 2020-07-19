from django.urls import path
from . import views

app_name = 'ml'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload', views.upload, name='upload')
]