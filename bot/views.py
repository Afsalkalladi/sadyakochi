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
                    
                    # Upload to Cloudinary (changed from Google Drive)
                    logger.debug("☁️ Uploading to Cloudinary...")
                    from .utils import upload_to_cloudinary
                    
                    cloudinary_url = upload_to_cloudinary(media_url, order.order_id)
                    
                    if cloudinary_url:
                        logger.debug(f"✅ Image uploaded to Cloudinary: {cloudinary_url}")
                        
                        # Update order
                        order.payment_screenshot_url = cloudinary_url
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
                        logger.error("❌ Failed to upload image to Cloudinary")
                else:
                    logger.error("❌ Failed to get media URL from WhatsApp")
            else:
                logger.warning(f"⚠️ No orders awaiting payment for user {msg_from}")
                
        except Exception as e:
            logger.error(f"❌ Error processing image upload: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")


# Additional debug function to test your full system
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
        # Test 1: Check imports
        logger.debug("\n🔧 Testing imports...")
        from .utils import (
            generate_qr_code, 
            upload_to_cloudinary, 
            generate_order_id,
            get_available_dates,
            save_to_google_sheet
        )
        logger.debug("✅ All utils imported successfully")
        
        # Test 2: Test QR code generation
        logger.debug("\n🔧 Testing QR code generation...")
        test_order_id = generate_order_id()
        qr_url = generate_qr_code(150.0, test_order_id)
        
        if qr_url:
            logger.debug(f"✅ QR code generated: {qr_url}")
        else:
            logger.error("❌ QR code generation failed")
        
        # Test 3: Test order ID generation
        logger.debug("\n🔧 Testing order ID generation...")
        for i in range(3):
            order_id = generate_order_id()
            logger.debug(f"Generated order ID {i+1}: {order_id}")
        
        # Test 4: Test available dates
        logger.debug("\n🔧 Testing available dates...")
        dates = get_available_dates()
        logger.debug(f"Available dates count: {len(dates)}")
        logger.debug(f"First 3 dates: {[d.strftime('%Y-%m-%d') for d in dates[:3]]}")
        
        # Test 5: Check database
        logger.debug("\n🗄️ Testing database...")
        from .models import Order, UserSession
        
        recent_orders = Order.objects.all()[:5]
        logger.debug(f"Recent orders count: {len(recent_orders)}")
        
        for order in recent_orders:
            logger.debug(f"Order {order.order_id}: {order.status}")
        
        # Test 6: Check Cloudinary configuration
        logger.debug("\n☁️ Testing Cloudinary configuration...")
        from .utils import configure_cloudinary
        from django.conf import settings
        
        required_settings = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
        cloudinary_configured = True
        
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                logger.error(f"❌ Missing or empty setting: {setting}")
                cloudinary_configured = False
            else:
                logger.debug(f"✅ {setting} is configured")
        
        if cloudinary_configured:
            logger.debug("✅ Cloudinary configuration appears complete")
            configure_cloudinary()
            logger.debug("✅ Cloudinary configured successfully")
        else:
            logger.error("❌ Cloudinary configuration incomplete")
        
        # Test 7: Check WhatsApp configuration
        logger.debug("\n📱 Testing WhatsApp configuration...")
        whatsapp_settings = ['WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_VERIFY_TOKEN']
        whatsapp_configured = True
        
        for setting in whatsapp_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                logger.error(f"❌ Missing or empty setting: {setting}")
                whatsapp_configured = False
            else:
                # Don't log the actual token, just confirm it exists
                logger.debug(f"✅ {setting} is configured")
        
        if whatsapp_configured:
            logger.debug("✅ WhatsApp configuration appears complete")
        else:
            logger.error("❌ WhatsApp configuration incomplete")
        
        # Test 8: Check UPI configuration
        logger.debug("\n💳 Testing UPI configuration...")
        upi_settings = ['UPI_ID', 'UPI_MERCHANT_NAME']
        upi_configured = True
        
        for setting in upi_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                logger.error(f"❌ Missing or empty setting: {setting}")
                upi_configured = False
            else:
                logger.debug(f"✅ {setting} is configured")
        
        if upi_configured:
            logger.debug("✅ UPI configuration appears complete")
        else:
            logger.error("❌ UPI configuration incomplete")
        
        logger.debug("✅ FULL SYSTEM DEBUG TEST COMPLETED")
        
        # Summary
        logger.debug("\n📋 SUMMARY:")
        logger.debug("="*40)
        logger.debug(f"✅ Imports: Working")
        logger.debug(f"✅ QR Generation: {'Working' if qr_url else 'Failed'}")
        logger.debug(f"✅ Order IDs: Working")
        logger.debug(f"✅ Database: Working")
        logger.debug(f"✅ Cloudinary: {'Configured' if cloudinary_configured else 'Not Configured'}")
        logger.debug(f"✅ WhatsApp: {'Configured' if whatsapp_configured else 'Not Configured'}")
        logger.debug(f"✅ UPI: {'Configured' if upi_configured else 'Not Configured'}")
        
        return {
            'imports': True,
            'qr_generation': bool(qr_url),
            'order_ids': True,
            'database': True,
            'cloudinary': cloudinary_configured,
            'whatsapp': whatsapp_configured,
            'upi': upi_configured
        }
        
    except Exception as e:
        logger.error(f"❌ SYSTEM DEBUG TEST FAILED: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {'error': str(e)}