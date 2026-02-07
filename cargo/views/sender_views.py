from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from cargo.models import Order, Sender, Route, Feedback
from cargo.forms import OrderForm, FeedbackForm
from django.views.decorators.http import require_POST


@login_required
def sender_dashboard(request):
    """Дашборд отправителя"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    sender = request.user.sender_profile
    active_orders = Order.objects.filter(sender=sender, status__in=['searching', 'assigned', 'in_transit'])
    completed_orders = Order.objects.filter(sender=sender, status='delivered')

    context = {
        'active_orders': active_orders[:5],
        'completed_orders': completed_orders[:5],
        'total_orders': Order.objects.filter(sender=sender).count(),
    }
    return render(request, 'cargo/sender/dashboard.html', context)


@login_required
def sender_order_create(request):
    """Создание нового заказа"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.sender = request.user.sender_profile
            order.status = 'searching'
            order.save()

            messages.success(request, f'Заказ #{order.id} успешно создан!')
            return redirect('sender_order_detail', order_id=order.id)
    else:
        form = OrderForm()

    context = {
        'form': form,
        'is_edit_mode': False,
    }
    return render(request, 'cargo/sender/order_form.html', context)


@login_required
def sender_orders_list(request):
    """Список всех заявок отправителя"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    orders = Order.objects.filter(sender=request.user.sender_profile).order_by('-date_create')

    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(request, 'cargo/sender/orders_list.html', {'orders': orders})


@login_required
def sender_order_detail(request, order_id):
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    order = get_object_or_404(Order, id=order_id, sender=request.user.sender_profile)
    route = Route.objects.filter(order=order).first()

    # Вычисляем объем груза
    volume = order.length * order.width * order.height

    context = {
        'order': order,
        'route': route,
        'volume': volume,  # Добавляем объем в контекст
    }
    return render(request, 'cargo/sender/order_detail.html', context)


@login_required
def sender_order_track(request, order_id):
    """Отслеживание заказа на карте"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    order = get_object_or_404(Order, id=order_id, sender=request.user.sender_profile)
    route = Route.objects.filter(order=order).first()

    # Подготавливаем координаты для карты
    map_data = {
        'departure': {
            'lat': order.lat_departure,
            'lon': order.lon_departure,
            'address': order.address_departure,
        },
        'arrival': {
            'lat': order.lat_arrival,
            'lon': order.lon_arrival,
            'address': order.address_arrival,
        },
    }

    if route and route.current_lat and route.current_lon:
        map_data['current'] = {
            'lat': route.current_lat,
            'lon': route.current_lon,
        }

    context = {
        'order': order,
        'map_data': map_data,
        'yandex_maps_api_key': 'YOUR_YANDEX_MAPS_API_KEY',  # TODO: Добавить в настройки
    }
    return render(request, 'cargo/sender/order_track.html', context)


@login_required
def sender_order_match(request, order_id):
    """Подбор перевозчиков для заказа - ЗАГЛУШКА"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    order = get_object_or_404(Order, id=order_id, sender=request.user.sender_profile)

    # TODO: Реализовать логику подбора перевозчиков
    context = {
        'order': order,
        'message': 'Функция подбора перевозчиков находится в разработке',
    }
    return render(request, 'cargo/sender/order_match.html', context)


@login_required
def sender_order_feedback(request, order_id):
    """Создание отзыва - ЗАГЛУШКА"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    order = get_object_or_404(Order, id=order_id, sender=request.user.sender_profile)

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.sender = request.user.sender_profile
            feedback.transporter = order.transporter
            feedback.order = order
            feedback.save()
            messages.success(request, 'Отзыв успешно добавлен!')
            return redirect('sender_order_detail', order_id=order.id)
    else:
        form = FeedbackForm()

    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'cargo/sender/order_feedback.html', context)


@login_required
def sender_order_edit(request, order_id):
    """Редактирование существующего заказа"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('index')

    # Получаем заказ и проверяем права доступа
    order = get_object_or_404(Order, id=order_id, sender=request.user.sender_profile)

    # Проверяем, что заказ можно редактировать (только в статусе поиска)
    if order.status != 'searching':
        messages.error(request, 'Заказ можно редактировать только пока он в статусе "Поиск перевозчика"')
        return redirect('sender_order_detail', order_id=order.id)

    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Заказ #{order.id} успешно обновлен!')
            return redirect('sender_order_detail', order_id=order.id)
    else:
        form = OrderForm(instance=order)

    context = {
        'form': form,
        'order': order,
        'is_edit_mode': True,  # Флаг для шаблона
    }
    return render(request, 'cargo/sender/order_form.html', context)


@login_required
@require_POST  # Разрешаем только POST-запросы для безопасности
def sender_order_cancel(request, order_id):
    """Отмена заявки отправителем"""
    if not hasattr(request.user, 'sender_profile'):
        messages.error(request, 'Доступно только для отправителей')
        return redirect('sender_dashboard')

    # Находим заявку, проверяем, что она принадлежит текущему пользователю
    order = get_object_or_404(Order, id=order_id, sender=request.user.sender_profile)

    # Проверяем, можно ли отменить заявку
    if order.status != Order.Status.SEARCHING:
        messages.error(request,
                       'Заявку можно отменить только в статусе "Поиск перевозчика"')
        return redirect('sender_order_detail', order_id=order.id)

    # Меняем статус на "Отменен"
    order.status = Order.Status.CANCELLED
    order.save()

    # Добавляем запись в журнал (опционально)
    messages.success(request, f'Заявка #{order.id} успешно отменена')

    # Перенаправляем на список заявок
    return redirect('sender_orders_list')


