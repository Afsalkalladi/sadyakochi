import cloudinary
import cloudinary.uploader
"""
Utility functions for EeOnam bot - DEBUG VERSION with extensive logging
Now uses JSON for token storage instead of pickle for Render compatibility.
"""
"""
Google API utility functions for EeOnam.
Uses JSON for token storage (token.json) and environment variables for configuration.
No pickle usage; fully compatible with Render and modern Google API best practices.
"""

import io
import json
import logging
import os
import random
import string
import traceback
from datetime import datetime, timedelta
from typing import List, Optional

import qrcode
import requests
from django.conf import settings
from django.utils import timezone
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


def debug_log_settings():
    logger.debug("=== SETTINGS DEBUG ===")
    logger.debug(f"UPI_ID: {'SET' if hasattr(settings, 'UPI_ID') else 'NOT SET'}")
    logger.debug(f"UPI_MERCHANT_NAME: {'SET' if hasattr(settings, 'UPI_MERCHANT_NAME') else 'NOT SET'}")
    logger.debug(f"GOOGLE_DRIVE_FOLDER_ID: {'SET' if hasattr(settings, 'GOOGLE_DRIVE_FOLDER_ID') else 'NOT SET'}")
    logger.debug(f"GOOGLE_SHEET_ID: {'SET' if hasattr(settings, 'GOOGLE_SHEET_ID') else 'NOT SET'}")
    logger.debug(f"WHATSAPP_ACCESS_TOKEN: {'SET' if hasattr(settings, 'WHATSAPP_ACCESS_TOKEN') else 'NOT SET'}")
    logger.debug("=== END SETTINGS DEBUG ===")


def generate_order_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    order_id = f"EO{timestamp}{random_suffix}"
    return order_id


def get_available_dates(days_ahead: int = 14) -> List[datetime.date]:
    today = timezone.now().date()
    start_date = today + timedelta(days=3)
    return [start_date + timedelta(days=i) for i in range(days_ahead)]


def test_google_credentials():
    try:
        creds = get_google_credentials()
        if not creds:
            return False
        
        service = build('drive', 'v3', credentials=creds)
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)
        if folder_id:
            service.files().get(fileId=folder_id).execute()
        else:
            return False
        
        gc = gspread.authorize(creds)
        sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None)
        if sheet_id:
            gc.open_by_key(sheet_id)
        else:
            return False
        
        return True
    except Exception:
        logger.error(traceback.format_exc())
        return False


def generate_qr_code(amount: float, order_id: str) -> Optional[str]:
    try:
        upi_string = (
            f"upi://pay?"
            f"pa={settings.UPI_ID}&"
            f"pn={settings.UPI_MERCHANT_NAME}&"
            f"am={amount}&"
            f"cu=INR&"
            f"tn=Order_{order_id}"
        )
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        # Upload to Cloudinary
        cloudinary.config(
            cloud_name=getattr(settings, 'CLOUDINARY_CLOUD_NAME', None),
            api_key=getattr(settings, 'CLOUDINARY_API_KEY', None),
            api_secret=getattr(settings, 'CLOUDINARY_API_SECRET', None)
        )
        result = cloudinary.uploader.upload(
            img_buffer,
            folder="qr_codes",
            public_id=f"qr_{order_id}",
            overwrite=True,
            resource_type="image"
        )
        qr_url = result.get('secure_url')
        return qr_url
    except Exception:
        logger.error(traceback.format_exc())
        return None


