from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def index(request):
    """Главная страница"""
    return render(request, 'cargo/index.html')