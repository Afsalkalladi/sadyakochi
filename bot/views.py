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
            logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
            
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
                    
                    # Handle status updates (delivery receipts, read receipts, etc.)
                    if 'statuses' in value:
                        statuses = value['statuses']
                        logger.info(f"Received status updates: {statuses}")
            
            return HttpResponse('OK')
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            return HttpResponse('Invalid JSON', status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return HttpResponse('Error', status=500)
    
    def _process_message(self, message_data):
        """Process individual message"""
        
        phone_number = message_data.get('from')
        message_type = message_data.get('type')
        message_id = message_data.get('id')
        timestamp = message_data.get('timestamp')
        
        # Add debug logging
        logger.info(f"Processing message {message_id} from {phone_number}, type: {message_type}")
        logger.info(f"Full message data: {json.dumps(message_data, indent=2)}")
        
        bot = EeOnamBot()
        
        try:
            if message_type == 'text':
                text = message_data.get('text', {}).get('body', '')
                logger.info(f"Text message: '{text}'")
                bot.process_message(phone_number, message_text=text, message_type='text')
                
            elif message_type == 'interactive':
                interactive_data = message_data.get('interactive', {})
                logger.info(f"Interactive data: {interactive_data}")
                bot.process_message(
                    phone_number, 
                    message_type='interactive',
                    interactive_data=interactive_data
                )
                
            elif message_type == 'location':
                location_data = message_data.get('location', {})
                logger.info(f"Raw location data from WhatsApp: {location_data}")
                
                # WhatsApp location format validation and processing
                if 'latitude' in location_data and 'longitude' in location_data:
                    processed_location = {
                        'latitude': location_data.get('latitude'),
                        'longitude': location_data.get('longitude'),
                        'name': location_data.get('name', ''),
                        'address': location_data.get('address', '')
                    }
                    
                    logger.info(f"Processed location: {processed_location}")
                    
                    bot.process_message(
                        phone_number,
                        message_type='location',
                        location_data=processed_location
                    )
                else:
                    logger.warning(f"Invalid location data received: {location_data}")
                    bot.whatsapp.send_message(
                        phone_number,
                        "Invalid location data received. Please share your location again."
                    )
                
            elif message_type == 'image':
                image_data = message_data.get('image', {})
                media_id = image_data.get('id')
                
                logger.info(f"Image data: {image_data}")
                
                if media_id:
                    media_url = self._get_media_url(media_id)
                    logger.info(f"Media URL: {media_url}")
                    
                    if media_url:
                        media_data = {
                            'type': 'image',
                            'url': media_url,
                            'caption': image_data.get('caption', '')
                        }
                        bot.process_message(
                            phone_number,
                            message_type='media',
                            media_data=media_data
                        )
                    else:
                        logger.error(f"Failed to get media URL for media_id: {media_id}")
                        bot.whatsapp.send_message(
                            phone_number,
                            "Unable to process image. Please try again."
                        )
                else:
                    logger.warning("Image message without media_id")
                    
            elif message_type == 'document':
                # Handle document messages if needed
                logger.info(f"Document message received: {message_data}")
                bot.whatsapp.send_message(
                    phone_number,
                    "Document messages are not supported. Please send images only."
                )
                
            elif message_type == 'audio':
                # Handle audio messages if needed
                logger.info(f"Audio message received: {message_data}")
                bot.whatsapp.send_message(
                    phone_number,
                    "Audio messages are not supported. Please send text or images."
                )
                
            elif message_type == 'video':
                # Handle video messages if needed
                logger.info(f"Video message received: {message_data}")
                bot.whatsapp.send_message(
                    phone_number,
                    "Video messages are not supported. Please send text or images."
                )
            
            else:
                logger.warning(f"Unhandled message type: {message_type}")
                bot.whatsapp.send_message(
                    phone_number,
                    "Sorry, I couldn't process that message type. Please try again or type 'start' to begin."
                )
                
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}", exc_info=True)
            # Send error message to user
            try:
                bot.whatsapp.send_message(
                    phone_number,
                    "Sorry, something went wrong processing your message. Please try again or type 'start'."
                )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
    
    def _get_media_url(self, media_id):
        """Get media URL from WhatsApp API"""
        if not media_id:
            return None
        
        try:
            import requests
            
            # First, get media info
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {
                'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            media_url = data.get('url')
            
            if not media_url:
                logger.error(f"No URL in media response: {data}")
                return None
                
            logger.info(f"Got media URL for {media_id}: {media_url}")
            return media_url
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout getting media URL for {media_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting media URL for {media_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting media URL for {media_id}: {e}")
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
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: green;'>✅ Payment Verified Successfully!</h2>"
            f"<p><strong>Order ID:</strong> {order.order_id}</p>"
            "<p>Customer has been notified via WhatsApp.</p>"
            "<p>You can close this window.</p>"
            "</body></html>"
        )
        
    except Http404:
        return HttpResponse(
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: red;'>❌ Order Not Found</h2>"
            "<p>Invalid or expired verification link.</p>"
            "</body></html>",
            status=404
        )
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return HttpResponse(
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: red;'>❌ Error Verifying Payment</h2>"
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
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: orange;'>❌ Payment Rejected</h2>"
            f"<p><strong>Order ID:</strong> {order.order_id}</p>"
            "<p>Customer has been notified via WhatsApp.</p>"
            "<p>You can close this window.</p>"
            "</body></html>"
        )
        
    except Http404:
        return HttpResponse(
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: red;'>❌ Order Not Found</h2>"
            "<p>Invalid or expired verification link.</p>"
            "</body></html>",
            status=404
        )
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}")
        return HttpResponse(
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: red;'>❌ Error Processing Rejection</h2>"
            "<p>Please try again or contact support.</p>"
            "</body></html>",
            status=500
        )


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return HttpResponse("EeOnam Bot is running!", content_type="text/plain")


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
            f"<html><body style='font-family: Arial, sans-serif; margin: 20px;'>"
            f"<h2>Order Status</h2>"
            f"<div style='background: #f5f5f5; padding: 20px; border-radius: 8px;'>"
            f"<p><strong>Order ID:</strong> {status_info['order_id']}</p>"
            f"<p><strong>Status:</strong> <span style='color: {'green' if status_info['status'] == 'verified' else 'orange'};'>{status_info['status'].title()}</span></p>"
            f"<p><strong>Amount:</strong> ₹{status_info['total_amount']}</p>"
            f"<p><strong>Delivery Date:</strong> {status_info['delivery_date']}</p>"
            f"<p><strong>Created:</strong> {status_info['created_at']}</p>"
            f"</div>"
            f"</body></html>"
        )
        
    except Http404:
        return HttpResponse(
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: red;'>❌ Order Not Found</h2>"
            "<p>Invalid order ID.</p>"
            "</body></html>",
            status=404
        )
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        return HttpResponse(
            "<html><body style='font-family: Arial, sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2 style='color: red;'>❌ Error</h2>"
            "<p>Unable to retrieve order status.</p>"
            "</body></html>",
            status=500
        )