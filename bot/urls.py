"""
URL configuration for bot app
"""

from django.urls import path
from . import views

app_name = 'bot'

urlpatterns = [
    # WhatsApp webhook - Now using DebugWebhookView for extensive logging
    path('webhook/', views.WhatsAppWebhookView.as_view(), name='webhook'),
    
    # Verification endpoints
    path('verify/<uuid:token>/', views.verify_payment, name='verify_payment'),
    path('reject/<uuid:token>/', views.reject_payment, name='reject_payment'),
    
    # Utility endpoints
    path('health/', views.health_check, name='health_check'),
    path('order/<str:order_id>/', views.order_status, name='order_status'),
]
