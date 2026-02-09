# cargo/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from .models import User, Sender, Transporter, Order, Transport, Feedback


class RegistrationForm(UserCreationForm):
    """Форма регистрации с выбором типа пользователя"""
    USER_TYPE_CHOICES = [
        ('sender', 'Я хочу отправлять грузы (Отправитель)'),
        ('transporter', 'Я хочу перевозить грузы (Перевозчик)'),
    ]

    user_type = forms.ChoiceField(
        label='Тип аккаунта',
        choices=USER_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )

    # Поля для отправителя
    sender_name = forms.CharField(
        label='Имя или название компании',
        max_length=40,
        required=False,
        help_text='Заполните, если вы отправитель'
    )
    sender_type = forms.ChoiceField(
        label='Тип отправителя',
        choices=[('', 'Выберите тип'), ('individual', 'Физическое лицо'), ('company', 'Юридическое лицо')],
        required=False
    )

    # Поля для перевозчика
    transporter_name = forms.CharField(
        label='Название компании или ФИО',
        max_length=40,
        required=False,
        help_text='Заполните, если вы перевозчик'
    )
    transporter_type = forms.ChoiceField(
        label='Тип перевозчика',
        choices=[('', 'Выберите тип'), ('individual', 'ИП'), ('company', 'Компания'), ('driver', 'Частный водитель')],
        required=False
    )

    email = forms.EmailField(required=True)
    phone = forms.CharField(
        max_length=13,
        required=True,
        help_text='Формат: +79991234567'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password1', 'password2', 'user_type')

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')

        # Проверка полей в зависимости от типа пользователя
        if user_type == 'sender':
            if not cleaned_data.get('sender_name'):
                raise ValidationError({
                    'sender_name': 'Это поле обязательно для отправителя'
                })
        elif user_type == 'transporter':
            if not cleaned_data.get('transporter_name'):
                raise ValidationError({
                    'transporter_name': 'Это поле обязательно для перевозчика'
                })

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = self.cleaned_data['user_type']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']

        if commit:
            user.save()

            # Создаем профиль в зависимости от типа пользователя
            if user.user_type == 'sender':
                Sender.objects.create(
                    user=user,
                    name=self.cleaned_data['sender_name'],
                    type=self.cleaned_data.get('sender_type')
                )
            elif user.user_type == 'transporter':
                Transporter.objects.create(
                    user=user,
                    name=self.cleaned_data['transporter_name'],
                    type=self.cleaned_data.get('transporter_type'),
                    score=0.00
                )

        return user


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'weight', 'height', 'width', 'length', 'coast',
            'address_departure', 'address_arrival',
            'date_departure_plan', 'date_arrival_plan'
        ]
        widgets = {
            'date_departure_plan': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'date_arrival_plan': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'weight': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'height': forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'}),
            'width': forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'}),
            'length': forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'}),
            'coast': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'address_departure': forms.TextInput(attrs={'class': 'form-control'}),
            'address_arrival': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'weight': 'Вес груза (кг)',
            'height': 'Высота (м)',
            'width': 'Ширина (м)',
            'length': 'Длина (м)',
            'coast': 'Предлагаемая стоимость (₽)',
            'address_departure': 'Адрес отправления',
            'address_arrival': 'Адрес назначения',
            'date_departure_plan': 'Плановая дата отправки',
            'date_arrival_plan': 'Плановая дата доставки',
        }

    def clean(self):
        """Простая валидация дат"""
        cleaned_data = super().clean()
        date_departure = cleaned_data.get('date_departure_plan')
        date_arrival = cleaned_data.get('date_arrival_plan')

        if date_departure and date_arrival and date_departure >= date_arrival:
            raise ValidationError('Дата отправки должна быть раньше даты доставки')

        return cleaned_data


