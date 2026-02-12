from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from cargo.models import Transport, Order, Route, Transporter, Feedback
from cargo.forms import TransportForm, OrderSearchForm
from django.db import models
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
import json


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
    """Поиск подходящих заказов для перевозчика"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    transporter = request.user.transporter_profile
    available_vehicles = Transport.objects.filter(transporter=transporter, is_active=True)

    # Получаем параметры поиска
    form = OrderSearchForm(request.GET or None)
    orders = Order.objects.filter(status='searching').select_related('sender')

    if form.is_valid():
        # Фильтрация по весу
        weight_min = form.cleaned_data.get('weight_min')
        weight_max = form.cleaned_data.get('weight_max')

        if weight_min:
            orders = orders.filter(weight__gte=weight_min)
        if weight_max:
            orders = orders.filter(weight__lte=weight_max)

        # Фильтрация по стоимости
        coast_min = form.cleaned_data.get('coast_min')
        if coast_min:
            orders = orders.filter(coast__gte=coast_min)

        # Фильтрация по датам
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')

        if date_from:
            orders = orders.filter(date_departure_plan__date__gte=date_from)
        if date_to:
            orders = orders.filter(date_departure_plan__date__lte=date_to)

        # Сортировка
        sort_by = form.cleaned_data.get('sort_by', '-date_create')
        orders = orders.order_by(sort_by)

        # Автоматический подбор под транспорт
        auto_match = form.cleaned_data.get('auto_match', True)
        if auto_match and available_vehicles.exists():
            # Получаем максимальные параметры доступного транспорта
            max_capacity = available_vehicles.aggregate(models.Max('capacity'))['capacity__max'] or 0
            max_length = available_vehicles.aggregate(models.Max('length'))['length__max'] or 0
            max_width = available_vehicles.aggregate(models.Max('width'))['width__max'] or 0
            max_height = available_vehicles.aggregate(models.Max('height'))['height__max'] or 0

            orders = orders.filter(
                weight__lte=max_capacity,
                length__lte=max_length,
                width__lte=max_width,
                height__lte=max_height
            )

    # Помечаем подходящие заказы
    matched_orders = []
    for order in orders:
        order.is_matched = False
        order.suitable_vehicles = []

        if available_vehicles.exists():
            # Проверяем каждый транспорт на соответствие
            for vehicle in available_vehicles:
                if (order.weight <= vehicle.capacity and
                        order.length <= vehicle.length and
                        order.width <= vehicle.width and
                        order.height <= vehicle.height):
                    order.is_matched = True
                    order.suitable_vehicles.append(vehicle)

        matched_orders.append(order)

    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(matched_orders, 10)

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'lat_dep': order.lat_departure,
            'lon_dep': order.lon_departure,
            'lat_arr': order.lat_arrival,
            'lon_arr': order.lon_arrival,
            'address_dep': order.address_departure,
            'address_arr': order.address_arrival,
        })

    context = {
        'form': form,
        'orders': orders_page,
        'available_vehicles': available_vehicles,
        'search_performed': bool(request.GET),
        'total_found': len(matched_orders),
        'orders_data_json': json.dumps(orders_data),
        'YANDEX_MAPS_API_KEY': settings.YANDEX_MAPS_API_KEY,
    }

    return render(request, 'cargo/transporter/orders_search.html', context)


@login_required
@require_POST
def transporter_accept_order(request, order_id):
    """Принятие заказа перевозчиком"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    order = get_object_or_404(Order, id=order_id, status='searching')
    transporter = request.user.transporter_profile

    # Проверяем, что перевозчик не берет свой же заказ
    if order.sender == transporter:
        messages.error(request, 'Вы не можете принять свой собственный заказ')
        return redirect('transporter_orders_search')

    # Получаем выбранный транспорт
    vehicle_id = request.POST.get('vehicle_id')
    if not vehicle_id:
        messages.error(request, 'Не выбран транспорт для выполнения заказа')
        return redirect('transporter_orders_search')

    vehicle = get_object_or_404(Transport, id=vehicle_id, transporter=transporter)

    # Дополнительная проверка совместимости
    if (order.weight > vehicle.capacity or
            order.length > vehicle.length or
            order.width > vehicle.width or
            order.height > vehicle.height):
        messages.error(request, 'Транспорт не подходит по параметрам груза')
        return redirect('transporter_orders_search')

    # Назначаем заказ перевозчику
    order.transporter = transporter
    order.status = 'assigned'
    order.save()

    # Создаем маршрут
    Route.objects.create(
        order=order,
        transport=vehicle,
        date_departure_plan=order.date_departure_plan,
        date_arrival_plan=order.date_arrival_plan,
    )

    messages.success(request, f'Заказ #{order.id} успешно принят!')
    return redirect('transporter_active_orders')


