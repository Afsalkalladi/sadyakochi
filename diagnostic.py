"""
EeOnam Bot Diagnostic Script
Run this to check your entire setup

Usage:
python manage.py shell
>>> exec(open('diagnostic.py').read())
"""

import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def run_diagnostics():
    """Run comprehensive diagnostics"""
    
    print("🚀 EONAM BOT DIAGNOSTICS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    results = {
        'settings': False,
        'database': False,
        'google_auth': False,
        'google_drive': False,
        'google_sheets': False,
        'whatsapp_token': False
    }
    
    # Test 1: Django Settings
    print("\n🔧 1. CHECKING DJANGO SETTINGS")
    print("-" * 40)
    
    try:
        from django.conf import settings
        
        required_settings = [
            'UPI_ID',
            'UPI_MERCHANT_NAME', 
            'GOOGLE_DRIVE_FOLDER_ID',
            'GOOGLE_SHEET_ID',
            'WHATSAPP_ACCESS_TOKEN'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)
                if value:
                    print(f"✅ {setting}: {'*' * 10}...{str(value)[-4:]}")
                else:
                    print(f"❌ {setting}: Empty")
                    missing_settings.append(setting)
            else:
                print(f"❌ {setting}: Not found")
                missing_settings.append(setting)
        
        if missing_settings:
            print(f"\n⚠️ Missing settings: {', '.join(missing_settings)}")
        else:
            print("\n✅ All required settings present")
            results['settings'] = True
            
    except Exception as e:
        print(f"❌ Settings error: {str(e)}")
    
    # Test 2: Database Connection
    print("\n🗄️ 2. CHECKING DATABASE")
    print("-" * 40)
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        print("✅ Database connection successful")
        
        # Check Order model
        try:
            from bot.models import Order
            order_count = Order.objects.count()
            print(f"✅ Order model accessible, {order_count} orders in database")
            
            # Show recent orders
            recent_orders = Order.objects.all()[:3]
            for order in recent_orders:
                print(f"   - {order.order_id}: {order.status} (₹{order.total_amount})")
            
            results['database'] = True
            
        except Exception as e:
            print(f"❌ Order model error: {str(e)}")
            
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
    
    # Test 3: Google Authentication
    print("\n🔐 3. CHECKING GOOGLE AUTHENTICATION")
    print("-" * 40)
    
    try:
        from bot.utils import get_google_credentials
        
        creds = get_google_credentials()
        if creds:
            print("✅ Google credentials loaded")
            print(f"   - Valid: {creds.valid}")
            print(f"   - Expired: {creds.expired if hasattr(creds, 'expired') else 'Unknown'}")
            results['google_auth'] = True
        else:
            print("❌ Failed to get Google credentials")
            
    except Exception as e:
        print(f"❌ Google auth error: {str(e)}")
    
    # Test 4: Google Drive Access
    print("\n☁️ 4. CHECKING GOOGLE DRIVE ACCESS")
    print("-" * 40)
    
    if results['google_auth']:
        try:
            from googleapiclient.discovery import build
            from bot.utils import get_google_credentials
            from django.conf import settings
            
            creds = get_google_credentials()
            service = build('drive', 'v3', credentials=creds)
            
            # Test folder access
            folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
            folder_info = service.files().get(fileId=folder_id).execute()
            
            print(f"✅ Drive folder accessible: {folder_info.get('name', 'Unknown')}")
            print(f"   - Folder ID: {folder_id}")
            
            # List recent files
            files_result = service.files().list(
                q=f"'{folder_id}' in parents",
                pageSize=5,
                fields="files(id, name, createdTime)"
            ).execute()
            
            files = files_result.get('files', [])
            print(f"   - Recent files: {len(files)}")
            
            for file in files[:3]:
                print(f"     • {file.get('name')} ({file.get('createdTime')})")
            
            results['google_drive'] = True
            
        except Exception as e:
            print(f"❌ Google Drive error: {str(e)}")
    else:
        print("⏭️ Skipped (Google auth failed)")
    
    # Test 5: Google Sheets Access
    print("\n📊 5. CHECKING GOOGLE SHEETS ACCESS")
    print("-" * 40)
    
    if results['google_auth']:
        try:
            import gspread
            from bot.utils import get_google_credentials
            from django.conf import settings
            
            creds = get_google_credentials()
            gc = gspread.authorize(creds)
            
            sheet_id = settings.GOOGLE_SHEET_ID
            workbook = gc.open_by_key(sheet_id)
            worksheet = workbook.sheet1
            
            print(f"✅ Google Sheet accessible: {workbook.title}")
            print(f"   - Sheet ID: {sheet_id}")
            
            # Check headers
            headers = worksheet.row_values(1)
            print(f"   - Headers: {len(headers)} columns")
            
            # Check row count
            all_values = worksheet.get_all_values()
            print(f"   - Rows: {len(all_values)}")
            
            results['google_sheets'] = True
            
        except Exception as e:
            print(f"❌ Google Sheets error: {str(e)}")
    else:
        print("⏭️ Skipped (Google auth failed)")
    
    # Test 6: WhatsApp Token
    print("\n📱 6. CHECKING WHATSAPP TOKEN")
    print("-" * 40)
    
    try:
        import requests
        from django.conf import settings
        
        if hasattr(settings, 'WHATSAPP_ACCESS_TOKEN'):
            token = settings.WHATSAPP_ACCESS_TOKEN
            
            # Test token with WhatsApp API
            url = "https://graph.facebook.com/v17.0/me"
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ WhatsApp token valid")
                print(f"   - App ID: {data.get('id', 'Unknown')}")
                print(f"   - App Name: {data.get('name', 'Unknown')}")
                results['whatsapp_token'] = True
            else:
                print(f"❌ WhatsApp token invalid (Status: {response.status_code})")
                print(f"   - Response: {response.text}")
        else:
            print("❌ WHATSAPP_ACCESS_TOKEN not found in settings")
            
    except Exception as e:
        print(f"❌ WhatsApp token test error: {str(e)}")
    
    # Test 7: File System Permissions
    print("\n📁 7. CHECKING FILE SYSTEM")
    print("-" * 40)
    
    try:
        # Check token.pickle file
        token_path = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.pickle')
        print(f"Token path: {token_path}")
        
        if os.path.exists(token_path):
            stat_info = os.stat(token_path)
            print(f"✅ Token file exists ({stat_info.st_size} bytes)")
            print(f"   - Modified: {datetime.fromtimestamp(stat_info.st_mtime)}")
        else:
            print(f"❌ Token file not found at: {token_path}")
        
        # Check write permissions in current directory
        test_file = 'temp_test.txt'
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print("✅ Write permissions available")
        except Exception as e:
            print(f"❌ Write permission error: {str(e)}")
            
    except Exception as e:
        print(f"❌ File system error: {str(e)}")
    
    # Test 8: Environment Variables
    print("\n🌍 8. CHECKING ENVIRONMENT VARIABLES")
    print("-" * 40)
    
    env_vars = [
        'DJANGO_SETTINGS_MODULE',
        'GOOGLE_OAUTH_TOKEN_PATH',
        'DEBUG'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if len(value) > 50:
                display_value = value[:20] + "..." + value[-10:]
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"⚪ {var}: Not set")
    
    # Test 9: Test Location Processing
    print("\n📍 9. TESTING LOCATION PROCESSING")
    print("-" * 40)
    
    try:
        # Create a mock location message for testing
        mock_location_data = {
            'latitude': 10.0261,
            'longitude': 76.3125,
            'name': 'Test Location',
            'address': 'Test Address, Kochi',
            'url': 'https://maps.google.com/?q=10.0261,76.3125'
        }
        
        print("🧪 Testing location data parsing...")
        
        # Test address construction
        if mock_location_data.get('name') and mock_location_data.get('address'):
            delivery_address = f"{mock_location_data['name']}, {mock_location_data['address']}"
        else:
            delivery_address = f"Location: {mock_location_data['latitude']}, {mock_location_data['longitude']}"
        
        print(f"✅ Address construction: {delivery_address}")
        
        # Test maps link
        maps_link = mock_location_data.get('url', f"https://maps.google.com/?q={mock_location_data['latitude']},{mock_location_data['longitude']}")
        print(f"✅ Maps link: {maps_link}")
        
    except Exception as e:
        print(f"❌ Location processing test error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"Tests passed: {passed_tests}/{total_tests}")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Your setup looks good.")
        print("\nIf you're still having issues with location uploads:")
        print("1. Enable the debug webhook handler")
        print("2. Check logs when user sends location")
        print("3. Look for '📍 PROCESSING LOCATION MESSAGE' in logs")
    else:
        print(f"\n⚠️ {total_tests - passed_tests} TESTS FAILED")
        print("Please fix the failing components before testing location uploads.")
    
    print("\n" + "=" * 60)
    print("To enable detailed debugging:")
    print("1. Replace your webhook view with DebugWebhookView")
    print("2. Send a test location from WhatsApp")
    print("3. Check logs for detailed processing information")
    print("=" * 60)
    
    return results


