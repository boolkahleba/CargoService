from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Sender, Transporter, Order, Transport, Route, Feedback


# 1. Настройка для модели User
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Поля для отображения в списке
    list_display = ('username', 'email', 'phone', 'user_type', 'is_staff')

    # Поля для поиска
    search_fields = ('username', 'email', 'phone')

    # Фильтры в правой панели
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')

    # Порядок и группировка полей на странице редактирования
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email', 'phone')}),  # Убраны first_name, last_name
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'user_type'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Поля при создании пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'user_type', 'password1', 'password2'),
        }),
    )

    def get_fields(self, request, obj=None):
        """Удаляем first_name и last_name из списка полей"""
        fields = super().get_fields(request, obj)
        # Удаляем поля, которые удалены из модели
        fields_to_remove = ['first_name', 'last_name']
        return [f for f in fields if f not in fields_to_remove]

    def get_form(self, request, obj=None, **kwargs):
        """Удаляем поля из формы"""
        form = super().get_form(request, obj, **kwargs)

        # Удаляем поля из формы, если они там появились
        if 'first_name' in form.base_fields:
            del form.base_fields['first_name']
        if 'last_name' in form.base_fields:
            del form.base_fields['last_name']

        return form


# 2. Профиль Отправителя (inline для User)
class SenderInline(admin.StackedInline):
    model = Sender
    can_delete = False
    verbose_name_plural = 'Профиль отправителя'
    fk_name = 'user'


# 3. Профиль Перевозчика (inline для User)
class TransporterInline(admin.StackedInline):
    model = Transporter
    can_delete = False
    verbose_name_plural = 'Профиль перевозчика'
    fk_name = 'user'


# 4. Добавляем inlines к UserAdmin
UserAdmin.inlines = [SenderInline, TransporterInline]


# 5. Модель Заказа
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Отображение в списке
    list_display = ('id', 'sender_name', 'transporter_name', 'status', 'weight', 'coast', 'date_create_display')

    # Поиск
    search_fields = ('id', 'sender__name', 'transporter__name', 'address_departure', 'address_arrival')

    # Фильтры
    list_filter = ('status', 'date_create', 'date_departure_plan')

    # Поля для быстрого редактирования прямо в списке
    list_editable = ('status',)

    # Разделы на странице редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': ('sender', 'transporter', 'status', 'coast')
        }),
        ('Характеристики груза', {
            'fields': ('weight', 'height', 'width', 'length'),
            'classes': ('collapse',)  # Сворачиваемый раздел
        }),
        ('Адреса и координаты', {
            'fields': ('address_departure', 'address_arrival',
                       'lat_departure', 'lon_departure',
                       'lat_arrival', 'lon_arrival')
        }),
        ('Даты', {
            'fields': ('date_departure_plan', 'date_arrival_plan',
                       'date_departure_fact', 'date_arrival_fact')
        }),
    )

    # Автоматическое заполнение некоторых полей
    readonly_fields = ('date_create',)

    # Для связанных полей используем поиск (удобно при большом количестве записей)
    raw_id_fields = ('sender', 'transporter')

    # Кастомные методы для отображения
    def sender_name(self, obj):
        return obj.sender.name if obj.sender else "-"

    sender_name.short_description = "Отправитель"

    def transporter_name(self, obj):
        return obj.transporter.name if obj.transporter else "-"

    transporter_name.short_description = "Перевозчик"

    def date_create_display(self, obj):
        return obj.date_create.strftime("%d.%m.%Y %H:%M")

    date_create_display.short_description = "Дата создания"

    # Действия в админке
    actions = ['mark_as_delivered', 'mark_as_cancelled']

    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered')
        self.message_user(request, f"{updated} заказов помечены как доставленные")

    mark_as_delivered.short_description = "Пометить как доставленные"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"{updated} заказов помечены как отмененные")

    mark_as_cancelled.short_description = "Пометить как отмененные"


# 6. Модель Транспорта
@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ('type', 'transporter_name', 'capacity', 'length', 'width', 'height', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('transporter__name',)
    list_editable = ('is_active',)

    def transporter_name(self, obj):
        return obj.transporter.name

    transporter_name.short_description = "Владелец"


# 7. Модель Маршрута
@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_id', 'transport_info', 'current_coords', 'updated_at_display')
    list_filter = ('date_departure_plan',)
    search_fields = ('order__id',)
    raw_id_fields = ('order', 'transport')

    def order_id(self, obj):
        return f"Заказ #{obj.order.id}"

    order_id.short_description = "Заказ"

    def transport_info(self, obj):
        if obj.transport:
            return f"{obj.transport.get_type_display()} ({obj.transport.transporter.name})"
        return "-"

    transport_info.short_description = "Транспорт"

    def current_coords(self, obj):
        if obj.current_lat and obj.current_lon:
            return f"{obj.current_lat:.4f}, {obj.current_lon:.4f}"
        return "Не указано"

    current_coords.short_description = "Текущие координаты"

    def updated_at_display(self, obj):
        return obj.updated_at.strftime("%d.%m.%Y %H:%M")

    updated_at_display.short_description = "Обновлено"


# 8. Модель Отзыва
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender_name', 'transporter_name', 'order_id', 'score', 'created_at_display')
    list_filter = ('score', 'created_at')
    search_fields = ('sender__name', 'transporter__name', 'text')
    raw_id_fields = ('sender', 'transporter', 'order')

    def sender_name(self, obj):
        return obj.sender.name

    sender_name.short_description = "Отправитель"

    def transporter_name(self, obj):
        return obj.transporter.name

    transporter_name.short_description = "Перевозчик"

    def order_id(self, obj):
        return f"Заказ #{obj.order.id}"

    order_id.short_description = "Заказ"

    def created_at_display(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    created_at_display.short_description = "Дата отзыва"


# 9. Дополнительная настройка админ-панели
admin.site.site_header = "Администрирование CargoService"
admin.site.site_title = "CargoService"
admin.site.index_title = "Панель управления сервисом грузоперевозок"

# 10. Группировка моделей в админке
# (Опционально) Чтобы сгруппировать ваши модели отдельно от стандартных
from django.apps import apps

cargo_app = apps.get_app_config('cargo')
cargo_app.verbose_name = "Грузоперевозки"