@login_required
def transporter_order_detail(request, order_id):
    """Детали заказа для перевозчика"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    transporter = request.user.transporter_profile
    order = get_object_or_404(Order, id=order_id)

    # Проверяем, имеет ли перевозчик доступ к этому заказу
    if order.status == 'searching':
        # Заказ в поиске - доступен всем перевозчикам для просмотра
        is_accessible = True
        can_accept = True
    elif order.transporter == transporter:
        # Заказ принадлежит текущему перевозчику
        is_accessible = True
        can_accept = False
    else:
        # Заказ принадлежит другому перевозчику
        is_accessible = False
        can_accept = False

    if not is_accessible:
        messages.error(request, 'У вас нет доступа к этому заказу')
        return redirect('transporter_orders_search')

    # Получаем связанные данные
    route = Route.objects.filter(order=order).first()
    feedback = Feedback.objects.filter(order=order).first()

    # Получаем доступный транспорт перевозчика
    available_vehicles = Transport.objects.filter(transporter=transporter, is_active=True)

    # Проверяем совместимость заказа с транспортом перевозчика
    suitable_vehicles = []
    if can_accept and available_vehicles.exists():
        for vehicle in available_vehicles:
            if (order.weight <= vehicle.capacity and
                    order.length <= vehicle.length and
                    order.width <= vehicle.width and
                    order.height <= vehicle.height):
                suitable_vehicles.append(vehicle)

    # Обработка принятия заказа
    if request.method == 'POST' and 'accept_order' in request.POST:
        if not can_accept:
            messages.error(request, 'Вы не можете принять этот заказ')
            return redirect('transporter_order_detail', order_id=order.id)

        vehicle_id = request.POST.get('vehicle_id')
        if not vehicle_id:
            messages.error(request, 'Выберите транспортное средство')
            return redirect('transporter_order_detail', order_id=order.id)

        vehicle = get_object_or_404(Transport, id=vehicle_id, transporter=transporter)

        # Назначаем заказ перевозчику
        order.transporter = transporter
        order.status = 'assigned'
        order.save()

        # Создаем маршрут
        Route.objects.create(
            order=order,
            transport=vehicle,
            date_departure_plan=order.date_departure_plan,
            date_arrival_plan=order.date_arrival_plan,
        )

        messages.success(request, f'Заказ #{order.id} успешно принят!')
        return redirect('transporter_active_orders')

    # Обработка обновления статуса
    if request.method == 'POST' and 'update_status' in request.POST:
        if order.transporter != transporter:
            messages.error(request, 'Вы не можете изменять статус этого заказа')
            return redirect('transporter_order_detail', order_id=order.id)

        new_status = request.POST.get('status')
        valid_statuses = ['in_transit', 'delivered']

        if new_status in valid_statuses:
            order.status = new_status

            # Обновляем фактические даты в маршруте
            if route:
                if new_status == 'in_transit':
                    route.date_departure_fact = timezone.now()
                elif new_status == 'delivered':
                    route.date_arrival_fact = timezone.now()
                route.save()

            order.save()
            messages.success(request, f'Статус заказа обновлен на "{order.get_status_display()}"')
            return redirect('transporter_order_detail', order_id=order.id)

    # Обработка обновления координат
    if request.method == 'POST' and 'update_coords' in request.POST:
        if order.transporter != transporter:
            messages.error(request, 'Вы не можете обновлять координаты этого заказа')
            return redirect('transporter_order_detail', order_id=order.id)

        if route:
            current_lat = request.POST.get('current_lat')
            current_lon = request.POST.get('current_lon')

            if current_lat and current_lon:
                try:
                    route.current_lat = float(current_lat)
                    route.current_lon = float(current_lon)
                    route.updated_at = timezone.now()
                    route.save()
                    messages.success(request, 'Координаты успешно обновлены')
                except ValueError:
                    messages.error(request, 'Некорректные координаты')

        return redirect('transporter_order_detail', order_id=order.id)

    timeline_steps = [
        "Создан",
        "В поиске перевозчика",
        "Назначен перевозчик",
        "Груз в пути",
        "Доставлен"
    ]

    context = {
        'order': order,
        'route': route,
        'feedback': feedback,
        'can_accept': can_accept,
        'suitable_vehicles': suitable_vehicles,
        'has_suitable_vehicles': len(suitable_vehicles) > 0,
        'available_vehicles': available_vehicles,
        'now': timezone.now(),
        'timeline_steps': timeline_steps,
        'YANDEX_MAPS_API_KEY': settings.YANDEX_MAPS_API_KEY,
    }

    return render(request, 'cargo/transporter/order_detail.html', context)

@login_required
def transporter_routes(request):
    """Планирование маршрутов - ЗАГЛУШКА"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

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
    return render(request, 'cargo/transporter/active_orders.html', context)


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


