# cargo/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser


# 1. Модель Пользователя (расширяем встроенную)
class User(AbstractUser):
    # Убираем стандартные поля first_name/last_name, если используем своё поле name в профилях
    first_name = None
    last_name = None

    # USER_TYPE_CHOICES определяет роли в системе
    class UserType(models.TextChoices):
        SENDER = 'sender', 'Отправитель'
        TRANSPORTER = 'transporter', 'Перевозчик'
        ADMIN = 'admin', 'Администратор'

    # Поле user_type использует выбор из предопределенных ролей
    user_type = models.CharField(
        max_length=15,
        choices=UserType.choices,
        default=UserType.SENDER,
        verbose_name='Тип пользователя'
    )
    # Уникальные контакты
    email = models.EmailField(unique=True, verbose_name='Электронная почта')
    phone = models.CharField(max_length=12, unique=True, verbose_name='Телефон')

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


# 2. Профиль Отправителя (связь 1 к 1 с User)
class Sender(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,  # Удаление пользователя -> удаление профиля
        primary_key=True,
        related_name='sender_profile'
    )
    # type может означать тип клиента: "физическое лицо", "юридическое лицо" и т.д.
    type = models.CharField(max_length=10, blank=True, null=True, verbose_name='Тип отправителя')
    name = models.CharField(max_length=40, blank=True, null=True, verbose_name='Имя/Название')

    def __str__(self):
        return f"Отправитель: {self.name or self.user.username}"


# 3. Профиль Перевозчика (связь 1 к 1 с User)
class Transporter(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,  # Удаление пользователя -> удаление профиля
        primary_key=True,
        related_name='transporter_profile'
    )
    type = models.CharField(max_length=10, blank=True, null=True, verbose_name='Тип перевозчика')
    name = models.CharField(max_length=40, blank=True, null=True, verbose_name='Имя/Название компании')
    # Рейтинг от 0.00 до 5.00. Можно рассчитать на основе отзывов.
    score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(5.00)],
        verbose_name='Рейтинг'
    )

    def __str__(self):
        return f"Перевозчик: {self.name or self.user.username}"


# 4. Модель Заказа
class Order(models.Model):
    class Status(models.TextChoices):
        SEARCHING = 'searching', 'Поиск перевозчика'
        ASSIGNED = 'assigned', 'Назначен'
        IN_TRANSIT = 'in_transit', 'В пути'
        DELIVERED = 'delivered', 'Доставлен'
        CANCELLED = 'cancelled', 'Отменен'

    sender = models.ForeignKey(
        Sender,
        on_delete=models.CASCADE,  # Удаление отправителя -> удаление его заказов
        related_name='orders'
    )
    # Поле может быть NULL, пока заказ не принят в работу
    transporter = models.ForeignKey(
        Transporter,
        on_delete=models.SET_NULL,  # Если перевозчик удален, заказ остается, поле обнуляется
        null=True,
        blank=True,
        related_name='orders'
    )
    # Габариты и стоимость
    weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Вес (кг)')
    height = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Высота (м)')
    width = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Ширина (м)')
    length = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Длина (м)')
    coast = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость')

    # Адреса в текстовом виде (для отображения на карте их нужно будет геокодировать)
    address_departure = models.CharField(max_length=100, verbose_name='Адрес отправления')
    address_arrival = models.CharField(max_length=100, verbose_name='Адрес назначения')

    # Координаты для карты (опционально, но очень рекомендуется для работы с API)
    lat_departure = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                        verbose_name='Широта отправления')
    lon_departure = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                        verbose_name='Долгота отправления')
    lat_arrival = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                      verbose_name='Широта назначения')
    lon_arrival = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                      verbose_name='Долгота назначения')

    # Статус и временные метки
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SEARCHING,
        verbose_name='Статус'
    )
    date_create = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    date_departure_plan = models.DateTimeField(verbose_name='Плановая дата отправки')
    date_arrival_plan = models.DateTimeField(verbose_name='Плановая дата доставки')
    date_departure_fact = models.DateTimeField(null=True, blank=True, verbose_name='Фактическая дата отправки')
    date_arrival_fact = models.DateTimeField(null=True, blank=True, verbose_name='Фактическая дата доставки')

    class Meta:
        ordering = ['-date_create']  # Сортировка по умолчанию: новые сверху

    def __str__(self):
        return f"Заказ #{self.id} от {self.sender.name}"


