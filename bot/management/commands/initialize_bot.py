"""
Management command to initialize EeOnam bot data
"""

from django.core.management.base import BaseCommand
from bot.models import MenuItem
from bot.utils import initialize_google_sheet


class Command(BaseCommand):
    """Initialize the EeOnam bot with menu items and Google Sheet"""
    
    help = 'Initialize EeOnam bot with menu items and Google Sheet setup'
    
    def handle(self, *args, **options):
        """Execute the command"""
        
        self.stdout.write(self.style.SUCCESS('🎉 Initializing EeOnam Bot...'))
        
        # Create menu items
        self.create_menu_items()
        
        # Initialize Google Sheet
        self.initialize_sheet()
        
        self.stdout.write(
            self.style.SUCCESS('✅ EeOnam Bot initialization completed!')
        )
    
    def create_menu_items(self):
        """Create default menu items"""
        
        menu_items = [
            {'name': 'Veg Sadhya', 'price': 150, 'sort_order': 1, 'description': 'Traditional vegetarian Onam feast'},
            {'name': 'Non-Veg Sadhya', 'price': 200, 'sort_order': 2, 'description': 'Sadhya with non-vegetarian dishes'},
            {'name': 'Palada Pradhaman', 'price': 40, 'sort_order': 3, 'description': 'Traditional Kerala dessert'},
            {'name': 'Parippu/Gothambu Payasam', 'price': 40, 'sort_order': 4, 'description': 'Lentil or wheat payasam'},
            {'name': 'Kaaya Varuthathu', 'price': 30, 'sort_order': 5, 'description': 'Banana chips'},
            {'name': 'Sharkkaravaratti', 'price': 30, 'sort_order': 6, 'description': 'Jaggery-coated banana chips'},
        ]
        
        created_count = 0
        for item_data in menu_items:
            item, created = MenuItem.objects.get_or_create(
                name=item_data['name'],
                defaults=item_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"  ✓ Created menu item: {item.name}")
            else:
                self.stdout.write(f"  - Menu item already exists: {item.name}")
        
        self.stdout.write(
            self.style.SUCCESS(f"📋 Menu items: {created_count} created, {len(menu_items) - created_count} already existed")
        )
    
    def initialize_sheet(self):
        """Initialize Google Sheet with headers"""
        
        try:
            success = initialize_google_sheet()
            
            if success:
                self.stdout.write(self.style.SUCCESS("📊 Google Sheet initialized successfully"))
            else:
                self.stdout.write(self.style.WARNING("⚠️  Google Sheet initialization failed"))
                self.stdout.write("   Make sure your Google credentials are properly configured")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error initializing Google Sheet: {e}"))
