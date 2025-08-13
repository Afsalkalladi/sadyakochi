import json
import logging
import traceback
from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from .models import Order
from .services import EeOnamBot
from .utils import update_sheet_verification_status

# Set up detailed logging
logger = logging.getLogger(__name__)
# This line is for debugging locally. In production, you'll likely configure this in settings.py
logging.basicConfig(level=logging.DEBUG)


# --- Original Views ---
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


# -----------------------------------------------------------------------------
# --- Debugging Views and Functions (Added) ---
# -----------------------------------------------------------------------------
"""
WhatsApp Webhook Debug Handler for EeOnam Bot
Add this to your views.py to debug location upload issues
"""

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_POST, name='dispatch')
class DebugWebhookView(View):
    """
    Debug version of WhatsApp webhook handler with extensive logging
    """
    
    def post(self, request):
        logger.debug("🚀 WEBHOOK REQUEST RECEIVED")
        logger.debug("="*60)
        
        try:
            # Log request details
            logger.debug(f"Request method: {request.method}")
            logger.debug(f"Request path: {request.path}")
            logger.debug(f"Content type: {request.content_type}")
            logger.debug(f"Request headers: {dict(request.headers)}")
            
            # Get raw body
            raw_body = request.body
            logger.debug(f"Raw body length: {len(raw_body)} bytes")
            logger.debug(f"Raw body (first 500 chars): {raw_body[:500]}")
            
            # Parse JSON
            try:
                data = json.loads(raw_body)
                logger.debug("✅ JSON parsed successfully")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {str(e)}")
                return HttpResponseBadRequest("Invalid JSON")
            
            # Log full webhook data
            logger.debug("📋 FULL WEBHOOK DATA:")
            logger.debug(json.dumps(data, indent=2))
            
            # Check if it's a WhatsApp Business Account webhook
            if data.get('object') != 'whatsapp_business_account':
                logger.warning(f"⚠️ Unexpected object type: {data.get('object')}")
                return HttpResponse("OK")
            
            # Process each entry
            entries = data.get('entry', [])
            logger.debug(f"📦 Processing {len(entries)} entries")
            
            for entry_idx, entry in enumerate(entries):
                logger.debug(f"\n🔍 PROCESSING ENTRY {entry_idx + 1}")
                logger.debug("-" * 40)
                logger.debug(f"Entry ID: {entry.get('id')}")
                
                changes = entry.get('changes', [])
                logger.debug(f"Changes count: {len(changes)}")
                
                for change_idx, change in enumerate(changes):
                    logger.debug(f"\n📝 PROCESSING CHANGE {change_idx + 1}")
                    logger.debug(f"Field: {change.get('field')}")
                    
                    value = change.get('value', {})
                    
                    # Check for messages
                    messages = value.get('messages', [])
                    if messages:
                        logger.debug(f"🔔 FOUND {len(messages)} MESSAGES")
                        self.debug_process_messages(messages)
                    
                    # Check for status updates
                    statuses = value.get('statuses', [])
                    if statuses:
                        logger.debug(f"📊 FOUND {len(statuses)} STATUS UPDATES")
                        self.debug_process_statuses(statuses)
            
            logger.debug("✅ WEBHOOK PROCESSING COMPLETED")
            return HttpResponse("OK")
            
        except Exception as e:
            logger.error(f"❌ WEBHOOK ERROR: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return HttpResponseBadRequest(f"Error: {str(e)}")
    
    def debug_process_messages(self, messages):
        """Debug process incoming messages"""
        logger.debug("\n🔔 PROCESSING MESSAGES")
        logger.debug("="*40)
        
        for msg_idx, message in enumerate(messages):
            logger.debug(f"\n📱 MESSAGE {msg_idx + 1}")
            logger.debug("-" * 30)
            
            # Basic message info
            msg_id = message.get('id')
            msg_from = message.get('from')
            timestamp = message.get('timestamp')
            msg_type = message.get('type')
            
            logger.debug(f"Message ID: {msg_id}")
            logger.debug(f"From: {msg_from}")
            logger.debug(f"Timestamp: {timestamp}")
            logger.debug(f"Type: {msg_type}")
            
            # Log full message structure
            logger.debug(f"Full message data:")
            logger.debug(json.dumps(message, indent=2))
            
            # Process different message types
            if msg_type == 'text':
                self.debug_process_text_message(message)
            elif msg_type == 'location':
                self.debug_process_location_message(message)
            elif msg_type == 'image':
                self.debug_process_image_message(message)
            elif msg_type == 'interactive':
                self.debug_process_interactive_message(message)
            else:
                logger.debug(f"🤷 Unknown message type: {msg_type}")
    
    def debug_process_text_message(self, message):
        """Debug process text messages"""
        logger.debug("💬 PROCESSING TEXT MESSAGE")
        
        text_data = message.get('text', {})
        body = text_data.get('body', '')
        
        logger.debug(f"Text body: '{body}'")
        logger.debug(f"Text body length: {len(body)}")
        
        # Check if it's a command or response
        if body.lower().startswith('/'):
            logger.debug(f"🤖 Detected command: {body}")
        elif body.isdigit():
            logger.debug(f"🔢 Detected number input: {body}")
        else:
            logger.debug(f"📝 Regular text message")
    
    def debug_process_location_message(self, message):
        """Debug process location messages - THIS IS KEY FOR YOUR ISSUE"""
        logger.debug("📍 PROCESSING LOCATION MESSAGE")
        logger.debug("🎯 THIS IS WHERE YOUR ISSUE MIGHT BE!")
        
        location_data = message.get('location', {})
        
        # Log all location data
        logger.debug(f"Location data keys: {list(location_data.keys())}")
        logger.debug(f"Full location data:")
        logger.debug(json.dumps(location_data, indent=2))
        
        # Extract location details
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        name = location_data.get('name')
        address = location_data.get('address')
        url = location_data.get('url')
        
        logger.debug(f"📌 Latitude: {latitude}")
        logger.debug(f"📌 Longitude: {longitude}")
        logger.debug(f"🏷️ Name: {name}")
        logger.debug(f"🏠 Address: {address}")
        logger.debug(f"🔗 URL: {url}")
        
        # Validate location data
        if not latitude or not longitude:
            logger.error("❌ Missing latitude or longitude in location message")
        else:
            logger.debug("✅ Location coordinates are present")
        
        # Check if we need to save this location
        msg_from = message.get('from')
        logger.debug(f"🔍 Checking if user {msg_from} has pending order for location...")
        
        try:
            # Import here to avoid circular imports
            from .models import Order
            
            # Look for pending order from this user
            pending_orders = Order.objects.filter(
                phone_number=msg_from,
                status__in=['pending_location', 'awaiting_payment']
            ).order_by('-created_at')
            
            logger.debug(f"Found {len(pending_orders)} pending orders for user {msg_from}")
            
            if pending_orders:
                order = pending_orders.first()
                logger.debug(f"Processing location for order: {order.order_id}")
                
                # This is where you would normally save the location
                self.debug_save_location_to_order(order, location_data)
            else:
                logger.warning(f"⚠️ No pending orders found for user {msg_from}")
                
        except Exception as e:
            logger.error(f"❌ Error processing location for order: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def debug_save_location_to_order(self, order, location_data):
        """Debug save location to order"""
        logger.debug(f"💾 SAVING LOCATION TO ORDER {order.order_id}")
        logger.debug("-" * 40)
        
        try:
            # Extract location details
            latitude = location_data.get('latitude')
            longitude = location_data.get('longitude')
            name = location_data.get('name', '')
            address = location_data.get('address', '')
            url = location_data.get('url', '')
            
            # Create delivery address
            if name and address:
                delivery_address = f"{name}, {address}"
            elif name:
                delivery_address = name
            elif address:
                delivery_address = address
            else:
                delivery_address = f"Location: {latitude}, {longitude}"
            
            logger.debug(f"📝 Constructed delivery address: {delivery_address}")
            
            # Create maps link
            maps_link = ""
            if url:
                maps_link = url
                logger.debug(f"🗺️ Using provided URL: {url}")
            elif latitude and longitude:
                maps_link = f"https://maps.google.com/?q={latitude},{longitude}"
                logger.debug(f"🗺️ Generated Google Maps link: {maps_link}")
            
            # Save to order
            logger.debug("💾 Updating order with location data...")
            
            old_address = order.delivery_address
            old_maps_link = order.maps_link
            old_status = order.status
            
            order.delivery_address = delivery_address
            order.maps_link = maps_link
            order.status = 'awaiting_payment'
            order.save()
            
            logger.debug(f"✅ Order updated successfully:")
            logger.debug(f"  - Address: '{old_address}' → '{order.delivery_address}'")
            logger.debug(f"  - Maps Link: '{old_maps_link}' → '{order.maps_link}'")
            logger.debug(f"  - Status: '{old_status}' → '{order.status}'")
            
            # Generate QR code for payment
            logger.debug("💳 Generating payment QR code...")
            
            from .utils import generate_qr_code
            qr_url = generate_qr_code(float(order.total_amount), order.order_id)
            
            if qr_url:
                logger.debug(f"✅ QR code generated: {qr_url}")
                
                # Send payment message (you would implement this)
                self.debug_send_payment_message(order, qr_url)
            else:
                logger.error("❌ Failed to generate QR code")
                
        except Exception as e:
            logger.error(f"❌ Error saving location to order: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def debug_send_payment_message(self, order, qr_url):
        """Debug send payment message"""
        logger.debug(f"💳 SENDING PAYMENT MESSAGE FOR ORDER {order.order_id}")
        
        # This is where you would send the payment QR code
        # Log what should be sent
        logger.debug(f"Should send payment QR: {qr_url}")
        logger.debug(f"To phone number: {order.phone_number}")
        logger.debug(f"Order total: ₹{order.total_amount}")
        
        # You would implement the actual message sending here
        logger.debug("📤 Payment message would be sent here")
    
    def debug_process_image_message(self, message):
        """Debug process image messages"""
        logger.debug("🖼️ PROCESSING IMAGE MESSAGE")
        
        image_data = message.get('image', {})
        
        # Log image details
        logger.debug(f"Image data keys: {list(image_data.keys())}")
        logger.debug(f"Full image data:")
        logger.debug(json.dumps(image_data, indent=2))
        
        # Extract image details
        media_id = image_data.get('id')
        mime_type = image_data.get('mime_type')
        sha256 = image_data.get('sha256')
        caption = image_data.get('caption', '')
        
        logger.debug(f"📷 Media ID: {media_id}")
        logger.debug(f"🎭 MIME Type: {mime_type}")
        logger.debug(f"🔒 SHA256: {sha256}")
        logger.debug(f"💬 Caption: '{caption}'")
        
        if media_id:
            logger.debug("🔄 Would process image upload here...")
            self.debug_process_image_upload(message, media_id)
    
    def debug_process_image_upload(self, message, media_id):
        """Debug process image upload (payment screenshots)"""
        logger.debug(f"📤 PROCESSING IMAGE UPLOAD - MEDIA ID: {media_id}")
        
        msg_from = message.get('from')
        logger.debug(f"Image from user: {msg_from}")
        
        try:
            # Import here to avoid circular imports
            from .models import Order
            
            # Look for pending payment order from this user
            pending_orders = Order.objects.filter(
                phone_number=msg_from,
                status='awaiting_payment'
            ).order_by('-created_at')
            
            logger.debug(f"Found {len(pending_orders)} orders awaiting payment for user {msg_from}")
            
            if pending_orders:
                order = pending_orders.first()
                logger.debug(f"Processing image for order: {order.order_id}")
                
                # Get media URL from WhatsApp
                logger.debug("🔄 Getting media URL from WhatsApp API...")
                media_url = self.debug_get_media_url(media_id)
                
                if media_url:
                    logger.debug(f"✅ Media URL obtained: {media_url}")
                    
                    # Upload to Google Drive
                    logger.debug("☁️ Uploading to Google Drive...")
                    from .utils import upload_to_drive
                    
                    drive_url = upload_to_drive(media_url, order.order_id)
                    
                    if drive_url:
                        logger.debug(f"✅ Image uploaded to Drive: {drive_url}")
                        
                        # Update order
                        order.payment_screenshot_url = drive_url
                        order.status = 'pending_verification'
                        order.save()
                        
                        logger.debug(f"✅ Order {order.order_id} updated with screenshot")
                        
                        # Save to Google Sheet
                        logger.debug("📊 Saving to Google Sheet...")
                        from .utils import save_to_google_sheet
                        
                        sheet_result = save_to_google_sheet(order)
                        if sheet_result:
                            logger.debug("✅ Order saved to Google Sheet")
                        else:
                            logger.error("❌ Failed to save to Google Sheet")
                    else:
                        logger.error("❌ Failed to upload image to Drive")
                else:
                    logger.error("❌ Failed to get media URL from WhatsApp")
            else:
                logger.warning(f"⚠️ No orders awaiting payment for user {msg_from}")
                
        except Exception as e:
            logger.error(f"❌ Error processing image upload: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def debug_get_media_url(self, media_id):
        """Debug get media URL from WhatsApp API"""
        logger.debug(f"🔗 GETTING MEDIA URL FOR ID: {media_id}")
        
        try:
            import requests
            from django.conf import settings
            
            # Check if access token is available
            if not hasattr(settings, 'WHATSAPP_ACCESS_TOKEN'):
                logger.error("❌ WHATSAPP_ACCESS_TOKEN not found in settings")
                return None
            
            access_token = settings.WHATSAPP_ACCESS_TOKEN
            logger.debug(f"Using access token (first 10 chars): {access_token[:10]}...")
            
            # Make request to WhatsApp API
            url = f"https://graph.facebook.com/v17.0/{media_id}"
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            logger.debug(f"Making request to: {url}")
            logger.debug(f"Headers: {headers}")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                media_data = response.json()
                logger.debug(f"Media data: {json.dumps(media_data, indent=2)}")
                
                media_url = media_data.get('url')
                if media_url:
                    logger.debug(f"✅ Media URL obtained: {media_url}")
                    return media_url
                else:
                    logger.error("❌ No 'url' field in media response")
            else:
                logger.error(f"❌ WhatsApp API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting media URL: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def debug_process_interactive_message(self, message):
        """Debug process interactive messages (button clicks)"""
        logger.debug("🎮 PROCESSING INTERACTIVE MESSAGE")
        
        interactive_data = message.get('interactive', {})
        
        logger.debug(f"Interactive data keys: {list(interactive_data.keys())}")
        logger.debug(f"Full interactive data:")
        logger.debug(json.dumps(interactive_data, indent=2))
        
        # Extract interactive details
        msg_type = interactive_data.get('type')
        
        if msg_type == 'button_reply':
            button_reply = interactive_data.get('button_reply', {})
            button_id = button_reply.get('id')
            title = button_reply.get('title')
            
            logger.debug(f"🔘 Button clicked:")
            logger.debug(f"  - ID: {button_id}")
            logger.debug(f"  - Title: {title}")
            
        elif msg_type == 'list_reply':
            list_reply = interactive_data.get('list_reply', {})
            list_id = list_reply.get('id')
            title = list_reply.get('title')
            
            logger.debug(f"📝 List item selected:")
            logger.debug(f"  - ID: {list_id}")
            logger.debug(f"  - Title: {title}")
    
    def debug_process_statuses(self, statuses):
        """Debug process status updates"""
        logger.debug("\n📊 PROCESSING STATUS UPDATES")
        logger.debug("="*40)
        
        for status_idx, status in enumerate(statuses):
            logger.debug(f"\n📈 STATUS {status_idx + 1}")
            logger.debug("-" * 30)
            
            status_id = status.get('id')
            status_value = status.get('status')
            timestamp = status.get('timestamp')
            recipient_id = status.get('recipient_id')
            
            logger.debug(f"Status ID: {status_id}")
            logger.debug(f"Status: {status_value}")
            logger.debug(f"Timestamp: {timestamp}")
            logger.debug(f"Recipient: {recipient_id}")
            
            # Log conversation and pricing info if available
            conversation = status.get('conversation')
            pricing = status.get('pricing')
            
            if conversation:
                logger.debug(f"Conversation: {json.dumps(conversation, indent=2)}")
            
            if pricing:
                logger.debug(f"Pricing: {json.dumps(pricing, indent=2)}")


# Additional debug function to test your setup
def debug_test_full_system():
    """
    Call this function to test your entire system
    Usage: python manage.py shell
    >>> from bot.views import debug_test_full_system
    >>> debug_test_full_system()
    """
    logger.debug("🚀 STARTING FULL SYSTEM DEBUG TEST")
    logger.debug("="*60)
    
    try:
        # Test 1: Import utils
        logger.debug("\n🔧 Testing imports...")
        from .utils import run_full_debug_test
        logger.debug("✅ Utils imported successfully")
        
        # Test 2: Run utils debug test
        logger.debug("\n🔧 Running utils debug test...")
        results = run_full_debug_test()
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.debug(f"{test_name}: {status}")
        
        # Test 3: Check database
        logger.debug("\n🗄️ Testing database...")
        from .models import Order
        
        recent_orders = Order.objects.all()[:5]
        logger.debug(f"Recent orders count: {len(recent_orders)}")
        
        for order in recent_orders:
            logger.debug(f"Order {order.order_id}: {order.status}")
        
        logger.debug("✅ FULL SYSTEM DEBUG TEST COMPLETED")
        
    except Exception as e:
        logger.error(f"❌ SYSTEM DEBUG TEST FAILED: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")