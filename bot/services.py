"""
WhatsApp Bot Service for EeOnam
Handles all WhatsApp messaging logic
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone

from .models import Order, UserSession, MenuItem
from .location_manager import location_manager
from .utils import (
    generate_order_id, 
    generate_qr_code, 
    upload_to_drive, 
    save_to_google_sheet,
    get_available_dates
)

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service class for WhatsApp API interactions"""
    
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        
    def send_message(self, to: str, message: str) -> bool:
        """Send a text message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        return self._make_request(payload)
    
    def send_interactive_message(self, to: str, message: str, buttons: List[Dict]) -> bool:
        """Send an interactive message with buttons"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": buttons
                }
            }
        }
        return self._make_request(payload)
    
    def send_list_message(self, to: str, message: str, button_text: str, sections: List[Dict]) -> bool:
        """Send a list message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }
        return self._make_request(payload)
    
    def send_image(self, to: str, image_url: str, caption: str = "") -> bool:
        """Send an image message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption
            }
        }
        return self._make_request(payload)
    
    def _make_request(self, payload: Dict) -> bool:
        """Make API request to WhatsApp"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Message sent successfully: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message: {e}")
            return False


class EeOnamBot:
    """Main bot logic handler"""
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        self.menu_items = self._load_menu_items()
        
    def _load_menu_items(self) -> Dict[str, Dict]:
        """Load menu items from database"""
        items = {}
        menu_items = MenuItem.objects.filter(is_available=True)
        for item in menu_items:
            items[str(item.id)] = {
                'name': item.name,
                'price': float(item.price),
                'description': item.description
            }
        return items
    
    def process_message(self, phone_number: str, message_text: str = None, 
                       message_type: str = "text", interactive_data: Dict = None,
                       location_data: Dict = None, media_data: Dict = None) -> bool:
        """Process incoming message and route to appropriate handler"""
        
        # Get or create user session
        session, created = UserSession.objects.get_or_create(
            phone_number=phone_number,
            defaults={'current_step': 'start'}
        )
        session.update_interaction()

        # Check for the 'start' message to reset the session
        if message_text and message_text.lower().strip() == 'start':
            session.current_step = 'start'
            session.save()
        
        try:
            if created or session.current_step == 'start':
                return self._handle_start(session)
            elif session.current_step == 'date_selection':
                return self._handle_date_selection(session, message_text, interactive_data)
            elif session.current_step == 'junction_selection':
                return self._handle_junction_selection(session, message_text, interactive_data)
            elif session.current_step == 'menu_selection':
                return self._handle_menu_selection(session, message_text)
            elif session.current_step == 'delivery_details':
                return self._handle_delivery_details(session, message_text, location_data)
            elif session.current_step == 'payment_qr':
                return self._handle_payment_qr(session, message_text)
            elif session.current_step == 'payment_screenshot':
                return self._handle_payment_screenshot(session, media_data)
            else:
                return self._handle_start(session)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.whatsapp.send_message(
                phone_number, 
                "Sorry, something went wrong. Please try again by typing 'start'."
            )
            return False
    
    def _handle_start(self, session: UserSession) -> bool:
        """Handle start of conversation"""
        welcome_message = (
            "🎉 *Welcome to EeOnam - OnamSadhya 2025!* 🎉\n\n"
            "We're excited to serve you delicious Onam Sadhya! "
            "Let's start by selecting your preferred delivery date.\n\n"
            "Please choose a date (minimum 3 days in advance):"
        )
        
        # Get available dates
        dates = get_available_dates()
        buttons = []
        
        for i, date in enumerate(dates[:3]):  # Show first 3 dates as buttons
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"date_{date.strftime('%Y-%m-%d')}",
                    "title": date.strftime('%d %b %Y')
                }
            })
        
        session.current_step = 'date_selection'
        session.save()
        
        return self.whatsapp.send_interactive_message(
            session.phone_number, welcome_message, buttons
        )
    
    def _handle_date_selection(self, session: UserSession, message_text: str, 
                              interactive_data: Dict) -> bool:
        """Handle date selection"""
        
        selected_date = None
        
        if interactive_data and interactive_data.get('button_reply'):
            button_id = interactive_data['button_reply']['id']
            if button_id.startswith('date_'):
                date_str = button_id.replace('date_', '')
                try:
                    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
        
        if not selected_date:
            # Try to parse text input
            try:
                selected_date = datetime.strptime(message_text.strip(), '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                dates = get_available_dates()
                date_list = '\n'.join([f"• {date.strftime('%d %b %Y')}" for date in dates[:7]])
                
                return self.whatsapp.send_message(
                    session.phone_number,
                    f"Please select a valid date. Available dates:\n\n{date_list}\n\n"
                    "You can click the buttons above or type the date in YYYY-MM-DD format."
                )
        
        # Validate date is available
        available_dates = get_available_dates()
        if selected_date not in available_dates:
            return self.whatsapp.send_message(
                session.phone_number,
                "Selected date is not available. Please choose from the available dates."
            )
        
        session.selected_date = selected_date
        session.current_step = 'junction_selection'
        session.save()
        
        # Show junction selection using location manager
        junction_message = (
            f"✅ Date selected: *{selected_date.strftime('%d %B %Y')}*\n\n"
            "Now, please select your preferred junction:\n\n"
            f"{location_manager.get_location_summary_text()}"
        )
        
        # Get WhatsApp buttons from location manager
        button_groups = location_manager.get_whatsapp_buttons(max_buttons=3)
        
        success_results = []
        for i, buttons in enumerate(button_groups):
            message = junction_message if i == 0 else "More options:"
            success = self.whatsapp.send_interactive_message(
                session.phone_number, message, buttons
            )
            success_results.append(success)
        
        return all(success_results)
    
    def _handle_junction_selection(self, session: UserSession, message_text: str,
                                  interactive_data: Dict) -> bool:
        """Handle junction selection"""
        
        selected_junction = None
        
        if interactive_data and interactive_data.get('button_reply'):
            selected_junction = interactive_data['button_reply']['id']
        
        # Validate junction using location manager
        if not location_manager.is_valid_location(selected_junction):
            return self.whatsapp.send_message(
                session.phone_number,
                "Please select a valid junction using the buttons provided."
            )
        
        session.selected_junction = selected_junction
        session.current_step = 'menu_selection'
        session.save()
        
        # Show menu
        return self._show_menu(session)
    
    def _show_menu(self, session: UserSession) -> bool:
        """Display menu to user"""
        
        # Get junction display name from location manager
        junction_display = location_manager.get_display_name(session.selected_junction)
        
        menu_message = (
            f"📍 Junction: *{junction_display}*\n"
            f"📅 Date: *{session.selected_date.strftime('%d %B %Y')}*\n\n"
            "🍽️ *Our Menu:*\n\n"
            "1️⃣ Veg Sadhya - ₹150\n"
            "2️⃣ Non-Veg Sadhya - ₹200\n"
            "3️⃣ Palada Pradhaman - ₹40\n"
            "4️⃣ Parippu/Gothambu Payasam - ₹40\n"
            "5️⃣ Kaaya Varuthathu - ₹30\n"
            "6️⃣ Sharkkaravaratti - ₹30\n\n"
            "*Note:* Payasams are included in sadhya, but can be ordered separately.\n\n"
            "Please reply with your order in this format:\n"
            "*Example:* 1 x 2, 3 x 1 (means 2 Veg Sadhya, 1 Palada Pradhaman)\n\n"
            "Just type the numbers and quantities you want!"
        )
        
        return self.whatsapp.send_message(session.phone_number, menu_message)
    
    def _handle_menu_selection(self, session: UserSession, message_text: str) -> bool:
        """Handle menu item selection and quantity"""
        
        try:
            # Parse order format: "1 x 2, 3 x 1"
            selected_items = self._parse_order(message_text.strip())
            
            if not selected_items:
                return self.whatsapp.send_message(
                    session.phone_number,
                    "Invalid format. Please use format like: 1 x 2, 3 x 1\n"
                    "Where numbers 1-6 represent menu items and quantities."
                )
            
            # Calculate total
            total_amount, order_summary = self._calculate_total(
                selected_items, session.selected_junction
            )
            
            # Store selected items
            session.selected_items = json.dumps(selected_items)
            
            # Show order summary
            summary_message = (
                "📋 *Order Summary:*\n\n"
                f"{order_summary}\n"
                f"💰 *Total: ₹{total_amount}*\n\n"
            )
            
            if 'delivery' in session.selected_junction:
                session.current_step = 'delivery_details'
                session.save()
                
                summary_message += (
                    "📍 Since you selected delivery, please share your delivery address.\n\n"
                    "You can either:\n"
                    "• Share your location using WhatsApp's location feature, OR\n"
                    "• Type your complete address"
                )
            else:
                # Skip to payment for pickup
                return self._generate_payment_qr(session, total_amount, order_summary)
            
            return self.whatsapp.send_message(session.phone_number, summary_message)
            
        except Exception as e:
            logger.error(f"Error in menu selection: {e}")
            return self.whatsapp.send_message(
                session.phone_number,
                "Error processing your order. Please try again with the correct format."
            )
    
    def _parse_order(self, order_text: str) -> Dict[int, int]:
        """Parse order text into item_id: quantity mapping"""
        
        # Menu item mapping
        menu_mapping = {
            1: 'Veg Sadhya',
            2: 'Non-Veg Sadhya', 
            3: 'Palada Pradhaman',
            4: 'Parippu/Gothambu Payasam',
            5: 'Kaaya Varuthathu',
            6: 'Sharkkaravaratti'
        }
        
        selected_items = {}
        
        # Split by comma and process each item
        items = order_text.split(',')
        
        for item in items:
            item = item.strip()
            # Match pattern like "1 x 2" or "1x2" or "1*2"
            import re
            match = re.match(r'(\d+)\s*[x*]\s*(\d+)', item, re.IGNORECASE)
            
            if match:
                item_id = int(match.group(1))
                quantity = int(match.group(2))
                
                if 1 <= item_id <= 6 and quantity > 0:
                    selected_items[item_id] = selected_items.get(item_id, 0) + quantity
        
        return selected_items
    
    def _calculate_total(self, selected_items: Dict[int, int], junction: str) -> Tuple[Decimal, str]:
        """Calculate total amount and generate order summary"""
        
        # Menu prices
        prices = {
            1: 150,  # Veg Sadhya
            2: 200,  # Non-Veg Sadhya
            3: 40,   # Palada Pradhaman
            4: 40,   # Parippu/Gothambu Payasam
            5: 30,   # Kaaya Varuthathu
            6: 30    # Sharkkaravaratti
        }
        
        names = {
            1: 'Veg Sadhya',
            2: 'Non-Veg Sadhya',
            3: 'Palada Pradhaman', 
            4: 'Parippu/Gothambu Payasam',
            5: 'Kaaya Varuthathu',
            6: 'Sharkkaravaratti'
        }
        
        total = 0
        summary_lines = []
        
        for item_id, quantity in selected_items.items():
            price = prices[item_id]
            item_total = price * quantity
            total += item_total
            
            summary_lines.append(
                f"• {names[item_id]} x {quantity} = ₹{item_total}"
            )
        
        # Add delivery fee if applicable
        if 'delivery' in junction:
            delivery_fee = 50
            total += delivery_fee
            summary_lines.append(f"• Delivery Fee = ₹{delivery_fee}")
        
        summary = '\n'.join(summary_lines)
        return Decimal(str(total)), summary
    
    def _handle_delivery_details(self, session: UserSession, message_text: str,
                                location_data: Dict) -> bool:
        """Handle delivery address input"""
        
        if location_data:
            # User shared location
            lat = location_data.get('latitude')
            lng = location_data.get('longitude')
            
            if lat and lng:
                # Corrected Google Maps URL format
                maps_link = f"https://www.google.com/maps/place/{lat},{lng}"
                session.maps_link = maps_link
                session.delivery_address = f"Location: {lat}, {lng}"
            else:
                return self.whatsapp.send_message(
                    session.phone_number,
                    "Unable to process location. Please share your location again or type your address."
                )
        
        elif message_text:
            # User typed address
            session.delivery_address = message_text.strip()
        
        else:
            return self.whatsapp.send_message(
                session.phone_number,
                "Please provide your delivery address or share your location."
            )
        
        session.save()
        
        # Calculate total and generate payment QR
        selected_items = json.loads(session.selected_items)
        total_amount, order_summary = self._calculate_total(
            selected_items, session.selected_junction
        )
        
        return self._generate_payment_qr(session, total_amount, order_summary)
    
    def _generate_payment_qr(self, session: UserSession, total_amount: Decimal, 
                           order_summary: str) -> bool:
        """Generate payment QR code"""
        
        # Generate order ID
        order_id = generate_order_id()
        
        # Generate QR code
        qr_url = generate_qr_code(float(total_amount), order_id)
        
        if not qr_url:
            return self.whatsapp.send_message(
                session.phone_number,
                "Error generating payment QR. Please try again."
            )
        
        # Create order record
        order = Order.objects.create(
            order_id=order_id,
            phone_number=session.phone_number,
            delivery_date=session.selected_date,
            junction=session.selected_junction,
            delivery_address=session.delivery_address or '',
            maps_link=session.maps_link or '',
            items=session.selected_items,
            total_amount=total_amount
        )
        
        session.current_order = order
        session.current_step = 'payment_screenshot'
        session.save()
        
        # Send QR code
        payment_message = (
            f"💳 *Payment Details*\n\n"
            f"Order ID: *{order_id}*\n"
            f"Amount: *₹{total_amount}*\n\n"
            f"📋 *Your Order:*\n{order_summary}\n\n"
            "Please scan the QR code below to make payment.\n"
            "After payment, send a screenshot of the transaction."
        )
        
        success1 = self.whatsapp.send_message(session.phone_number, payment_message)
        success2 = self.whatsapp.send_image(
            session.phone_number, 
            qr_url,
            f"Scan to pay ₹{total_amount} for Order {order_id}"
        )
        
        return success1 and success2
    
    def _handle_payment_screenshot(self, session: UserSession, media_data: Dict) -> bool:
        """Handle payment screenshot upload"""
        
        if not media_data or media_data.get('type') != 'image':
            return self.whatsapp.send_message(
                session.phone_number,
                "Please send a screenshot of your payment transaction."
            )
        
        # Download and upload screenshot
        media_url = media_data.get('url')
        if not media_url:
            return self.whatsapp.send_message(
                session.phone_number,
                "Unable to process image. Please try sending the screenshot again."
            )
        
        try:
            # Upload to Google Drive
            drive_url = upload_to_drive(media_url, session.current_order.order_id)
            
            if not drive_url:
                return self.whatsapp.send_message(
                    session.phone_number,
                    "Error uploading screenshot. Please try again."
                )
            
            # Update order
            order = session.current_order
            order.payment_screenshot_url = drive_url
            order.save()
            
            # Save to Google Sheet
            save_to_google_sheet(order)
            
            # Send confirmation
            confirmation_message = (
                f"✅ *Order Submitted Successfully!*\n\n"
                f"Order ID: *{order.order_id}*\n"
                f"Amount: *₹{order.total_amount}*\n"
                f"Date: *{order.delivery_date.strftime('%d %B %Y')}*\n\n"
                "Your payment screenshot has been received and is under verification.\n"
                "You will receive a confirmation message once verified.\n\n"
                "Thank you for ordering with EeOnam! 🎉"
            )
            
            session.current_step = 'completed'
            session.save()
            
            return self.whatsapp.send_message(session.phone_number, confirmation_message)
            
        except Exception as e:
            logger.error(f"Error processing payment screenshot: {e}")
            return self.whatsapp.send_message(
                session.phone_number,
                "Error processing your screenshot. Please try again."
            )
    
    def send_verification_result(self, order: Order, verified: bool) -> bool:
        """Send verification result to customer"""
        
        if verified:
            message = (
                f"✅ *Payment Verified!*\n\n"
                f"Order ID: *{order.order_id}*\n"
                f"Amount: *₹{order.total_amount}*\n"
                f"Date: *{order.delivery_date.strftime('%d %B %Y')}*\n\n"
                "Your order has been confirmed! We'll prepare your delicious Onam Sadhya.\n\n"
                "Thank you for choosing EeOnam! 🎉"
            )
        else:
            message = (
                f"❌ *Payment Verification Failed*\n\n"
                f"Order ID: *{order.order_id}*\n\n"
                "There was an issue with your payment verification. "
                "Please contact us or submit a new order.\n\n"
                "We apologize for any inconvenience."
            )
        
        return self.whatsapp.send_message(order.phone_number, message)