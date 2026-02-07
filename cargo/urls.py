from django.urls import path, include
from .views.views import index
from .views.auth_views import register, custom_login, custom_logout
from .views.sender_views import sender_dashboard, sender_order_create, sender_orders_list, sender_order_detail, \
    sender_order_match, sender_order_track, sender_order_feedback, sender_order_edit, sender_order_cancel
from .views.transporter_views import transporter_dashboard, transporter_vehicles, transporter_vehicle_add, \
    transporter_order_detail, transporter_orders_search, transporter_routes, transporter_orders_list, \
    transporter_vehicle_edit, transporter_vehicle_delete
from .views.common_views import profile_settings, notifications_list

urlpatterns = [
    # Общие страницы
    path('', index, name='index'),
    path('register/', register, name='register'),
    path('login/', custom_login, name='login'),
    path('logout/', custom_logout, name='logout'),

    # Личный кабинет отправителя
    path('sender/', include([
        path('dashboard/', sender_dashboard, name='sender_dashboard'),
        path('order/create/', sender_order_create, name='sender_order_create'),
        path('orders/', sender_orders_list, name='sender_orders_list'),
        path('order/<int:order_id>/', sender_order_detail, name='sender_order_detail'),
        path('order/<int:order_id>/track/', sender_order_track, name='sender_order_track'),
        path('order/<int:order_id>/match/', sender_order_match, name='sender_order_match'),
        path('order/<int:order_id>/feedback/', sender_order_feedback, name='sender_order_feedback'),
        path('order/<int:order_id>/edit/', sender_order_edit, name='sender_order_edit'),
        path('order/<int:order_id>/cancel/', sender_order_cancel, name='sender_order_cancel'),
    ])),

    # Личный кабинет перевозчика
    path('transporter/', include([
        path('dashboard/', transporter_dashboard, name='transporter_dashboard'),
        path('vehicles/', transporter_vehicles, name='transporter_vehicles'),
        path('vehicles/add/', transporter_vehicle_add, name='transporter_vehicle_add'),
        path('routes/', transporter_routes, name='transporter_routes'),
        path('orders/search/', transporter_orders_search, name='transporter_orders_search'),
        path('orders/', transporter_orders_list, name='transporter_orders_list'),
        path('order/<int:order_id>/', transporter_order_detail, name='transporter_order_detail'),
        path('vehicles/<int:vehicle_id>/edit/', transporter_vehicle_edit, name='transporter_vehicle_edit'),
        path('vehicles/<int:vehicle_id>/delete/', transporter_vehicle_delete, name='transporter_vehicle_delete'),
    ])),

    # Общие страницы профиля
    path('profile/settings/', profile_settings, name='profile_settings'),
    path('notifications/', notifications_list, name='notifications_list'),
]