def upload_qr_to_drive(image_buffer: io.BytesIO, filename: str) -> Optional[str]:
    try:
        creds = get_google_credentials()
        if not creds:
            return None
        service = build('drive', 'v3', credentials=creds)
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)
        if not folder_id:
            return None
        
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(image_buffer, mimetype='image/png')
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id'
        ).execute()
        
        file_id = file.get('id')
        service.permissions().create(
            fileId=file_id, body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        return f"https://drive.google.com/uc?id={file_id}"
    except Exception:
        logger.error(traceback.format_exc())
        return None


def upload_to_drive(media_url: str, order_id: str) -> Optional[str]:
    try:
        headers = {'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'}
        response = requests.get(media_url, headers=headers, timeout=30)
        response.raise_for_status()
        img_buffer = io.BytesIO(response.content)
        
        creds = get_google_credentials()
        if not creds:
            return None
        service = build('drive', 'v3', credentials=creds)
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)
        if not folder_id:
            return None
        
        file_metadata = {'name': f"payment_screenshot_{order_id}.jpg", 'parents': [folder_id]}
        media = MediaIoBaseUpload(img_buffer, mimetype='image/jpeg')
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id'
        ).execute()
        
        file_id = file.get('id')
        service.permissions().create(
            fileId=file_id, body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        return f"https://drive.google.com/uc?id={file_id}"
    except Exception:
        logger.error(traceback.format_exc())
        return None


def get_google_credentials():
    """Load credentials from JSON token file (token.json) using env config."""
    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    token_path = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.json')
    
    creds = None
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r') as token_file:
                token_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            logger.error(traceback.format_exc())
            return None
    else:
        logger.error(f"Token file not found: {token_path}")
        return None
    
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
        except Exception:
            logger.error(traceback.format_exc())
            return None
    
    if not creds or not creds.valid:
        logger.error("Invalid or missing credentials.")
        return None
    return creds


def debug_save_to_google_sheet(order) -> bool:
    try:
        creds = get_google_credentials()
        if not creds:
            return False
        gc = gspread.authorize(creds)
        sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None)
        if not sheet_id:
            return False
        workbook = gc.open_by_key(sheet_id)
        sheet = workbook.sheet1
        
        items_dict = json.loads(order.items)
        items_display = parse_items_for_display(items_dict)
        
        from .models import Order
        junction_display = dict(Order.JUNCTION_CHOICES)[order.junction]
        
        row_data = [
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.phone_number,
            junction_display,
            order.delivery_date.strftime('%Y-%m-%d'),
            order.order_id,
            items_display,
            float(order.total_amount),
            order.delivery_address,
            order.maps_link or '',
            order.payment_screenshot_url or '',
            order.get_verification_url(),
            order.get_rejection_url(),
            order.status.title()
        ]
        
        sheet.append_row(row_data)
        all_values = sheet.get_all_values()
        order.sheet_row_number = len(all_values)
        order.save(update_fields=['sheet_row_number'])
        return True
    except Exception:
        logger.error(traceback.format_exc())
        return False


save_to_google_sheet = debug_save_to_google_sheet


def parse_items_for_display(items_dict: dict) -> str:
    names = {
        1: 'Veg Sadhya',
        2: 'Non-Veg Sadhya',
        3: 'Palada Pradhaman',
        4: 'Parippu/Gothambu Payasam',
        5: 'Kaaya Varuthathu',
        6: 'Sharkkaravaratti'
    }
    if isinstance(list(items_dict.keys())[0], str):
        items_dict = {int(k): v for k, v in items_dict.items()}
    return ', '.join(f"{names[i]} x {q}" for i, q in items_dict.items() if i in names)


def update_sheet_verification_status(order, status: str) -> bool:
    try:
        creds = get_google_credentials()
        if not creds:
            return False
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        if order.sheet_row_number:
            sheet.update_cell(order.sheet_row_number, 13, status.title())
            return True
        return False
    except Exception:
        logger.error(traceback.format_exc())
        return False


def initialize_google_sheet() -> bool:
    try:
        creds = get_google_credentials()
        if not creds:
            return False
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        if not sheet.row_values(1):
            headers = [
                'Timestamp', 'Phone', 'Junction', 'Delivery Date', 'Order ID',
                'Items', 'Total', 'Delivery Address', 'Maps Link', 'Drive Link',
                'Verification Link', 'Rejection Link', 'Verified Status'
            ]
            sheet.append_row(headers)
        return True
    except Exception:
        logger.error(traceback.format_exc())
        return False
