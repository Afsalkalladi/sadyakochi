"""
Utility functions for EeOnam bot - DEBUG VERSION with extensive logging
"""

import io
import json
import logging
import os
import random
import string
import pickle
import traceback
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
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Enable detailed debugging
logging.basicConfig(level=logging.DEBUG)


def debug_log_settings():
    """Debug function to log important settings"""
    logger.debug("=== SETTINGS DEBUG ===")
    logger.debug(f"UPI_ID: {'SET' if hasattr(settings, 'UPI_ID') else 'NOT SET'}")
    logger.debug(f"UPI_MERCHANT_NAME: {'SET' if hasattr(settings, 'UPI_MERCHANT_NAME') else 'NOT SET'}")
    logger.debug(f"GOOGLE_DRIVE_FOLDER_ID: {'SET' if hasattr(settings, 'GOOGLE_DRIVE_FOLDER_ID') else 'NOT SET'}")
    logger.debug(f"GOOGLE_SHEET_ID: {'SET' if hasattr(settings, 'GOOGLE_SHEET_ID') else 'NOT SET'}")
    logger.debug(f"WHATSAPP_ACCESS_TOKEN: {'SET' if hasattr(settings, 'WHATSAPP_ACCESS_TOKEN') else 'NOT SET'}")
    logger.debug("=== END SETTINGS DEBUG ===")


def generate_order_id() -> str:
    """Generate a unique order ID"""
    logger.debug("🔄 Generating order ID...")
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    order_id = f"EO{timestamp}{random_suffix}"
    logger.debug(f"✅ Generated order ID: {order_id}")
    return order_id


def get_available_dates(days_ahead: int = 14) -> List[datetime.date]:
    """Get list of available dates (starting 3 days from today)"""
    logger.debug(f"🔄 Getting available dates for {days_ahead} days ahead...")
    today = timezone.now().date()
    start_date = today + timedelta(days=3)  # Minimum 3 days advance
    
    available_dates = []
    for i in range(days_ahead):
        date = start_date + timedelta(days=i)
        available_dates.append(date)
    
    logger.debug(f"✅ Generated {len(available_dates)} available dates from {start_date}")
    return available_dates


