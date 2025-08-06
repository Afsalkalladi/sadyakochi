# EeOnam: OnamSadhya 2025 WhatsApp Order Bot

A comprehensive WhatsApp bot for managing OnamSadhya orders, built with Django and integrated with WhatsApp Cloud API, Google Sheets, and Google Drive.

## 🎯 Features

- **Date Selection**: Users can select delivery dates (minimum 3 days in advance)
- **Junction Selection**: Choose from delivery locations (Vyttila, Kakkanad, Edappally, Palarivattom) or pickup
- **Menu Ordering**: Interactive menu with quantities (Veg/Non-Veg Sadhya, Payasams, etc.)
- **Location Sharing**: Support for WhatsApp location sharing or text address
- **Dynamic UPI QR**: Generates QR codes with pre-filled order details
- **Payment Verification**: Link-based verification system for admin
- **Google Integration**: Auto-sync with Google Sheets and Drive storage
- **Order Management**: Complete order tracking and status updates

## 🛠️ Tech Stack

- **Backend**: Django 4.2.7
- **Bot API**: WhatsApp Cloud API
- **Data Storage**: Google Sheets (gspread)
- **File Storage**: Google Drive
- **Payments**: UPI QR codes
- **Database**: SQLite (default) / PostgreSQL (production)

## 🚀 Quick Setup

### 1. Clone and Install

```bash
cd /path/to/your/project
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Update `.env` with your credentials:

```env
# WhatsApp Cloud API
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_id
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Google API
GOOGLE_CREDENTIALS_JSON=./service-account.json
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# UPI Details
UPI_ID=yourname@bank
UPI_MERCHANT_NAME=EeOnam

# Production
BASE_URL=https://yourdomain.com
```

### 3. Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API and Google Drive API
4. Create a Service Account and download JSON credentials
5. Place the JSON file in your project root as `service-account.json`
6. Share your Google Sheet and Drive folder with the service account email

### 4. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py initialize_bot  # Initialize menu items and Google Sheet
python manage.py createsuperuser  # Optional: for admin access
```

### 5. Run Development Server

```bash
python manage.py runserver
```

## 📱 WhatsApp Setup

### 1. Meta Developer Account
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create an app and add WhatsApp product
3. Get your Access Token and Phone Number ID

### 2. Webhook Configuration
- **Webhook URL**: `https://yourdomain.com/webhook/`
- **Verify Token**: Set in your `.env` file
- **Webhook Fields**: `messages`

## 📊 Google Sheets Structure

The bot automatically creates a sheet with these columns:

| Timestamp | Phone | Junction | Delivery Date | Order ID | Items | Total | Delivery Address | Maps Link | Drive Link | Verification Link | Rejection Link | Verified Status |

## 🔄 Order Flow

1. **Start**: User messages the bot
2. **Date Selection**: Choose delivery date (3+ days ahead)
3. **Junction Selection**: Pick delivery location or pickup
4. **Menu Selection**: Select items and quantities (format: "1 x 2, 3 x 1")
5. **Address**: Share location or type address (delivery only)
6. **Payment QR**: Bot generates UPI QR with order details
7. **Screenshot**: User sends payment screenshot
8. **Verification**: Admin clicks verify/reject link in Google Sheet
9. **Confirmation**: Customer receives final status via WhatsApp

## 🛡️ Security Features

- UUID-based verification tokens
- One-time use verification links
- Environment-based secret management
- CSRF protection disabled only for webhook endpoint

## 🚀 Deployment

### Environment Variables for Production

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
BASE_URL=https://yourdomain.com
SECRET_KEY=your_production_secret_key
```

### Recommended Platforms
- **Render**: Easy deployment with free tier
- **Railway**: Simple setup with PostgreSQL
- **DigitalOcean**: App Platform or Droplets
- **Heroku**: Classic choice with add-ons

## 📋 Menu Items

| Item | Price |
|------|-------|
| Veg Sadhya | ₹150 |
| Non-Veg Sadhya | ₹200 |
| Palada Pradhaman | ₹40 |
| Parippu/Gothambu Payasam | ₹40 |
| Kaaya Varuthathu | ₹30 |
| Sharkkaravaratti | ₹30 |

*Delivery fee: ₹50 for all delivery locations*

## 🔧 Management Commands

```bash
# Initialize bot with menu items and Google Sheet
python manage.py initialize_bot

# Check order status
python manage.py shell
>>> from bot.models import Order
>>> Order.objects.all()
```

## 📍 API Endpoints

- **Webhook**: `POST /webhook/` - WhatsApp message handling
- **Verify**: `GET /verify/<token>/` - Payment verification
- **Reject**: `GET /reject/<token>/` - Payment rejection
- **Health**: `GET /health/` - Health check
- **Order Status**: `GET /order/<order_id>/` - Check order status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For support and questions:
- Check the Django admin interface at `/admin/`
- Review logs for debugging
- Ensure all environment variables are set correctly

## 📄 License

This project is created for EeOnam - OnamSadhya 2025. All rights reserved.

---

**Happy Onam! 🎉**