def test_specific_location_flow():
    """Test the specific location upload flow"""
    print("\n🎯 TESTING LOCATION UPLOAD FLOW")
    print("=" * 50)
    
    try:
        from bot.models import Order
        from bot.utils import generate_qr_code, upload_to_drive, save_to_google_sheet
        
        # Find a test order or create one
        test_orders = Order.objects.filter(status__in=['pending_location', 'awaiting_payment'])[:1]
        
        if test_orders:
            order = test_orders[0]
            print(f"✅ Found test order: {order.order_id}")
            print(f"   - Status: {order.status}")
            print(f"   - Phone: {order.phone_number}")
            print(f"   - Total: ₹{order.total_amount}")
            
            # Test QR code generation
            print("\n💳 Testing QR code generation...")
            qr_url = generate_qr_code(float(order.total_amount), order.order_id)
            if qr_url:
                print(f"✅ QR code generated: {qr_url}")
            else:
                print("❌ QR code generation failed")
            
            # Test Google Sheet saving
            print("\n📊 Testing Google Sheet save...")
            sheet_result = save_to_google_sheet(order)
            if sheet_result:
                print("✅ Google Sheet save successful")
            else:
                print("❌ Google Sheet save failed")
            
        else:
            print("⚪ No test orders found in pending_location or awaiting_payment status")
            print("Create a test order first to test the location flow")
            
    except Exception as e:
        print(f"❌ Location flow test error: {str(e)}")