def test_google_credentials():
    """Test Google credentials connectivity"""
    logger.debug("🔄 Testing Google credentials...")
    
    try:
        creds = get_google_credentials()
        if not creds:
            logger.error("❌ Failed to get Google credentials")
            return False
        
        logger.debug("✅ Google credentials obtained successfully")
        logger.debug(f"Credentials valid: {creds.valid}")
        logger.debug(f"Credentials expired: {creds.expired if hasattr(creds, 'expired') else 'Unknown'}")
        
        # Test Drive API connection
        logger.debug("🔄 Testing Google Drive API connection...")
        service = build('drive', 'v3', credentials=creds)
        
        # Try to get folder info
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)
        if folder_id:
            folder_info = service.files().get(fileId=folder_id).execute()
            logger.debug(f"✅ Drive folder accessible: {folder_info.get('name', 'Unknown')}")
        else:
            logger.error("❌ GOOGLE_DRIVE_FOLDER_ID not set")
            return False
        
        # Test Sheets API connection
        logger.debug("🔄 Testing Google Sheets API connection...")
        gc = gspread.authorize(creds)
        sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None)
        if sheet_id:
            sheet = gc.open_by_key(sheet_id)
            logger.debug(f"✅ Google Sheet accessible: {sheet.title}")
        else:
            logger.error("❌ GOOGLE_SHEET_ID not set")
            return False
        
        logger.debug("✅ All Google API connections successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Google credentials test failed: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def generate_qr_code(amount: float, order_id: str) -> Optional[str]:
    """Generate UPI QR code and return its URL"""
    logger.debug(f"🔄 Generating QR code for order {order_id}, amount: ₹{amount}")
    
    try:
        # Debug settings
        if not hasattr(settings, 'UPI_ID'):
            logger.error("❌ UPI_ID not found in settings")
            return None
        if not hasattr(settings, 'UPI_MERCHANT_NAME'):
            logger.error("❌ UPI_MERCHANT_NAME not found in settings")
            return None
            
        logger.debug(f"Using UPI ID: {settings.UPI_ID}")
        
        # UPI payment string
        upi_string = (
            f"upi://pay?"
            f"pa={settings.UPI_ID}&"
            f"pn={settings.UPI_MERCHANT_NAME}&"
            f"am={amount}&"
            f"cu=INR&"
            f"tn=Order_{order_id}"
        )
        logger.debug(f"UPI string generated: {upi_string}")
        
        # Generate QR code
        logger.debug("🔄 Creating QR code image...")
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
        logger.debug("✅ QR code image created successfully")
        
        # Save to BytesIO
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        logger.debug(f"QR code image size: {len(img_buffer.getvalue())} bytes")
        
        # Upload to Google Drive and get public URL
        logger.debug("🔄 Uploading QR code to Google Drive...")
        drive_url = upload_qr_to_drive(img_buffer, f"qr_{order_id}.png")
        
        if drive_url:
            logger.debug(f"✅ QR code uploaded successfully: {drive_url}")
        else:
            logger.error("❌ Failed to upload QR code to Drive")
        
        return drive_url
        
    except Exception as e:
        logger.error(f"❌ Error generating QR code: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


def upload_qr_to_drive(image_buffer: io.BytesIO, filename: str) -> Optional[str]:
    """Upload QR code image to Google Drive and return public URL"""
    logger.debug(f"🔄 Uploading QR to Drive: {filename}")
    
    try:
        # Get credentials
        logger.debug("🔄 Getting Google credentials for Drive upload...")
        creds = get_google_credentials()
        if not creds:
            logger.error("❌ Failed to get credentials for Drive upload")
            return None
        logger.debug("✅ Credentials obtained for Drive upload")
        
        # Build Drive service
        logger.debug("🔄 Building Google Drive service...")
        service = build('drive', 'v3', credentials=creds)
        logger.debug("✅ Google Drive service built successfully")
        
        # Check folder ID
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)
        if not folder_id:
            logger.error("❌ GOOGLE_DRIVE_FOLDER_ID not set")
            return None
        logger.debug(f"Using Drive folder ID: {folder_id}")
        
        # File metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        logger.debug(f"File metadata: {file_metadata}")
        
        # Check buffer size
        buffer_size = len(image_buffer.getvalue())
        logger.debug(f"Image buffer size: {buffer_size} bytes")
        
        # Upload file
        logger.debug("🔄 Uploading file to Drive...")
        media = MediaIoBaseUpload(image_buffer, mimetype='image/png')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        if not file_id:
            logger.error("❌ No file ID returned from Drive upload")
            return None
        logger.debug(f"✅ File uploaded successfully, ID: {file_id}")
        
        # Make file publicly viewable
        logger.debug("🔄 Making file publicly viewable...")
        service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        logger.debug("✅ File permissions set to public")
        
        # Return direct link
        drive_url = f"https://drive.google.com/uc?id={file_id}"
        logger.debug(f"✅ Drive URL generated: {drive_url}")
        return drive_url
        
    except Exception as e:
        logger.error(f"❌ Error uploading QR to Drive: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


def debug_whatsapp_media_download(media_url: str) -> bool:
    """Debug WhatsApp media download process"""
    logger.debug(f"🔄 Testing WhatsApp media download from: {media_url}")
    
    try:
        # Check if access token is set
        if not hasattr(settings, 'WHATSAPP_ACCESS_TOKEN'):
            logger.error("❌ WHATSAPP_ACCESS_TOKEN not found in settings")
            return False
        
        token = settings.WHATSAPP_ACCESS_TOKEN
        logger.debug(f"Using access token (first 10 chars): {token[:10]}...")
        
        # Test headers
        headers = {
            'Authorization': f'Bearer {token}'
        }
        logger.debug(f"Request headers: {headers}")
        
        # Make request
        logger.debug("🔄 Making request to WhatsApp media URL...")
        response = requests.get(media_url, headers=headers, timeout=30)
        
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            logger.error(f"❌ WhatsApp media request failed with status: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return False
        
        content_length = len(response.content)
        logger.debug(f"✅ Media downloaded successfully, size: {content_length} bytes")
        
        # Check content type
        content_type = response.headers.get('content-type', 'unknown')
        logger.debug(f"Content type: {content_type}")
        
        if content_length == 0:
            logger.error("❌ Downloaded media has 0 bytes")
            return False
        
        return True
        
    except requests.exceptions.Timeout:
        logger.error("❌ WhatsApp media download timed out")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ WhatsApp media download failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in media download test: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def upload_to_drive(media_url: str, order_id: str) -> Optional[str]:
    """Download media from WhatsApp and upload to Google Drive - DEBUG VERSION"""
    logger.debug(f"🔄 Starting media upload process for order: {order_id}")
    logger.debug(f"Media URL: {media_url}")
    
    try:
        # Test WhatsApp media download first
        logger.debug("🔄 Testing WhatsApp media download...")
        if not debug_whatsapp_media_download(media_url):
            logger.error("❌ WhatsApp media download test failed")
            return None
        
        # Download image from WhatsApp
        logger.debug("🔄 Downloading image from WhatsApp...")
        headers = {
            'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'
        }
        
        response = requests.get(media_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content_length = len(response.content)
        content_type = response.headers.get('content-type', 'unknown')
        logger.debug(f"✅ Media downloaded: {content_length} bytes, type: {content_type}")
        
        if content_length == 0:
            logger.error("❌ Downloaded media is empty")
            return None
        
        # Create buffer
        logger.debug("🔄 Creating image buffer...")
        img_buffer = io.BytesIO(response.content)
        logger.debug(f"✅ Image buffer created with {len(img_buffer.getvalue())} bytes")
        
        # Get credentials
        logger.debug("🔄 Getting Google credentials...")
        creds = get_google_credentials()
        if not creds:
            logger.error("❌ Failed to get Google credentials")
            return None
        logger.debug("✅ Google credentials obtained")
        
        # Build Drive service
        logger.debug("🔄 Building Google Drive service...")
        service = build('drive', 'v3', credentials=creds)
        logger.debug("✅ Google Drive service built")
        
        # Check folder ID
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None)
        if not folder_id:
            logger.error("❌ GOOGLE_DRIVE_FOLDER_ID not set")
            return None
        logger.debug(f"Using folder ID: {folder_id}")
        
        # File metadata
        filename = f"payment_screenshot_{order_id}.jpg"
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        logger.debug(f"File metadata: {file_metadata}")
        
        # Determine MIME type based on content
        mime_type = 'image/jpeg'
        if content_type and 'image' in content_type:
            mime_type = content_type
        logger.debug(f"Using MIME type: {mime_type}")
        
        # Upload file
        logger.debug("🔄 Uploading file to Google Drive...")
        media = MediaIoBaseUpload(img_buffer, mimetype=mime_type)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,size'
        ).execute()
        
        file_id = file.get('id')
        file_name = file.get('name')
        file_size = file.get('size')
        
        if not file_id:
            logger.error("❌ No file ID returned from Drive upload")
            return None
        
        logger.debug(f"✅ File uploaded successfully:")
        logger.debug(f"  - ID: {file_id}")
        logger.debug(f"  - Name: {file_name}")
        logger.debug(f"  - Size: {file_size} bytes")
        
        # Make file publicly viewable
        logger.debug("🔄 Setting file permissions to public...")
        permission_result = service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        logger.debug(f"✅ Permissions set: {permission_result.get('id', 'unknown')}")
        
        # Return direct link
        drive_url = f"https://drive.google.com/uc?id={file_id}"
        logger.debug(f"✅ Final Drive URL: {drive_url}")
        return drive_url
        
    except requests.exceptions.Timeout:
        logger.error("❌ Request timed out during media upload")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error during media upload: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Error uploading media to Drive: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None


def get_google_credentials():
    """Get Google API credentials using a pre-generated token.pickle file - DEBUG VERSION"""
    logger.debug("🔄 Getting Google credentials...")
    
    creds = None
    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    logger.debug(f"Required scopes: {SCOPES}")

    # The file token.pickle stores the user's access and refresh tokens.
    token_path = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.pickle')
    logger.debug(f"Token path: {token_path}")
    logger.debug(f"Token file exists: {os.path.exists(token_path)}")
    
    if os.path.exists(token_path):
        try:
            logger.debug("🔄 Loading credentials from token file...")
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            logger.debug("✅ Credentials loaded from pickle file")
        except Exception as e:
            logger.error(f"❌ Error loading token file: {str(e)}")
            return None
    else:
        logger.error(f"❌ Token file not found at: {token_path}")
        return None
    
    # Check credentials status
    if creds:
        logger.debug(f"Credentials valid: {creds.valid}")
        logger.debug(f"Credentials expired: {creds.expired}")
        logger.debug(f"Has refresh token: {bool(creds.refresh_token)}")
        
        # If the token is expired, try to refresh it
        if creds.expired and creds.refresh_token:
            try:
                logger.debug("🔄 Refreshing expired credentials...")
                creds.refresh(Request())
                logger.debug("✅ Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"❌ Error refreshing credentials: {str(e)}")
                return None
    
    if not creds or not creds.valid:
        logger.error("❌ OAuth token is invalid or missing")
        return None
    
    logger.debug("✅ Valid Google credentials obtained")
    return creds


def debug_save_to_google_sheet(order) -> bool:
    """Debug version of save_to_google_sheet with extensive logging"""
    logger.debug(f"🔄 Starting Google Sheet save for order: {order.order_id}")
    
    try:
        # Get credentials
        logger.debug("🔄 Getting credentials for Sheet access...")
        creds = get_google_credentials()
        if not creds:
            logger.error("❌ Failed to get credentials for Sheet")
            return False
        logger.debug("✅ Credentials obtained for Sheet")
        
        # Connect to Google Sheets
        logger.debug("🔄 Connecting to Google Sheets...")
        gc = gspread.authorize(creds)
        logger.debug("✅ Google Sheets client authorized")
        
        sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None)
        if not sheet_id:
            logger.error("❌ GOOGLE_SHEET_ID not set")
            return False
        logger.debug(f"Using sheet ID: {sheet_id}")
        
        logger.debug("🔄 Opening Google Sheet...")
        workbook = gc.open_by_key(sheet_id)
        sheet = workbook.sheet1
        logger.debug(f"✅ Sheet opened: {workbook.title}")
        
        # Log order details
        logger.debug(f"Order details:")
        logger.debug(f"  - Order ID: {order.order_id}")
        logger.debug(f"  - Phone: {order.phone_number}")
        logger.debug(f"  - Total: {order.total_amount}")
        logger.debug(f"  - Items: {order.items}")
        logger.debug(f"  - Status: {order.status}")
        
        # Parse items for display
        logger.debug("🔄 Parsing items for display...")
        items_dict = json.loads(order.items)
        items_display = parse_items_for_display(items_dict)
        logger.debug(f"Items display: {items_display}")
        
        # Get junction display name
        from .models import Order
        junction_display = dict(Order.JUNCTION_CHOICES)[order.junction]
        logger.debug(f"Junction display: {junction_display}")
        
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
        
        logger.debug(f"Row data prepared: {len(row_data)} columns")
        for i, data in enumerate(row_data):
            logger.debug(f"  Column {i+1}: {data}")
        
        # Add row to sheet
        logger.debug("🔄 Appending row to sheet...")
        sheet.append_row(row_data)
        logger.debug("✅ Row appended successfully")
        
        # Update order with sheet row number
        logger.debug("🔄 Getting sheet row count...")
        all_values = sheet.get_all_values()
        row_count = len(all_values)
        logger.debug(f"Total rows in sheet: {row_count}")
        
        order.sheet_row_number = row_count
        order.save(update_fields=['sheet_row_number'])
        logger.debug(f"✅ Order updated with sheet row number: {row_count}")
        
        logger.debug(f"✅ Order {order.order_id} saved to Google Sheet successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving to Google Sheet: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


# Replace the original function with debug version
save_to_google_sheet = debug_save_to_google_sheet


def parse_items_for_display(items_dict: dict) -> str:
    """Parse items dictionary to readable string - DEBUG VERSION"""
    logger.debug(f"🔄 Parsing items: {items_dict}")
    
    names = {
        1: 'Veg Sadhya',
        2: 'Non-Veg Sadhya',
        3: 'Palada Pradhaman',
        4: 'Parippu/Gothambu Payasam',
        5: 'Kaaya Varuthathu',
        6: 'Sharkkaravaratti'
    }
    logger.debug(f"Available items: {names}")
    
    # Convert string keys to int if necessary
    if isinstance(list(items_dict.keys())[0], str):
        logger.debug("Converting string keys to integers")
        items_dict = {int(k): v for k, v in items_dict.items()}
    
    items_list = []
    for item_id, quantity in items_dict.items():
        logger.debug(f"Processing item {item_id}: {quantity}")
        if item_id in names:
            item_text = f"{names[item_id]} x {quantity}"
            items_list.append(item_text)
            logger.debug(f"Added: {item_text}")
        else:
            logger.warning(f"Unknown item ID: {item_id}")
    
    result = ', '.join(items_list)
    logger.debug(f"✅ Items display result: {result}")
    return result


def update_sheet_verification_status(order, status: str) -> bool:
    """Update verification status in Google Sheet - DEBUG VERSION"""
    logger.debug(f"🔄 Updating sheet verification status for {order.order_id} to {status}")
    
    try:
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            logger.error("❌ Failed to get credentials for status update")
            return False
        
        # Connect to Google Sheets
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        
        if order.sheet_row_number:
            logger.debug(f"Updating row {order.sheet_row_number}, column 13 with status: {status}")
            # Update status column (column 13)
            sheet.update_cell(order.sheet_row_number, 13, status.title())
            logger.debug(f"✅ Updated verification status for order {order.order_id}")
            return True
        else:
            logger.error(f"❌ No sheet row number found for order {order.order_id}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error updating sheet status: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def initialize_google_sheet() -> bool:
    """Initialize Google Sheet with headers - DEBUG VERSION"""
    logger.debug("🔄 Initializing Google Sheet...")
    
    try:
        # Get credentials
        creds = get_google_credentials()
        if not creds:
            logger.error("❌ Failed to get credentials for sheet initialization")
            return False
        
        # Connect to Google Sheets
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1
        logger.debug(f"✅ Connected to sheet: {sheet.title}")
        
        # Check if headers exist
        logger.debug("🔄 Checking existing headers...")
        existing_headers = sheet.row_values(1)
        logger.debug(f"Existing headers: {existing_headers}")
        
        if not existing_headers:
            logger.debug("🔄 No headers found, adding them...")
            # Add headers
            headers = [
                'Timestamp', 'Phone', 'Junction', 'Delivery Date', 'Order ID',
                'Items', 'Total', 'Delivery Address', 'Maps Link', 'Drive Link',
                'Verification Link', 'Rejection Link', 'Verified Status'
            ]
            
            sheet.append_row(headers)
            logger.debug(f"✅ Headers added: {headers}")
        else:
            logger.debug("✅ Headers already exist")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error initializing Google Sheet: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def run_full_debug_test():
    """Run comprehensive debug test of all systems"""
    logger.debug("🚀 Starting full debug test...")
    
    # Test 1: Settings
    logger.debug("\n" + "="*50)
    logger.debug("TEST 1: SETTINGS")
    logger.debug("="*50)
    debug_log_settings()
    
    # Test 2: Google Credentials
    logger.debug("\n" + "="*50)
    logger.debug("TEST 2: GOOGLE CREDENTIALS")
    logger.debug("="*50)
    creds_result = test_google_credentials()
    logger.debug(f"Google credentials test result: {'PASS' if creds_result else 'FAIL'}")
    
    # Test 3: WhatsApp Media (if URL provided)
    logger.debug("\n" + "="*50)
    logger.debug("TEST 3: WHATSAPP MEDIA TEST")
    logger.debug("="*50)
    logger.debug("To test WhatsApp media, call debug_whatsapp_media_download(media_url)")
    
    # Test 4: Sheet Initialization
    logger.debug("\n" + "="*50)
    logger.debug("TEST 4: GOOGLE SHEET INITIALIZATION")
    logger.debug("="*50)
    sheet_result = initialize_google_sheet()
    logger.debug(f"Google Sheet initialization result: {'PASS' if sheet_result else 'FAIL'}")
    
    logger.debug("\n" + "="*50)
    logger.debug("FULL DEBUG TEST COMPLETED")
    logger.debug("="*50)
    
    return {
        'settings': True,  # Always passes if no exception
        'google_credentials': creds_result,
        'google_sheet': sheet_result
    }