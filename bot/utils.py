import io
import os
import json
import qrcode
import traceback
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import cloudinary
import cloudinary.uploader
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.conf import settings
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# =========================
# Cloudinary / QR Functions
# =========================

def generate_qr_code(amount: float, order_id: str) -> Optional[str]:
    """
    Generate a branded QR code with Sadya Kochi branding and graphics.
    Ensures the final image is at least 10KB in size.
    """
    try:
        upi_string = (
            f"upi://pay?"
            f"pa={settings.UPI_ID}&"
            f"pn={settings.UPI_MERCHANT_NAME}&"
            f"am={amount}&"
            f"cu=INR&"
            f"tn=Order_{order_id}"
        )
        
        # Create QR code with higher settings for better quality
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=15,
            border=6,
        )
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        # Generate base QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Create a larger canvas with branding
        canvas_width = 800
        canvas_height = 1000
        
        # Create new image with white background
        canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
        draw = ImageDraw.Draw(canvas)
        
        # Decorative borders
        border_color = "#2E8B57"
        border_width = 8
        draw.rectangle([0, 0, canvas_width, canvas_height], outline=border_color, width=border_width)
        inner_border_margin = 20
        draw.rectangle([
            inner_border_margin, inner_border_margin, 
            canvas_width - inner_border_margin, canvas_height - inner_border_margin
        ], outline="#FFD700", width=4)
        
        # Brand header
        header_height = 120
        draw.rectangle([
            border_width, border_width, 
            canvas_width - border_width, header_height + border_width
        ], fill="#2E8B57")
        
        # Fonts (fallback-safe)
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 48)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 24)
            detail_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 20)
        except Exception:
            try:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                detail_font = ImageFont.load_default()
            except Exception:
                title_font = subtitle_font = detail_font = None
        
        # Brand text
        brand_text = "SADYA KOCHI"
        if title_font:
            bbox = draw.textbbox((0, 0), brand_text, font=title_font)
            text_width = bbox[2] - bbox[0]
            draw.text(((canvas_width - text_width) // 2, 25), brand_text, fill="white", font=title_font)
        
        tagline = "Authentic Kerala Meals Delivered"
        if subtitle_font:
            bbox = draw.textbbox((0, 0), tagline, font=subtitle_font)
            text_width = bbox[2] - bbox[0]
            draw.text(((canvas_width - text_width) // 2, 80), tagline, fill="#FFD700", font=subtitle_font)
        
        # QR placement
        qr_size = 450
        qr_img_resized = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = (canvas_width - qr_size) // 2
        qr_y = header_height + 50
        
        # Shadow + frame
        shadow_offset = 5
        draw.rectangle([
            qr_x + shadow_offset, qr_y + shadow_offset,
            qr_x + qr_size + shadow_offset, qr_y + qr_size + shadow_offset
        ], fill="#CCCCCC")
        draw.rectangle([qr_x - 10, qr_y - 10, qr_x + qr_size + 10, qr_y + qr_size + 10], 
                      fill="white", outline="#DDDDDD", width=2)
        canvas.paste(qr_img_resized, (qr_x, qr_y))
        
        # Details
        details_y = qr_y + qr_size + 40
        if detail_font:
            amount_text = f"Amount: ₹{amount:.2f}"
            bbox = draw.textbbox((0, 0), amount_text, font=detail_font)
            draw.text(((canvas_width - (bbox[2]-bbox[0])) // 2, details_y), amount_text, fill="#2E8B57", font=detail_font)
            
            order_text = f"Order ID: {order_id}"
            bbox = draw.textbbox((0, 0), order_text, font=detail_font)
            draw.text(((canvas_width - (bbox[2]-bbox[0])) // 2, details_y + 35), order_text, fill="#666666", font=detail_font)
            
            instruction_text = "Scan to pay with any UPI app"
            bbox = draw.textbbox((0, 0), instruction_text, font=detail_font)
            draw.text(((canvas_width - (bbox[2]-bbox[0])) // 2, details_y + 70), instruction_text, fill="#666666", font=detail_font)
        
        # Decorative arcs
        for i in range(3):
            draw.arc([30 + i*10, 140 + i*10, 70 + i*10, 180 + i*10], start=0, end=90, fill="#FFD700", width=3)
            draw.arc([canvas_width - 70 - i*10, 140 + i*10, canvas_width - 30 - i*10, 180 + i*10], start=90, end=180, fill="#FFD700", width=3)
        
        # Encode
        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format='PNG', quality=95, optimize=False)
        img_buffer.seek(0)
        
        if len(img_buffer.getvalue()) < 10240:
            # Bump size if under 10KB
            canvas_large = canvas.resize((1000, 1200), Image.Resampling.LANCZOS)
            img_buffer = io.BytesIO()
            canvas_large.save(img_buffer, format='PNG', quality=100, optimize=False)
            img_buffer.seek(0)

        # Upload to Cloudinary
        configure_cloudinary()
        result = cloudinary.uploader.upload(
            img_buffer,
            folder="qr_codes",
            public_id=f"qr_{order_id}",
            overwrite=True,
            resource_type="image",
            format="png",
            quality="auto:best"
        )
        return result.get('secure_url')
        
    except Exception as e:
        logger.error(f"Error generating branded QR code: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def configure_cloudinary():
    """Configure Cloudinary with settings from Django settings."""
    cloudinary.config(
        cloud_name=getattr(settings, 'CLOUDINARY_CLOUD_NAME', None),
        api_key=getattr(settings, 'CLOUDINARY_API_KEY', None),
        api_secret=getattr(settings, 'CLOUDINARY_API_SECRET', None)
    )


def upload_to_cloudinary(media_url: str, order_id: str) -> Optional[str]:
    """
    Upload payment screenshot to Cloudinary.
    """
    try:
        import requests
        headers = { 'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}' }
        resp = requests.get(media_url, headers=headers, timeout=30)
        resp.raise_for_status()

        configure_cloudinary()
        result = cloudinary.uploader.upload(
            resp.content,
            folder="payment_screenshots",
            public_id=f"payment_{order_id}",
            overwrite=True,
            resource_type="image"
        )
        return result.get('secure_url')
    except Exception as e:
        logger.error(f"Error uploading to Cloudinary: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def generate_order_id() -> str:
    """Generate unique order ID (EO-YYYYMMDD-XXXX)."""
    import uuid
    date_str = datetime.now().strftime('%Y%m%d')
    uuid_suffix = str(uuid.uuid4()).replace('-', '')[-4:].upper()
    return f"EO-{date_str}-{uuid_suffix}"


def get_available_dates():
    """Get list of available delivery dates (minimum 3 days advance, next 30 days)."""
    start_date = datetime.now().date() + timedelta(days=3)
    return [start_date + timedelta(days=i) for i in range(30)]


# =========================
# Google Sheets (Restored)
# =========================

def get_google_credentials():
    """Load credentials from environment variable (GOOGLE_OAUTH_TOKEN_JSON) or token.json."""
    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    creds = None
    token_json_str = os.getenv('GOOGLE_OAUTH_TOKEN_JSON')

    if token_json_str:
        try:
            logger.debug("Loading Google credentials from environment variable")
            token_data = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            logger.debug("Successfully loaded credentials from environment variable")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing GOOGLE_OAUTH_TOKEN_JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating credentials from environment variable: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    else:
        token_path = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.json')
        if os.path.exists(token_path):
            try:
                logger.debug(f"Loading Google credentials from file: {token_path}")
                with open(token_path, 'r') as token_file:
                    token_data = json.load(token_file)
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                logger.debug("Successfully loaded credentials from file")
            except Exception as e:
                logger.error(f"Error loading credentials from file: {str(e)}")
                logger.error(traceback.format_exc())
                return None
        else:
            logger.error(f"Neither GOOGLE_OAUTH_TOKEN_JSON env var nor token file found at: {token_path}")
            return None

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.debug("Refreshing expired Google credentials")
            creds.refresh(Request())
            refreshed_token_json = creds.to_json()
            if token_json_str:
                logger.info("Token refreshed. Update GOOGLE_OAUTH_TOKEN_JSON env var with the new token JSON.")
                logger.debug(refreshed_token_json)
            else:
                with open(os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.json'), 'w') as token_file:
                    token_file.write(refreshed_token_json)
                logger.debug("Updated local token.json with refreshed token")
        except Exception as e:
            logger.error(f"Error refreshing Google credentials: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    if not creds or not creds.valid:
        logger.error("Invalid or missing Google credentials.")
        return None

    logger.debug("Google credentials are valid and ready to use")
    return creds


def parse_items_for_display(items_dict: dict) -> str:
    names = {
        1: 'Veg Sadhya',
        2: 'Non-Veg Sadhya',
        3: 'Palada Pradhaman',
        4: 'Parippu/Gothambu Payasam',
        5: 'Kaaya Varuthathu',
        6: 'Sharkkaravaratti'
    }
    # Accept both {"1": 2} and {1: 2}
    if items_dict and isinstance(list(items_dict.keys())[0], str):
        items_dict = {int(k): v for k, v in items_dict.items()}
    return ', '.join(f"{names[i]} x {q}" for i, q in items_dict.items() if i in names)


def save_to_google_sheet(order) -> bool:
    """
    Append order details to Google Sheet and store the row number in the DB.
    (Restored behavior)
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return False

        gc = gspread.authorize(creds)
        sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None)
        if not sheet_id:
            logger.error("GOOGLE_SHEET_ID not set")
            return False

        workbook = gc.open_by_key(sheet_id)
        sheet = workbook.sheet1

        # Items -> readable string
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
            order.payment_screenshot_url or '',  # Cloudinary URL
            order.get_verification_url(),
            order.get_rejection_url(),
            order.status.title()
        ]

        sheet.append_row(row_data)

        # Capture row number for future updates
        all_values = sheet.get_all_values()
        order.sheet_row_number = len(all_values)
        order.save(update_fields=['sheet_row_number'])

        logger.debug(f"Order {order.order_id} saved to Google Sheet (row {order.sheet_row_number})")
        return True

    except Exception:
        logger.error(traceback.format_exc())
        return False


def update_sheet_verification_status(order, status: str) -> bool:
    """
    Update the 'Verified Status' column (col 13) in Google Sheet for the order row.
    (Restored behavior)
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return False

        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1

        if order.sheet_row_number:
            sheet.update_cell(order.sheet_row_number, 13, status.title())
            logger.debug(f"Updated Google Sheet row {order.sheet_row_number} to {status.title()}")
            return True

        logger.warning(f"Order {order.order_id} has no stored sheet_row_number")
        return False

    except Exception:
        logger.error(traceback.format_exc())
        return False


def initialize_google_sheet() -> bool:
    """
    Ensure Google Sheet has the expected headers (if first row is empty).
    (Restored behavior)
    """
    try:
        creds = get_google_credentials()
        if not creds:
            return False

        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(settings.GOOGLE_SHEET_ID).sheet1

        if not sheet.row_values(1):
            headers = [
                'Timestamp', 'Phone', 'Junction', 'Delivery Date', 'Order ID',
                'Items', 'Total', 'Delivery Address', 'Maps Link', 'Cloudinary Link',
                'Verification Link', 'Rejection Link', 'Verified Status'
            ]
            sheet.append_row(headers)

        return True

    except Exception:
        logger.error(traceback.format_exc())
        return False
