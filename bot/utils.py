
import gspread
from datetime import datetime
import json
import os
import logging

import traceback

logger = logging.getLogger(__name__)
from django.conf import settings

def get_google_sheets_client():
    """Initialize and return Google Sheets client using OAuth token from env"""
    try:
        token_json_str = getattr(settings, 'GOOGLE_OAUTH_TOKEN_JSON', None) or os.getenv('GOOGLE_OAUTH_TOKEN_JSON')
        if not token_json_str:
            raise Exception("GOOGLE_OAUTH_TOKEN_JSON not set in environment or settings.")
        token_data = json.loads(token_json_str)
        creds = gspread.auth.service_account.Credentials.from_authorized_user_info(token_data)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Error initializing Google Sheets client: {str(e)}")
        return None


def get_or_create_worksheet():
    """Get the first worksheet in the Google Sheet (no worksheet name env needed)"""
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        spreadsheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
        worksheet = spreadsheet.get_worksheet(0)  # Use the first worksheet
        return worksheet
    except Exception as e:
        logger.error(f"Error getting worksheet: {str(e)}")
        return None

def get_or_create_worksheet():
    """Get or create the orders worksheet"""
    try:
        client = get_google_sheets_client()
        if not client:
            return None
            
        # Open the spreadsheet
        spreadsheet = client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
        
        try:
            # Try to get existing worksheet
            worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEETS_WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            # Create new worksheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(
                title=settings.GOOGLE_SHEETS_WORKSHEET_NAME,
                rows="1000",
                cols="20"
            )
            
            # Add headers
            headers = [
                'Order ID', 'Customer Name', 'Phone Number', 'Email',
                'Delivery Date', 'Delivery Time Slot', 'Address',
                'Meal Type', 'Quantity', 'Special Requests',
                'Amount', 'Payment Status', 'Verification Status',
                'QR Code URL', 'Payment Screenshot URL',
                'Order Date', 'Created At', 'Updated At',
                'Notes', 'Status'
            ]
            worksheet.append_row(headers)
            
            # Format headers
            worksheet.format('A1:T1', {
                'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.3},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
        
        return worksheet
        
    except Exception as e:
        logger.error(f"Error getting/creating worksheet: {str(e)}")
        return None

def save_to_google_sheet(order) -> bool:
    """
    Save order to Google Sheet
    """
    try:
        worksheet = get_or_create_worksheet()
        if not worksheet:
            logger.error("Could not get worksheet")
            return False
        
        # Prepare order data
        order_data = [
            order.order_id,
            order.customer_name,
            order.phone_number,
            getattr(order, 'email', ''),
            str(order.delivery_date) if order.delivery_date else '',
            order.delivery_time_slot,
            order.address,
            order.meal_type,
            str(order.quantity),
            order.special_requests or '',
            f"₹{order.amount:.2f}",
            order.payment_status,
            order.verification_status,
            order.qr_code_url or '',
            order.payment_screenshot_url or '',
            str(order.delivery_date) if order.delivery_date else '',
            order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else '',
            order.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(order, 'updated_at') and order.updated_at else '',
            '',  # Notes - can be filled manually
            'Active'  # Status
        ]
        
        # Find if order already exists
        try:
            cell = worksheet.find(order.order_id)
            # Update existing row
            row_number = cell.row
            worksheet.update(f'A{row_number}:T{row_number}', [order_data])
            logger.info(f"Updated existing order {order.order_id} in Google Sheet at row {row_number}")
        except gspread.CellNotFound:
            # Add new row
            worksheet.append_row(order_data)
            logger.info(f"Added new order {order.order_id} to Google Sheet")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving to Google Sheet: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def update_sheet_verification_status(order, status: str) -> bool:
    """
    Update verification status in Google Sheet
    """
    try:
        worksheet = get_or_create_worksheet()
        if not worksheet:
            return False
        
        # Find the order row
        try:
            cell = worksheet.find(order.order_id)
            row_number = cell.row
            
            # Update verification status (column M) and updated_at (column R)
            updates = [
                {
                    'range': f'M{row_number}',  # Verification Status column
                    'values': [[status]]
                },
                {
                    'range': f'R{row_number}',  # Updated At column
                    'values': [[datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
                }
            ]
            
            # If payment screenshot URL is available, update that too
            if hasattr(order, 'payment_screenshot_url') and order.payment_screenshot_url:
                updates.append({
                    'range': f'O{row_number}',  # Payment Screenshot URL column
                    'values': [[order.payment_screenshot_url]]
                })
            
            # Batch update
            worksheet.batch_update(updates)
            
            logger.info(f"Updated verification status for order {order.order_id} to {status}")
            return True
            
        except gspread.CellNotFound:
            logger.error(f"Order {order.order_id} not found in Google Sheet")
            return False
        
    except Exception as e:
        logger.error(f"Error updating verification status in Google Sheet: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def update_payment_status_in_sheet(order, payment_status: str, payment_screenshot_url: str = None) -> bool:
    """
    Update payment status and screenshot URL in Google Sheet
    """
    try:
        worksheet = get_or_create_worksheet()
        if not worksheet:
            return False
        
        # Find the order row
        try:
            cell = worksheet.find(order.order_id)
            row_number = cell.row
            
            # Prepare updates
            updates = [
                {
                    'range': f'L{row_number}',  # Payment Status column
                    'values': [[payment_status]]
                },
                {
                    'range': f'R{row_number}',  # Updated At column
                    'values': [[datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
                }
            ]
            
            # Add payment screenshot URL if provided
            if payment_screenshot_url:
                updates.append({
                    'range': f'O{row_number}',  # Payment Screenshot URL column
                    'values': [[payment_screenshot_url]]
                })
            
            # Batch update
            worksheet.batch_update(updates)
            
            logger.info(f"Updated payment status for order {order.order_id} to {payment_status}")
            return True
            
        except gspread.CellNotFound:
            logger.error(f"Order {order.order_id} not found in Google Sheet")
            return False
        
    except Exception as e:
        logger.error(f"Error updating payment status in Google Sheet: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def get_orders_from_sheet(date_filter=None) -> list:
    """
    Retrieve orders from Google Sheet with optional date filter
    """
    try:
        worksheet = get_or_create_worksheet()
        if not worksheet:
            return []
        
        # Get all records
        records = worksheet.get_all_records()
        
        if date_filter:
            # Filter by delivery date
            filtered_records = []
            for record in records:
                if record.get('Delivery Date') == str(date_filter):
                    filtered_records.append(record)
            return filtered_records
        
        return records
        
    except Exception as e:
        logger.error(f"Error retrieving orders from Google Sheet: {str(e)}")
        return []

def add_notes_to_order(order_id: str, notes: str) -> bool:
    """
    Add notes to an order in Google Sheet
    """
    try:
        worksheet = get_or_create_worksheet()
        if not worksheet:
            return False
        
        # Find the order row
        try:
            cell = worksheet.find(order_id)
            row_number = cell.row
            
            # Update notes column (column S) and updated_at
            updates = [
                {
                    'range': f'S{row_number}',  # Notes column
                    'values': [[notes]]
                },
                {
                    'range': f'R{row_number}',  # Updated At column
                    'values': [[datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
                }
            ]
            
            worksheet.batch_update(updates)
            logger.info(f"Added notes to order {order_id}")
            return True
            
        except gspread.CellNotFound:
            logger.error(f"Order {order_id} not found in Google Sheet")
            return False
        
    except Exception as e:
        logger.error(f"Error adding notes to Google Sheet: {str(e)}")
        return False

# Additional utility functions

def get_daily_orders_summary(date) -> dict:
    """
    Get summary of orders for a specific date
    """
    try:
        orders = get_orders_from_sheet(date_filter=date)
        
        summary = {
            'total_orders': len(orders),
            'confirmed_orders': 0,
            'pending_verification': 0,
            'total_amount': 0,
            'meal_types': {}
        }
        
        for order in orders:
            # Count confirmed orders
            if order.get('Verification Status') == 'verified':
                summary['confirmed_orders'] += 1
            elif order.get('Verification Status') == 'pending':
                summary['pending_verification'] += 1
            
            # Sum total amount
            amount_str = order.get('Amount', '₹0').replace('₹', '')
            try:
                amount = float(amount_str)
                summary['total_amount'] += amount
            except:
                pass
            
            # Count meal types
            meal_type = order.get('Meal Type', 'Unknown')
            summary['meal_types'][meal_type] = summary['meal_types'].get(meal_type, 0) + 1
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}")
        return {}

def backup_sheet_data() -> bool:
    """
    Create a backup of the sheet data as JSON
    """
    try:
        worksheet = get_or_create_worksheet()
        if not worksheet:
            return False
        
        # Get all data
        all_data = worksheet.get_all_records()
        
        # Create backup filename with timestamp
        backup_filename = f"orders_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = f"/tmp/{backup_filename}"  # Adjust path as needed
        
        # Save to JSON file
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Sheet data backed up to {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return False