# 5. Модель Транспортного средства
class Transport(models.Model):
    class TransportType(models.TextChoices):
        TRUCK = 'truck', 'Грузовик'
        VAN = 'van', 'Фургон'
        MINIVAN = 'minivan', 'Минивэн'
        PICKUP = 'pickup', 'Пикап'

    transporter = models.ForeignKey(
        Transporter,
        on_delete=models.CASCADE,  # Удаление перевозчика -> удаление его транспорта
        related_name='transports'
    )
    type = models.CharField(
        max_length=25,
        choices=TransportType.choices,
        verbose_name='Тип транспорта'
    )
    # Характеристики
    capacity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Грузоподъемность (кг)')
    length = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Длина кузова (м)')
    width = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Ширина кузова (м)')
    height = models.DecimalField(max_digits=6, decimal_places=3, verbose_name='Высота кузова (м)')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    def __str__(self):
        return f"{self.get_type_display()} ({self.transporter.name})"


# 6. Модель Маршрута/Рейса (ключевая для отслеживания)
class Route(models.Model):
    # Связь с заказом и транспортом
    transport = models.ForeignKey(
        Transport,
        on_delete=models.SET_NULL,  # Если транспорт удален, запись маршрута остается
        null=True,
        related_name='routes'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,  # Удаление заказа -> удаление связанных маршрутов
        related_name='routes'
    )

    # Координаты текущего местоположения (храним как два отдельных числа)
    # Для интеграции с Яндекс.Картами этого достаточно
    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Текущая широта'
    )
    current_lon = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Текущая долгота'
    )

    # Плановые и фактические даты
    date_departure_plan = models.DateTimeField(verbose_name='Плановая дата отправления по маршруту')
    date_arrival_plan = models.DateTimeField(verbose_name='Плановая дата прибытия по маршруту')
    date_departure_fact = models.DateTimeField(null=True, blank=True, verbose_name='Фактическая дата отправления')
    date_arrival_fact = models.DateTimeField(null=True, blank=True, verbose_name='Фактическая дата прибытия')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')

    class Meta:
        # Уникальность: один заказ не может быть на двух маршрутах одновременно
        constraints = [
            models.UniqueConstraint(fields=['order'], condition=models.Q(date_arrival_fact__isnull=True),
                                    name='unique_active_route_per_order')
        ]

    def __str__(self):
        return f"Маршрут для заказа #{self.order.id}"


# 7. Модель Отзыва
class Feedback(models.Model):
    sender = models.ForeignKey(
        Sender,
        on_delete=models.CASCADE,  # Удаление отправителя -> удаление его отзывов
        related_name='feedbacks_given'
    )
    transporter = models.ForeignKey(
        Transporter,
        on_delete=models.CASCADE,  # Удаление перевозчика -> удаление отзывов о нем
        related_name='feedbacks_received'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,  # Удаление заказа -> удаление связанного отзыва
        related_name='feedbacks'
    )
    text = models.TextField(blank=True, null=True, verbose_name='Текст отзыва')
    # Оценка от 1 до 5 с шагом 0.5 (например, 4.5)
    score = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        verbose_name='Оценка'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата отзыва')

    class Meta:
        # Один отзыв на одну пару (отправитель-перевозчик) для конкретного заказа
        constraints = [
            models.UniqueConstraint(fields=['sender', 'transporter', 'order'], name='unique_feedback_per_order')
        ]

    def __str__(self):
        return f"Отзыв от {self.sender.name} для {self.transporter.name} ({self.score}/5)"
