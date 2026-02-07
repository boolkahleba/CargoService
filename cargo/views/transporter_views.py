from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from cargo.models import Transport, Order, Route, Transporter
from cargo.forms import TransportForm
from django.db import models
from django.views.decorators.http import require_POST


@login_required
def transporter_dashboard(request):
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    transporter = request.user.transporter_profile

    # Получаем данные для дашборда
    active_orders = Order.objects.filter(
        transporter=transporter,
        status__in=['assigned', 'in_transit']
    ).order_by('-date_create')[:5]

    vehicles = Transport.objects.filter(transporter=transporter, is_active=True)

    # Рассчитываем общий заработок
    completed_orders = Order.objects.filter(
        transporter=transporter,
        status='delivered'
    )
    total_earnings = completed_orders.aggregate(
        total=models.Sum('coast')
    )['total'] or 0

    # Считаем количество выполненных заказов
    completed_orders_count = completed_orders.count()

    context = {
        'active_orders': active_orders,
        'vehicles': vehicles,
        'total_earnings': total_earnings,
        'completed_orders_count': completed_orders_count,
    }
    return render(request, 'cargo/transporter/dashboard.html', context)


@login_required
def transporter_vehicles(request):
    """Управление транспортными средствами"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    vehicles = Transport.objects.filter(transporter=request.user.transporter_profile)
    return render(request, 'cargo/transporter/vehicles.html', {'vehicles': vehicles})


@login_required
def transporter_vehicle_add(request):
    """Добавление нового транспорта"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    if request.method == 'POST':
        form = TransportForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.transporter = request.user.transporter_profile
            vehicle.is_active = True  # Новый транспорт по умолчанию активен
            vehicle.save()
            messages.success(request, f'Транспортное средство "{vehicle.get_type_display()}" успешно добавлено!')
            return redirect('transporter_vehicles')
    else:
        form = TransportForm()

    return render(request, 'cargo/transporter/vehicle_add.html', {'form': form})


@login_required
def transporter_orders_search(request):
    """Поиск подходящих заказов"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    transporter = request.user.transporter_profile
    available_vehicles = Transport.objects.filter(transporter=transporter, is_active=True)

    # Фильтры из GET-параметров
    weight_min = request.GET.get('weight_min')
    weight_max = request.GET.get('weight_max')
    # TODO: Добавить больше фильтров

    # Базовый запрос - заказы в поиске перевозчика
    orders = Order.objects.filter(status='searching')

    # TODO: Добавить сложную логику подбора
    # по совпадению маршрутов, типу транспорта и т.д.

    return render(request, 'cargo/transporter/orders_search.html', {
        'orders': orders,
        'vehicles': available_vehicles,
    })


@login_required
def transporter_order_detail(request, order_id):
    """Детали заказа для перевозчика"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST' and 'accept_order' in request.POST:
        # Принятие заказа
        order.transporter = request.user.transporter_profile
        order.status = 'assigned'
        order.save()

        # Создание маршрута
        Route.objects.create(
            order=order,
            transport=request.user.transporter_profile.transports.first(),  # TODO: Выбор транспорта
            date_departure_plan=order.date_departure_plan,
            date_arrival_plan=order.date_arrival_plan,
        )

        messages.success(request, 'Заказ принят!')
        return redirect('transporter_dashboard')

    return render(request, 'cargo/transporter/order_detail.html', {'order': order})


# cargo/views/transporter_views.py (дополните в конец файла)

@login_required
def transporter_routes(request):
    """Планирование маршрутов - ЗАГЛУШКА"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    # TODO: Реализовать логику планирования маршрутов
    context = {
        'message': 'Функция планирования маршрутов находится в разработке',
    }
    return render(request, 'cargo/transporter/routes.html', context)


@login_required
def transporter_orders_list(request):
    """Список заказов перевозчика - ЗАГЛУШКА"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    transporter = request.user.transporter_profile
    orders = Order.objects.filter(transporter=transporter).order_by('-date_create')

    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
    }
    return render(request, 'cargo/transporter/orders_list.html', context)


@login_required
def transporter_vehicle_edit(request, vehicle_id):
    """Редактирование транспортного средства"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    # Получаем транспорт, проверяя, что он принадлежит текущему перевозчику
    vehicle = get_object_or_404(
        Transport,
        id=vehicle_id,
        transporter=request.user.transporter_profile
    )

    if request.method == 'POST':
        form = TransportForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f'Транспорт "{vehicle.get_type_display()}" успешно обновлен!')
            return redirect('transporter_vehicles')
    else:
        form = TransportForm(instance=vehicle)

    return render(request, 'cargo/transporter/vehicle_edit.html', {
        'form': form,
        'vehicle': vehicle
    })


@login_required
@require_POST
def transporter_vehicle_delete(request, vehicle_id):
    """Удаление транспортного средства"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    # Получаем транспорт, проверяя, что он принадлежит текущему перевозчику
    vehicle = get_object_or_404(
        Transport,
        id=vehicle_id,
        transporter=request.user.transporter_profile
    )

    vehicle_type = vehicle.get_type_display()
    vehicle.delete()

    messages.success(request, f'Транспорт "{vehicle_type}" успешно удален!')
    return redirect('transporter_vehicles')
