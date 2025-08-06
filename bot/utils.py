"""
Utility functions for EeOnam bot
"""

import io
import json
import logging
import os
import random
import string
from datetime import datetime, timedelta
from typing import List, Optional

import qrcode
import requests
from django.conf import settings
from django.utils import timezone
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread

logger = logging.getLogger(__name__)


def generate_order_id() -> str:
    """Generate a unique order ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"EO{timestamp}{random_suffix}"


def get_available_dates(days_ahead: int = 14) -> List[datetime.date]:
    """Get list of available dates (starting 3 days from today)"""
    today = timezone.now().date()
    start_date = today + timedelta(days=3)  # Minimum 3 days advance
    
    available_dates = []
    for i in range(days_ahead):
        date = start_date + timedelta(days=i)
        available_dates.append(date)
    
    return available_dates


def generate_qr_code(amount: float, order_id: str) -> Optional[str]:
    """Generate UPI QR code and return its URL"""
    
    try:
        # UPI payment string
        upi_string = (
            f"upi://pay?"
            f"pa={settings.UPI_ID}&"
            f"pn={settings.UPI_MERCHANT_NAME}&"
            f"am={amount}&"
            f"cu=INR&"
            f"tn=Order_{order_id}"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Upload to Google Drive and get public URL
        drive_url = upload_qr_to_drive(img_buffer, f"qr_{order_id}.png")
        
        return drive_url
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None


def upload_qr_to_drive(image_buffer: io.BytesIO, filename: str) -> Optional[str]:
    """Upload QR code image to Google Drive and return public URL"""
    
    try:
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            return None
        
        # Build Drive service
        service = build('drive', 'v3', credentials=creds)
        
        # File metadata
        file_metadata = {
            'name': filename,
            'parents': [settings.GOOGLE_DRIVE_FOLDER_ID]
        }
        
        # Upload file
        media = MediaIoBaseUpload(image_buffer, mimetype='image/png')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Make file publicly viewable
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # Return direct link
        return f"https://drive.google.com/uc?id={file_id}"
        
    except Exception as e:
        logger.error(f"Error uploading QR to Drive: {e}")
        return None


def upload_to_drive(media_url: str, order_id: str) -> Optional[str]:
    """Download media from WhatsApp and upload to Google Drive"""
    
    try:
        # Download image from WhatsApp
        headers = {
            'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'
        }
        
        response = requests.get(media_url, headers=headers)
        response.raise_for_status()
        
        # Create buffer
        img_buffer = io.BytesIO(response.content)
        
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            return None
        
        # Build Drive service
        service = build('drive', 'v3', credentials=creds)
        
        # File metadata
        filename = f"payment_screenshot_{order_id}.jpg"
        file_metadata = {
            'name': filename,
            'parents': [settings.GOOGLE_DRIVE_FOLDER_ID]
        }
        
        # Upload file
        media = MediaIoBaseUpload(img_buffer, mimetype='image/jpeg')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Make file publicly viewable
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # Return direct link
        return f"https://drive.google.com/uc?id={file_id}"
        
    except Exception as e:
        logger.error(f"Error uploading to Drive: {e}")
        return None


def get_google_credentials():
    """Get Google API credentials"""
    
    try:
        credentials_path = settings.GOOGLE_CREDENTIALS_JSON
        if not os.path.exists(credentials_path):
            logger.error(f"Google credentials file not found: {credentials_path}")
            return None
        
        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
        )
        
        return creds
        
    except Exception as e:
        logger.error(f"Error getting Google credentials: {e}")
        return None


def save_to_google_sheet(order) -> bool:
    """Save order details to Google Sheet"""
    
    try:
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            return False
        
        # Connect to Google Sheets
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        
        # Parse items for display
        items_dict = json.loads(order.items)
        items_display = parse_items_for_display(items_dict)
        
        # Get junction display name
        from .models import Order
        junction_display = dict(Order.JUNCTION_CHOICES)[order.junction]
        
        # Prepare row data
        row_data = [
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
            order.phone_number,  # Phone
            junction_display,  # Junction
            order.delivery_date.strftime('%Y-%m-%d'),  # Delivery Date
            order.order_id,  # Order ID
            items_display,  # Items
            float(order.total_amount),  # Total
            order.delivery_address,  # Delivery Address
            order.maps_link or '',  # Maps Link
            order.payment_screenshot_url or '',  # Drive Link
            order.get_verification_url(),  # Verification Link
            order.get_rejection_url(),  # Rejection Link
            order.status.title()  # Verified Status
        ]
        
        # Add row to sheet
        sheet.append_row(row_data)
        
        # Update order with sheet row number
        order.sheet_row_number = len(sheet.get_all_values())
        order.save(update_fields=['sheet_row_number'])
        
        logger.info(f"Order {order.order_id} saved to Google Sheet")
        return True
        
    except Exception as e:
        logger.error(f"Error saving to Google Sheet: {e}")
        return False


def parse_items_for_display(items_dict: dict) -> str:
    """Parse items dictionary to readable string"""
    
    names = {
        1: 'Veg Sadhya',
        2: 'Non-Veg Sadhya',
        3: 'Palada Pradhaman',
        4: 'Parippu/Gothambu Payasam',
        5: 'Kaaya Varuthathu',
        6: 'Sharkkaravaratti'
    }
    
    # Convert string keys to int if necessary
    if isinstance(list(items_dict.keys())[0], str):
        items_dict = {int(k): v for k, v in items_dict.items()}
    
    items_list = []
    for item_id, quantity in items_dict.items():
        if item_id in names:
            items_list.append(f"{names[item_id]} x {quantity}")
    
    return ', '.join(items_list)


def update_sheet_verification_status(order, status: str) -> bool:
    """Update verification status in Google Sheet"""
    
    try:
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            return False
        
        # Connect to Google Sheets
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        
        if order.sheet_row_number:
            # Update status column (column 13)
            sheet.update_cell(order.sheet_row_number, 13, status.title())
            logger.info(f"Updated verification status for order {order.order_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error updating sheet status: {e}")
        return False


def initialize_google_sheet() -> bool:
    """Initialize Google Sheet with headers"""
    
    try:
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            return False
        
        # Connect to Google Sheets
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        
        # Check if headers exist
        existing_headers = sheet.row_values(1)
        
        if not existing_headers:
            # Add headers
            headers = [
                'Timestamp', 'Phone', 'Junction', 'Delivery Date', 'Order ID',
                'Items', 'Total', 'Delivery Address', 'Maps Link', 'Drive Link',
                'Verification Link', 'Rejection Link', 'Verified Status'
            ]
            
            sheet.append_row(headers)
            logger.info("Google Sheet initialized with headers")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Google Sheet: {e}")
        return False
