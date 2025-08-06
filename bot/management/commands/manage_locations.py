"""
Django management command for location management
Usage: python manage.py manage_locations [options]
"""

from django.core.management.base import BaseCommand, CommandError
from bot.location_manager import location_manager


class Command(BaseCommand):
    help = 'Manage delivery locations for EeOnam bot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all locations with their status',
        )
        parser.add_argument(
            '--activate',
            type=str,
            help='Activate a location by ID',
        )
        parser.add_argument(
            '--deactivate',
            type=str,
            help='Deactivate a location by ID',
        )
        parser.add_argument(
            '--update-fee',
            nargs=2,
            metavar=('LOCATION_ID', 'FEE'),
            help='Update delivery fee for a location',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show location statistics',
        )
        parser.add_argument(
            '--whatsapp-preview',
            action='store_true',
            help='Preview WhatsApp buttons for locations',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_locations()
        elif options['activate']:
            self.activate_location(options['activate'])
        elif options['deactivate']:
            self.deactivate_location(options['deactivate'])
        elif options['update_fee']:
            location_id, fee = options['update_fee']
            self.update_fee(location_id, int(fee))
        elif options['stats']:
            self.show_stats()
        elif options['whatsapp_preview']:
            self.whatsapp_preview()
        else:
            self.stdout.write(
                self.style.WARNING('No action specified. Use --help for options.')
            )

    def list_locations(self):
        """List all locations with their status"""
        self.stdout.write(self.style.SUCCESS('Current Locations:'))
        self.stdout.write('-' * 50)
        
        for location_id, location in location_manager.get_all_locations().items():
            status = self.style.SUCCESS('ACTIVE') if location.is_active else self.style.ERROR('INACTIVE')
            fee_display = f"₹{location.delivery_fee}" if location.delivery_fee > 0 else "FREE"
            
            self.stdout.write(
                f"{location.display_name:<25} | {status} | {fee_display:>8}"
            )

    def activate_location(self, location_id):
        """Activate a location"""
        if location_id not in location_manager.get_all_locations():
            raise CommandError(f'Location "{location_id}" does not exist.')
        
        location_manager.activate_location(location_id)
        location = location_manager.get_location(location_id)
        self.stdout.write(
            self.style.SUCCESS(f'Activated location: {location.display_name}')
        )

    def deactivate_location(self, location_id):
        """Deactivate a location"""
        if location_id not in location_manager.get_all_locations():
            raise CommandError(f'Location "{location_id}" does not exist.')
        
        location_manager.deactivate_location(location_id)
        location = location_manager.get_location(location_id)
        self.stdout.write(
            self.style.WARNING(f'Deactivated location: {location.display_name}')
        )

    def update_fee(self, location_id, new_fee):
        """Update delivery fee for a location"""
        if location_id not in location_manager.get_all_locations():
            raise CommandError(f'Location "{location_id}" does not exist.')
        
        old_fee = location_manager.get_delivery_fee(location_id)
        location_manager.update_delivery_fee(location_id, new_fee)
        location = location_manager.get_location(location_id)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Updated {location.display_name}: ₹{old_fee} → ₹{new_fee}'
            )
        )

    def show_stats(self):
        """Show location statistics from orders"""
        try:
            from bot.models import Order
            from django.db.models import Count, Sum, Avg
            
            self.stdout.write(self.style.SUCCESS('Location Statistics:'))
            self.stdout.write('-' * 60)
            
            for location_id, location in location_manager.get_active_locations().items():
                orders = Order.objects.filter(junction=location_id)
                
                if orders.exists():
                    stats = orders.aggregate(
                        total_orders=Count('id'),
                        total_revenue=Sum('total_amount'),
                        avg_order=Avg('total_amount')
                    )
                    
                    self.stdout.write(
                        f"{location.display_name}:\n"
                        f"  Orders: {stats['total_orders']}\n"
                        f"  Revenue: ₹{stats['total_revenue'] or 0:.2f}\n"
                        f"  Avg Order: ₹{stats['avg_order'] or 0:.2f}\n"
                    )
                else:
                    self.stdout.write(f"{location.display_name}: No orders yet\n")
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error fetching statistics: {e}')
            )

    def whatsapp_preview(self):
        """Preview WhatsApp button layout"""
        self.stdout.write(self.style.SUCCESS('WhatsApp Button Preview:'))
        self.stdout.write('-' * 40)
        
        button_groups = location_manager.get_whatsapp_buttons()
        
        for i, group in enumerate(button_groups, 1):
            self.stdout.write(f"Message {i}:")
            for button in group:
                title = button['reply']['title']
                button_id = button['reply']['id']
                self.stdout.write(f"  [{title}] (ID: {button_id})")
            self.stdout.write("")
