#!/usr/bin/env python
"""
Test script to verify EeOnam bot setup
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/afsalkalladi/Pictures/eeonam')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eeonam_project.settings')
django.setup()

from bot.models import MenuItem, Order, UserSession
from bot.utils import get_available_dates, generate_order_id


def test_setup():
    """Test the basic setup"""
    
    print("🧪 Testing EeOnam Bot Setup...")
    print("=" * 50)
    
    # Test menu items
    menu_items = MenuItem.objects.all()
    print(f"📋 Menu Items: {menu_items.count()} items loaded")
    for item in menu_items:
        print(f"   - {item.name}: ₹{item.price}")
    
    print()
    
    # Test date generation
    dates = get_available_dates()
    print(f"📅 Available Dates: {len(dates)} dates generated")
    print(f"   - First date: {dates[0]}")
    print(f"   - Last date: {dates[-1]}")
    
    print()
    
    # Test order ID generation
    order_id = generate_order_id()
    print(f"🆔 Order ID Generation: {order_id}")
    
    print()
    
    # Test database models
    orders_count = Order.objects.count()
    sessions_count = UserSession.objects.count()
    print(f"🗄️  Database Status:")
    print(f"   - Orders: {orders_count}")
    print(f"   - Sessions: {sessions_count}")
    
    print()
    
    # Test environment variables
    from django.conf import settings
    
    print("🔧 Environment Variables:")
    env_vars = [
        'WHATSAPP_ACCESS_TOKEN',
        'WHATSAPP_PHONE_NUMBER_ID', 
        'WHATSAPP_VERIFY_TOKEN',
        'UPI_ID',
        'UPI_MERCHANT_NAME',
        'BASE_URL'
    ]
    
    for var in env_vars:
        value = getattr(settings, var, None)
        status = "✅" if value else "❌"
        display_value = value if var not in ['WHATSAPP_ACCESS_TOKEN'] else "[HIDDEN]"
        print(f"   {status} {var}: {display_value}")
    
    print()
    print("🎉 Setup test completed!")
    print()
    print("📝 Next steps:")
    print("   1. Configure your .env file with actual credentials")
    print("   2. Set up Google credentials (service-account.json)")
    print("   3. Configure WhatsApp webhook URL")
    print("   4. Test with python manage.py runserver")


if __name__ == "__main__":
    test_setup()
