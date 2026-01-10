from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def profile_settings(request):
    """Настройки профиля - ЗАГЛУШКА"""
    context = {
        'message': 'Функция настройки профиля находится в разработке',
        'user': request.user,
    }
    return render(request, 'cargo/common/profile_settings.html', context)

@login_required
def notifications_list(request):
    """Список уведомлений - ЗАГЛУШКА"""
    context = {
        'message': 'Функция уведомлений находится в разработке',
        'notifications': [],  # Пустой список для заглушки
    }
    return render(request, 'cargo/common/notifications.html', context)