class TransportForm(forms.ModelForm):
    """Форма добавления транспорта"""

    class Meta:
        model = Transport
        fields = ['type', 'capacity', 'length', 'width', 'height']
        widgets = {
            'capacity': forms.NumberInput(attrs={'step': '0.01'}),
            'length': forms.NumberInput(attrs={'step': '0.001'}),
            'width': forms.NumberInput(attrs={'step': '0.001'}),
            'height': forms.NumberInput(attrs={'step': '0.001'}),
        }
        labels = {
            'type': 'Тип транспорта',
            'capacity': 'Грузоподъемность (кг)',
            'length': 'Длина кузова (м)',
            'width': 'Ширина кузова (м)',
            'height': 'Высота кузова (м)',
        }

        capacity = forms.DecimalField(
            max_digits=10,
            decimal_places=2,
            validators=[MinValueValidator(0.01)],
            label='Грузоподъемность (кг)'
        )

        length = forms.DecimalField(
            max_digits=6,
            decimal_places=3,
            validators=[MinValueValidator(0.001)],
            label='Длина кузова (м)'
        )


class FeedbackForm(forms.ModelForm):
    """Форма оставления отзыва"""

    class Meta:
        model = Feedback
        fields = ['score', 'text']
        widgets = {
            'score': forms.Select(choices=[
                (1, '1 - Очень плохо'),
                (2, '2 - Плохо'),
                (3, '3 - Удовлетворительно'),
                (4, '4 - Хорошо'),
                (5, '5 - Отлично'),
            ], attrs={'class': 'form-select'}),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Расскажите о своем опыте...'
            }),
        }
        labels = {
            'score': 'Оценка',
            'text': 'Текст отзыва',
        }


class ProfileSettingsForm(forms.ModelForm):
    """Форма настройки профиля"""
    current_password = forms.CharField(
        label='Текущий пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Введите текущий пароль для изменения пароля'
    )
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    new_password2 = forms.CharField(
        label='Подтверждение нового пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 or new_password2:
            if not current_password:
                raise ValidationError({
                    'current_password': 'Для изменения пароля необходимо ввести текущий пароль'
                })
            if not self.instance.check_password(current_password):
                raise ValidationError({
                    'current_password': 'Неверный текущий пароль'
                })
            if new_password1 != new_password2:
                raise ValidationError({
                    'new_password2': 'Пароли не совпадают'
                })

        return cleaned_data


class OrderSearchForm(forms.Form):
    """Форма поиска заказов для перевозчика"""

    # Параметры груза
    weight_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label='Минимальный вес (кг)',
        widget=forms.NumberInput(attrs={'placeholder': '0'})
    )
    weight_max = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label='Максимальный вес (кг)',
        widget=forms.NumberInput(attrs={'placeholder': '10000'})
    )

    coast_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label='Минимальная стоимость (₽)',
        widget=forms.NumberInput(attrs={'placeholder': '0'})
    )

    # География
    departure_city = forms.CharField(
        required=False,
        max_length=100,
        label='Город отправления',
        widget=forms.TextInput(attrs={'placeholder': 'Например, Москва'})
    )
    arrival_city = forms.CharField(
        required=False,
        max_length=100,
        label='Город назначения',
        widget=forms.TextInput(attrs={'placeholder': 'Например, Санкт-Петербург'})
    )

    # Даты
    date_from = forms.DateField(
        required=False,
        label='Дата отправления от',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        label='Дата отправления до',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    # Сортировка
    SORT_CHOICES = [
        ('-date_create', 'Сначала новые'),
        ('date_create', 'Сначала старые'),
        ('coast', 'Дешевле'),
        ('-coast', 'Дороже'),
        ('weight', 'Легче'),
        ('-weight', 'Тяжелее'),
    ]
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-date_create',
        label='Сортировать по'
    )

    # Дополнительные параметры
    auto_match = forms.BooleanField(
        required=False,
        initial=True,
        label='Автоподбор под мой транспорт'
    )

    def clean(self):
        cleaned_data = super().clean()
        weight_min = cleaned_data.get('weight_min')
        weight_max = cleaned_data.get('weight_max')

        if weight_min and weight_max and weight_min > weight_max:
            raise forms.ValidationError("Минимальный вес не может быть больше максимального")

        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Дата 'от' не может быть позже даты 'до'")

        return cleaned_data