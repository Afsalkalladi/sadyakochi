from bot.models import Order
from django.utils import timezone

# Test phone number
TEST_PHONE = '918891281090'

# Create a test order
order = Order.objects.create(
    phone_number=TEST_PHONE,
    delivery_date=timezone.now().date(),
    junction='vyttila_delivery',
    items='{"1": 1}',
    total_amount=100,
    status='pending_location',
    delivery_address='',
)

print(f"Created order: {order.order_id}, status: {order.status}, phone: {order.phone_number}")

# Query for pending orders
pending_orders = Order.objects.filter(
    phone_number=TEST_PHONE,
    status__in=['pending_location', 'awaiting_payment']
).order_by('-created_at')

print(f"Pending orders found: {pending_orders.count()}")
for o in pending_orders:
    print(f"Order: {o.order_id}, status: {o.status}, created: {o.created_at}")
