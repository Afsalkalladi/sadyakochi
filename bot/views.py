import json
import logging
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Order
from .services import EeOnamBot
from .utils import update_sheet_verification_status

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """Handle WhatsApp webhook requests"""
    
    def get(self, request):
        """Verify webhook"""
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge)
        
        return HttpResponse('Forbidden', status=403)
    
    def post(self, request):
        """Handle incoming messages"""
        try:
            data = json.loads(request.body)
            logger.info(f"Received webhook data: {data}")
            
            # Extract message data
            entries = data.get('entry', [])
            
            for entry in entries:
                changes = entry.get('changes', [])
                
                for change in changes:
                    value = change.get('value', {})
                    
                    if 'messages' in value:
                        messages = value['messages']
                        
                        for message in messages:
                            self._process_message(message)
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return HttpResponse('Error', status=500)
    
    def _process_message(self, message_data):
        """Process individual message"""
        
        phone_number = message_data.get('from')
        message_type = message_data.get('type')
        
        bot = EeOnamBot()
        
        if message_type == 'text':
            text = message_data.get('text', {}).get('body', '')
            bot.process_message(phone_number, message_text=text, message_type='text')
            
        elif message_type == 'interactive':
            interactive_data = message_data.get('interactive', {})
            bot.process_message(
                phone_number, 
                message_type='interactive',
                interactive_data=interactive_data
            )
            
        elif message_type == 'location':
            location_data = message_data.get('location', {})
            bot.process_message(
                phone_number,
                message_type='location',
                location_data=location_data
            )
            
        elif message_type == 'image':
            image_data = message_data.get('image', {})
            media_data = {
                'type': 'image',
                'url': self._get_media_url(image_data.get('id')),
                'caption': image_data.get('caption', '')
            }
            bot.process_message(
                phone_number,
                message_type='media',
                media_data=media_data
            )
    
    def _get_media_url(self, media_id):
        """Get media URL from WhatsApp API"""
        if not media_id:
            return None
        
        try:
            import requests
            
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {
                'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('url')
            
        except Exception as e:
            logger.error(f"Error getting media URL: {e}")
            return None


@require_http_methods(["GET"])
def verify_payment(request, token):
    """Verify payment and update order status"""
    
    try:
        order = get_object_or_404(Order, verification_token=token, status='pending')
        
        # Update order status
        order.status = 'verified'
        order.save()
        
        # Update Google Sheet
        update_sheet_verification_status(order, 'verified')
        
        # Send WhatsApp message to customer
        bot = EeOnamBot()
        bot.send_verification_result(order, verified=True)
        
        return HttpResponse(
            "<html><body>"
            "<h2>✅ Payment Verified Successfully!</h2>"
            f"<p>Order ID: <strong>{order.order_id}</strong></p>"
            "<p>Customer has been notified via WhatsApp.</p>"
            "<p>You can close this window.</p>"
            "</body></html>"
        )
        
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return HttpResponse(
            "<html><body>"
            "<h2>❌ Error Verifying Payment</h2>"
            "<p>Please try again or contact support.</p>"
            "</body></html>",
            status=500
        )


@require_http_methods(["GET"])
def reject_payment(request, token):
    """Reject payment and update order status"""
    
    try:
        order = get_object_or_404(Order, verification_token=token, status='pending')
        
        # Update order status
        order.status = 'rejected'
        order.save()
        
        # Update Google Sheet
        update_sheet_verification_status(order, 'rejected')
        
        # Send WhatsApp message to customer
        bot = EeOnamBot()
        bot.send_verification_result(order, verified=False)
        
        return HttpResponse(
            "<html><body>"
            "<h2>❌ Payment Rejected</h2>"
            f"<p>Order ID: <strong>{order.order_id}</strong></p>"
            "<p>Customer has been notified via WhatsApp.</p>"
            "<p>You can close this window.</p>"
            "</body></html>"
        )
        
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}")
        return HttpResponse(
            "<html><body>"
            "<h2>❌ Error Processing Rejection</h2>"
            "<p>Please try again or contact support.</p>"
            "</body></html>",
            status=500
        )


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return HttpResponse("EeOnam Bot is running!")


@require_http_methods(["GET"])
def order_status(request, order_id):
    """Check order status"""
    try:
        order = get_object_or_404(Order, order_id=order_id)
        
        status_info = {
            'order_id': order.order_id,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d'),
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return HttpResponse(
            f"<html><body>"
            f"<h2>Order Status</h2>"
            f"<p><strong>Order ID:</strong> {status_info['order_id']}</p>"
            f"<p><strong>Status:</strong> {status_info['status'].title()}</p>"
            f"<p><strong>Amount:</strong> ₹{status_info['total_amount']}</p>"
            f"<p><strong>Delivery Date:</strong> {status_info['delivery_date']}</p>"
            f"<p><strong>Created:</strong> {status_info['created_at']}</p>"
            f"</body></html>"
        )
        
    except Exception as e:
        return HttpResponse("Order not found", status=404)
