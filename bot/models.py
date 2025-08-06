import uuid
from django.db import models
from django.utils import timezone


class Order(models.Model):
    """Model to store order details"""
    
    # Order status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    # Junction choices - dynamically generated from location manager
    @property
    def junction_choices(self):
        from .location_manager import location_manager
        return location_manager.get_junction_choices()
    
    # Static choices for migration compatibility
    JUNCTION_CHOICES = [
        ('vyttila_delivery', 'Vyttila (Delivery)'),
        ('kakkanad_delivery', 'Kakkanad (Delivery)'),
        ('edappally_delivery', 'Edappally (Delivery)'),
        ('palarivattom_delivery', 'Palarivattom (Delivery)'),
        ('pickup', 'Pickup Only'),
    ]
    
    # Basic order information
    order_id = models.CharField(max_length=20, unique=True, db_index=True)
    phone_number = models.CharField(max_length=15)
    
    # Date and location
    delivery_date = models.DateField()
    junction = models.CharField(max_length=30, choices=JUNCTION_CHOICES)
    delivery_address = models.TextField(blank=True, null=True)
    maps_link = models.URLField(blank=True, null=True)
    
    # Order items (stored as JSON-like string)
    items = models.TextField()  # Format: "1 x 2, 3 x 1" (item_id x quantity)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment verification
    payment_screenshot_url = models.URLField(blank=True, null=True)
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Google Sheet sync
    sheet_row_number = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Order {self.order_id} - {self.phone_number}"
    
    def get_verification_url(self):
        """Generate verification URL"""
        from django.conf import settings
        return f"{settings.BASE_URL}/verify/{self.verification_token}/"
    
    def get_rejection_url(self):
        """Generate rejection URL"""
        from django.conf import settings
        return f"{settings.BASE_URL}/reject/{self.verification_token}/"
    
    def is_delivery(self):
        """Check if this order is for delivery"""
        return 'delivery' in self.junction
    
    def get_delivery_fee(self):
        """Get delivery fee based on junction"""
        from .location_manager import location_manager
        return location_manager.get_delivery_fee(self.junction)


class UserSession(models.Model):
    """Model to track user conversation state"""
    
    STEP_CHOICES = [
        ('start', 'Start'),
        ('date_selection', 'Date Selection'),
        ('junction_selection', 'Junction Selection'),
        ('menu_selection', 'Menu Selection'),
        ('delivery_details', 'Delivery Details'),
        ('payment_qr', 'Payment QR'),
        ('payment_screenshot', 'Payment Screenshot'),
        ('completed', 'Completed'),
    ]
    
    phone_number = models.CharField(max_length=15, unique=True)
    current_step = models.CharField(max_length=20, choices=STEP_CHOICES, default='start')
    
    # Temporary data storage during conversation
    selected_date = models.DateField(null=True, blank=True)
    selected_junction = models.CharField(max_length=30, blank=True)
    selected_items = models.TextField(blank=True)  # JSON string
    delivery_address = models.TextField(blank=True)
    maps_link = models.URLField(blank=True, null=True)
    
    # Current order reference
    current_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_interaction = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-last_interaction']
        
    def __str__(self):
        return f"Session {self.phone_number} - {self.current_step}"
    
    def update_interaction(self):
        """Update last interaction timestamp"""
        self.last_interaction = timezone.now()
        self.save(update_fields=['last_interaction'])


class MenuItem(models.Model):
    """Model for menu items"""
    
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
        
    def __str__(self):
        return f"{self.name} - ₹{self.price}"
