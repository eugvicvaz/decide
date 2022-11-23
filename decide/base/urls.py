from django.urls import path
from .views import HomeView
from django.conf.urls import url

urlpatterns = [
    url('',HomeView.as_view(),name='home'),
]