def create_test_order():
    """Create a test order for testing location flow"""
    print("\n🧪 CREATING TEST ORDER")
    print("=" * 30)
    
    try:
        from bot.models import Order
        from bot.utils import generate_order_id
        from datetime import date, timedelta
        
        order_id = generate_order_id()
        delivery_date = date.today() + timedelta(days=5)
        
        test_order = Order.objects.create(
            phone_number="918891281090",  # Your test number
            junction="kochi_metro",
            delivery_date=delivery_date,
            order_id=order_id,
            items='{"1": 2, "3": 1}',  # 2 Veg Sadhya, 1 Palada Pradhaman
            total_amount=450.00,
            delivery_address="",
            maps_link="",
            status="pending_location"
        )
        
        print(f"✅ Test order created: {order_id}")
        print(f"   - Status: {test_order.status}")
        print(f"   - Ready for location upload test")
        
        return test_order
        
    except Exception as e:
        print(f"❌ Test order creation error: {str(e)}")
        return None


# Main execution
if __name__ == "__main__":
    try:
        results = run_diagnostics()
        
        # Offer to run additional tests
        if sum(results.values()) >= 4:  # Most tests passed
            print("\n🔍 ADDITIONAL TESTS AVAILABLE:")
            print("1. Test specific location flow: test_specific_location_flow()")
            print("2. Create test order: create_test_order()")
            print("\nRun these in Django shell if needed.")
        
    except Exception as e:
        print(f"❌ DIAGNOSTIC FAILED: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

# Run diagnostics when script is executed
run_diagnostics()