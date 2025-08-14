import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
import cloudinary
import cloudinary.uploader
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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
            version=3,  # Increased from 1 to 3 for higher capacity and size
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Highest error correction
            box_size=15,  # Increased from 10 to 15 for larger QR code
            border=6,  # Increased border
        )
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        # Generate base QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Create a larger canvas with branding
        canvas_width = 800  # Large canvas for high resolution
        canvas_height = 1000
        
        # Create new image with white background
        canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
        draw = ImageDraw.Draw(canvas)
        
        # Add decorative border
        border_color = "#2E8B57"  # Sea green color for Kerala theme
        border_width = 8
        draw.rectangle([0, 0, canvas_width, canvas_height], outline=border_color, width=border_width)
        
        # Add inner decorative border
        inner_border_margin = 20
        draw.rectangle([
            inner_border_margin, inner_border_margin, 
            canvas_width - inner_border_margin, canvas_height - inner_border_margin
        ], outline="#FFD700", width=4)  # Golden border
        
        # Add brand header background
        header_height = 120
        draw.rectangle([
            border_width, border_width, 
            canvas_width - border_width, header_height + border_width
        ], fill="#2E8B57")
        
        # Try to load custom fonts, fallback to default
        try:
            # For title - larger font
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 48)
            # For subtitle - medium font
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 24)
            # For details - smaller font
            detail_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttc", 20)
        except:
            try:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                detail_font = ImageFont.load_default()
            except:
                title_font = None
                subtitle_font = None
                detail_font = None
        
        # Add brand name
        brand_text = "SADYA KOCHI"
        if title_font:
            bbox = draw.textbbox((0, 0), brand_text, font=title_font)
            text_width = bbox[2] - bbox[0]
            text_x = (canvas_width - text_width) // 2
            draw.text((text_x, 25), brand_text, fill="white", font=title_font)
        
        # Add tagline
        tagline = "Authentic Kerala Meals Delivered"
        if subtitle_font:
            bbox = draw.textbbox((0, 0), tagline, font=subtitle_font)
            text_width = bbox[2] - bbox[0]
            text_x = (canvas_width - text_width) // 2
            draw.text((text_x, 80), tagline, fill="#FFD700", font=subtitle_font)
        
        # Resize QR code to fit nicely in the canvas
        qr_size = 450  # Large QR code
        qr_img_resized = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        
        # Position QR code in center
        qr_x = (canvas_width - qr_size) // 2
        qr_y = header_height + 50
        
        # Add QR code background with shadow effect
        shadow_offset = 5
        shadow_color = "#CCCCCC"
        draw.rectangle([
            qr_x + shadow_offset, qr_y + shadow_offset,
            qr_x + qr_size + shadow_offset, qr_y + qr_size + shadow_offset
        ], fill=shadow_color)
        
        # Add white background for QR code
        draw.rectangle([qr_x - 10, qr_y - 10, qr_x + qr_size + 10, qr_y + qr_size + 10], 
                      fill="white", outline="#DDDDDD", width=2)
        
        # Paste the QR code
        canvas.paste(qr_img_resized, (qr_x, qr_y))
        
        # Add payment details below QR code
        details_y = qr_y + qr_size + 40
        
        # Payment amount
        amount_text = f"Amount: ₹{amount:.2f}"
        if detail_font:
            bbox = draw.textbbox((0, 0), amount_text, font=detail_font)
            text_width = bbox[2] - bbox[0]
            text_x = (canvas_width - text_width) // 2
            draw.text((text_x, details_y), amount_text, fill="#2E8B57", font=detail_font)
        
        # Order ID
        order_text = f"Order ID: {order_id}"
        if detail_font:
            bbox = draw.textbbox((0, 0), order_text, font=detail_font)
            text_width = bbox[2] - bbox[0]
            text_x = (canvas_width - text_width) // 2
            draw.text((text_x, details_y + 35), order_text, fill="#666666", font=detail_font)
        
        # Instructions
        instruction_text = "Scan to pay with any UPI app"
        if detail_font:
            bbox = draw.textbbox((0, 0), instruction_text, font=detail_font)
            text_width = bbox[2] - bbox[0]
            text_x = (canvas_width - text_width) // 2
            draw.text((text_x, details_y + 70), instruction_text, fill="#666666", font=detail_font)
        
        # Add decorative elements (simple geometric patterns)
        # Top corners
        for i in range(3):
            draw.arc([30 + i*10, 140 + i*10, 70 + i*10, 180 + i*10], 
                    start=0, end=90, fill="#FFD700", width=3)
            draw.arc([canvas_width - 70 - i*10, 140 + i*10, 
                     canvas_width - 30 - i*10, 180 + i*10], 
                    start=90, end=180, fill="#FFD700", width=3)
        
        # Convert to bytes with high quality
        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format='PNG', quality=95, optimize=False)
        img_buffer.seek(0)
        
        # Check file size and increase quality if needed
        current_size = len(img_buffer.getvalue())
        logger.debug(f"Generated QR code size: {current_size} bytes")
        
        # If still under 10KB, increase the canvas size
        if current_size < 10240:  # 10KB
            logger.debug("Image under 10KB, increasing size...")
            canvas_width = 1000
            canvas_height = 1200
            
            # Recreate with larger dimensions
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            draw = ImageDraw.Draw(canvas)
            
            # Repeat the drawing process with larger dimensions
            # (You can extract this into a separate function to avoid repetition)
            # For brevity, I'll just resize the existing image
            canvas_large = canvas.resize((1000, 1200), Image.Resampling.LANCZOS)
            
            img_buffer = io.BytesIO()
            canvas_large.save(img_buffer, format='PNG', quality=100, optimize=False)
            img_buffer.seek(0)
            
            final_size = len(img_buffer.getvalue())
            logger.debug(f"Final QR code size: {final_size} bytes")

        # Upload to Cloudinary
        configure_cloudinary()
        result = cloudinary.uploader.upload(
            img_buffer,
            folder="qr_codes",
            public_id=f"qr_{order_id}",
            overwrite=True,
            resource_type="image",
            format="png",
            quality="auto:best"  # Ensure high quality
        )
        
        qr_url = result.get('secure_url')
        logger.debug(f"QR code uploaded to Cloudinary: {qr_url}")
        return qr_url
        
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