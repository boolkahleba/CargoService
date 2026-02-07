from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from cargo.models import User
from cargo.forms import RegistrationForm


def register(request):
    """Регистрация с выбором типа пользователя"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')

            # Редирект в зависимости от типа пользователя
            if user.user_type == 'sender':
                return redirect('sender_dashboard')
            else:
                return redirect('transporter_dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'cargo/auth/register.html', {'form': form})


def custom_login(request):
    """Вход в систему"""
    if request.user.is_authenticated:
        # Редирект уже авторизованных пользователей
        if request.user.user_type == 'sender':
            return redirect('sender_dashboard')
        else:
            return redirect('transporter_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')

                if user.user_type == 'sender':
                    return redirect('sender_dashboard')
                else:
                    return redirect('transporter_dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'cargo/auth/login.html', {'form': form})


def custom_logout(request):
    """Выход из системы"""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('index')