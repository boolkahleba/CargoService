# cargo/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
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
        max_length=12,
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
    """Форма создания/редактирования заказа"""

    class Meta:
        model = Order
        fields = [
            'weight', 'height', 'width', 'length',
            'coast', 'address_departure', 'address_arrival',
            'date_departure_plan', 'date_arrival_plan'
        ]
        widgets = {
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: 100.5',
                'step': '0.01'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В метрах',
                'step': '0.001'
            }),
            'width': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В метрах',
                'step': '0.001'
            }),
            'length': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В метрах',
                'step': '0.001'
            }),
            'coast': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Стоимость в рублях',
                'step': '0.01'
            }),
            'address_departure': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Начните вводить адрес...',
                'id': 'address-departure'
            }),
            'address_arrival': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Начните вводить адрес...',
                'id': 'address-arrival'
            }),
            'date_departure_plan': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'date_arrival_plan': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
        labels = {
            'weight': 'Вес груза (кг)',
            'height': 'Высота (м)',
            'width': 'Ширина (м)',
            'length': 'Длина (м)',
            'coast': 'Предлагаемая стоимость (руб.)',
            'address_departure': 'Адрес отправления',
            'address_arrival': 'Адрес назначения',
            'date_departure_plan': 'Плановая дата отправки',
            'date_arrival_plan': 'Плановая дата доставки',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем CSS классы ко всем полям
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'


class TransportForm(forms.ModelForm):
    """Форма добавления/редактирования транспорта"""
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Загрузите фото транспорта (необязательно)'
    )

    class Meta:
        model = Transport
        fields = ['type', 'capacity', 'length', 'width', 'height', 'photo']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В кг',
                'step': '0.01'
            }),
            'length': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В метрах',
                'step': '0.001'
            }),
            'width': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В метрах',
                'step': '0.001'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'В метрах',
                'step': '0.001'
            }),
        }
        labels = {
            'type': 'Тип транспорта',
            'capacity': 'Грузоподъемность',
            'length': 'Длина кузова',
            'width': 'Ширина кузова',
            'height': 'Высота кузова',
        }


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
    """Форма поиска заказов для перевозчиков"""
    weight_min = forms.DecimalField(
        label='Вес от (кг)',
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    weight_max = forms.DecimalField(
        label='Вес до (кг)',
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    departure_city = forms.CharField(
        label='Город отправления',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    arrival_city = forms.CharField(
        label='Город назначения',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    date_from = forms.DateField(
        label='Дата с',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    date_to = forms.DateField(
        label='Дата по',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    coast_min = forms.DecimalField(
        label='Стоимость от (руб.)',
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    coast_max = forms.DecimalField(
        label='Стоимость до (руб.)',
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )