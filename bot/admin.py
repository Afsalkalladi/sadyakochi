from django.contrib import admin
from .models import Order, UserSession, MenuItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model"""
    
    list_display = [
        'order_id', 'phone_number', 'delivery_date', 'junction', 
        'total_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'junction', 'delivery_date', 'created_at']
    search_fields = ['order_id', 'phone_number']
    readonly_fields = ['order_id', 'verification_token', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'phone_number', 'delivery_date', 'junction')
        }),
        ('Items & Payment', {
            'fields': ('items', 'total_amount', 'payment_screenshot_url')
        }),
        ('Delivery Details', {
            'fields': ('delivery_address', 'maps_link')
        }),
        ('Verification', {
            'fields': ('verification_token', 'status')
        }),
        ('System Fields', {
            'fields': ('created_at', 'updated_at', 'sheet_row_number'),
            'classes': ('collapse',)
        })
    )


@admin.register(UserSession) 
class UserSessionAdmin(admin.ModelAdmin):
    """Admin interface for UserSession model"""
    
    list_display = [
        'phone_number', 'current_step', 'selected_date', 
        'selected_junction', 'last_interaction'
    ]
    list_filter = ['current_step', 'selected_junction', 'last_interaction']
    search_fields = ['phone_number']
    readonly_fields = ['created_at', 'updated_at', 'last_interaction']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin interface for MenuItem model"""
    
    list_display = ['name', 'price', 'is_available', 'sort_order']
    list_filter = ['is_available']
    search_fields = ['name']
    list_editable = ['price', 'is_available', 'sort_order']
    ordering = ['sort_order', 'name']
