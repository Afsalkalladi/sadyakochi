# Google Services Setup Guide for EeOnam Bot

This guide will help you set up Google Sheets and Google Drive integration for the EeOnam bot.

## 🚀 Quick Setup Steps

### 1. Google Cloud Console Setup

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create or Select Project**
   - Click on the project dropdown at the top
   - Create a new project or select an existing one
   - Name it something like "EeOnam Bot"

3. **Enable Required APIs**
   - Go to "APIs & Services" > "Library"
   - Search and enable:
     - **Google Sheets API**
     - **Google Drive API**

### 2. Service Account Creation

1. **Create Service Account**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Name: `eeonam-bot-service`
   - Description: `Service account for EeOnam WhatsApp bot`
   - Click "Create and Continue"

2. **Add Roles (Optional)**
   - You can skip role assignment for now
   - Click "Continue" then "Done"

3. **Generate Key**
   - Click on your newly created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose "JSON" format
   - Download the JSON file

4. **Place Credentials File**
   - Move the downloaded JSON file to your project root
   - Rename it to `service-account.json`
   - Update your `.env` file:
     ```env
     GOOGLE_CREDENTIALS_JSON=./service-account.json
     ```

### 3. Google Sheet Setup

1. **Create Google Sheet**
   - Go to https://sheets.google.com/
   - Create a new blank spreadsheet
   - Name it "EeOnam Orders 2025"

2. **Get Sheet ID**
   - From the URL: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit`
   - Copy the `SHEET_ID` part
   - Add to your `.env` file:
     ```env
     GOOGLE_SHEET_ID=your_copied_sheet_id_here
     ```

3. **Share with Service Account**
   - Click "Share" button in your Google Sheet
   - Add the service account email as an editor
   - Service account email format: `eeonam-bot-service@project-name.iam.gserviceaccount.com`
   - You can find this email in your service account JSON file

### 4. Google Drive Setup

1. **Create Drive Folder**
   - Go to https://drive.google.com/
   - Create a new folder named "EeOnam Bot Files"
   - This will store QR codes and payment screenshots

2. **Get Folder ID**
   - Open the folder you created
   - From the URL: `https://drive.google.com/drive/folders/FOLDER_ID`
   - Copy the `FOLDER_ID` part
   - Add to your `.env` file:
     ```env
     GOOGLE_DRIVE_FOLDER_ID=your_copied_folder_id_here
     ```

3. **Share with Service Account**
   - Right-click the folder > "Share"
   - Add the same service account email as an editor

### 5. Test Configuration

Run the bot initialization to test Google integration:

```bash
source venv/bin/activate
python manage.py initialize_bot
```

If successful, you should see:
```
📊 Google Sheet initialized successfully
```

## 🔧 Troubleshooting

### Common Issues

**1. "Google credentials file not found"**
- Ensure the JSON file is in the correct location
- Check the file path in your `.env` file
- Verify file permissions

**2. "Permission denied" errors**
- Make sure you shared both Sheet and Drive folder with service account
- Check that the service account email is correct
- Verify the service account has "Editor" permissions

**3. "API not enabled" errors**
- Go back to Google Cloud Console
- Enable Google Sheets API and Google Drive API
- Wait a few minutes for activation

### File Structure Check

Your project should look like this:
```
eeonam/
├── service-account.json          # Google credentials
├── .env                         # Environment variables
├── manage.py
├── requirements.txt
└── ...
```

### Environment Variables Check

Your `.env` should contain:
```env
GOOGLE_CREDENTIALS_JSON=./service-account.json
GOOGLE_SHEET_ID=1ABC...XYZ
GOOGLE_DRIVE_FOLDER_ID=1DEF...UVW
```

## 📊 Google Sheet Structure

The bot will automatically create these columns:

| Column | Description |
|--------|-------------|
| Timestamp | Order creation time |
| Phone | Customer phone number |
| Junction | Delivery/pickup location |
| Delivery Date | Selected delivery date |
| Order ID | Unique order identifier |
| Items | Ordered items with quantities |
| Total | Total amount including delivery |
| Delivery Address | Customer address |
| Maps Link | Google Maps link (if location shared) |
| Drive Link | Payment screenshot link |
| Verification Link | Admin verification link |
| Rejection Link | Admin rejection link |
| Verified Status | Current verification status |

## 🔗 Admin Workflow

1. **Receive Order**: New row appears in Google Sheet
2. **Check Screenshot**: Click "Drive Link" to view payment proof
3. **Verify Payment**: Click "Verification Link" to approve
4. **OR Reject**: Click "Rejection Link" to deny
5. **Customer Notified**: WhatsApp message sent automatically

## 🔒 Security Notes

- Keep your service account JSON file secure
- Don't commit it to version control
- Limit service account permissions to only what's needed
- Regularly review shared access to your Google resources

## 🆘 Need Help?

If you encounter issues:
1. Check the Django logs for error messages
2. Verify all environment variables are set correctly
3. Test Google API access with the `python test_setup.py` script
4. Ensure your Google Cloud project has billing enabled (if required)

---

**Once everything is configured, your bot will seamlessly integrate with Google services! 🎉**