@login_required
@require_POST
def transporter_vehicle_toggle(request, vehicle_id):
    """Переключение статуса активности транспорта"""
    if not hasattr(request.user, 'transporter_profile'):
        return JsonResponse({'success': False, 'error': 'Доступ запрещен'})

    vehicle = get_object_or_404(
        Transport,
        id=vehicle_id,
        transporter=request.user.transporter_profile
    )

    vehicle.is_active = not vehicle.is_active
    vehicle.save()

    return JsonResponse({
        'success': True,
        'is_active': vehicle.is_active,
        'message': f'Транспорт {"активирован" if vehicle.is_active else "деактивирован"}'
    })


@login_required
def transporter_active_orders(request):
    """Просмотр активных заказов перевозчика"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    transporter = request.user.transporter_profile

    # Получаем активные заказы (assigned или in_transit)
    active_orders = Order.objects.filter(
        transporter=transporter,
        status__in=['assigned', 'in_transit']
    ).order_by('-date_create')

    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter and status_filter in ['assigned', 'in_transit']:
        active_orders = active_orders.filter(status=status_filter)

    # Фильтрация по дате
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        active_orders = active_orders.filter(date_create__date__gte=date_from)
    if date_to:
        active_orders = active_orders.filter(date_create__date__lte=date_to)

    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(active_orders, 10)  # 10 заказов на странице

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    context = {
        'orders': orders_page,
        'total_orders': active_orders.count(),
        'assigned_count': active_orders.filter(status='assigned').count(),
        'in_transit_count': active_orders.filter(status='in_transit').count(),
    }

    return render(request, 'cargo/transporter/active_orders.html', context)


@login_required
@require_POST
def transporter_update_order_status(request, order_id):
    """Обновление статуса заказа перевозчиком"""
    if not hasattr(request.user, 'transporter_profile'):
        messages.error(request, 'Доступно только для перевозчиков')
        return redirect('index')

    order = get_object_or_404(
        Order,
        id=order_id,
        transporter=request.user.transporter_profile
    )

    new_status = request.POST.get('status')

    # Проверяем допустимые переходы статусов
    valid_transitions = {
        'assigned': ['in_transit'],
        'in_transit': ['delivered'],
    }

    if (order.status in valid_transitions and
            new_status in valid_transitions[order.status]):

        order.status = new_status

        # Обновляем фактические даты в маршруте
        route = Route.objects.filter(order=order).first()
        if route:
            if new_status == 'in_transit':
                route.date_departure_fact = timezone.now()
            elif new_status == 'delivered':
                route.date_arrival_fact = timezone.now()
            route.save()

        order.save()
        messages.success(request, f'Статус заказа #{order.id} обновлен на "{order.get_status_display()}"')
    else:
        messages.error(request, 'Недопустимое изменение статуса')

    return redirect('transporter_active_orders')

