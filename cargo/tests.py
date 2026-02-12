from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from cargo.models import Sender, Transporter, Order, Transport

User = get_user_model()


class CargoModelTestCase(TestCase):
    @staticmethod
    def print_info(message):
        order_count = Order.objects.count()
        transport_count = Transport.objects.count()
        print(f"{message}: orders={order_count}, transports={transport_count}")

    def setUp(self):
        print('-' * 40)
        self.print_info('Start setUp')
        # Отправитель
        self.sender_user = User.objects.create_user(
            username='sender1',
            email='sender@test.ru',
            phone='+79991234567',
            user_type='sender',
            password='testpass123'
        )
        self.sender = Sender.objects.create(
            user=self.sender_user,
            name='ООО ТестОтправитель',
            inn='1234567890'
        )
        # Перевозчик
        self.transporter_user = User.objects.create_user(
            username='trans1',
            email='trans@test.ru',
            phone='+79997654321',
            user_type='transporter',
            password='testpass123'
        )
        self.transporter = Transporter.objects.create(
            user=self.transporter_user,
            name='ИП ТестПеревозчик',
            inn='0987654321'
        )

        # Заказ
        self.order = Order.objects.create(
            sender=self.sender,
            weight=500.00,
            height=1.20,
            width=1.00,
            length=1.50,
            coast=3500.00,
            address_departure='Москва, ул. Ленина, д.1',
            address_arrival='Санкт-Петербург, Невский пр., д.10',
            lat_departure=55.751244,
            lon_departure=37.618423,
            lat_arrival=59.931100,
            lon_arrival=30.360900,
            date_departure_plan=timezone.now(),
            date_arrival_plan=timezone.now() + timezone.timedelta(days=1),
            status='searching'
        )
        self.print_info('Finish setUp')

    def test_order_creation(self):
        self.print_info('Start test_order_creation')
        order = Order.objects.get(id=self.order.id)
        self.assertEqual(order.weight, 500.00)
        self.assertEqual(order.coast, 3500.00)
        self.assertEqual(order.status, 'searching')
        self.assertEqual(order.sender, self.sender)
        self.assertIsNotNone(order.lat_departure)
        self.assertIsNotNone(order.lon_arrival)
        self.print_info('Finish test_order_creation')

    def test_order_deletion(self):
        self.print_info('Start test_order_deletion')
        self.assertEqual(Order.objects.count(), 1)
        self.order.delete()
        self.assertEqual(Order.objects.count(), 0)
        self.print_info('Finish test_order_deletion')

    def test_order_status_change(self):
        self.print_info('Start test_order_status_change')

        self.order.transporter = self.transporter
        self.order.status = 'assigned'
        self.order.save()
        order = Order.objects.get(id=self.order.id)
        self.assertEqual(order.status, 'assigned')
        self.assertEqual(order.transporter, self.transporter)

        order.status = 'in_transit'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_transit')
        self.print_info('Finish test_order_status_change')