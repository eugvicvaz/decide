from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
class HomeView(TemplateView):
    template_name="home.html"
    def home(request):
        context={}
        return render(request,template_name,context)