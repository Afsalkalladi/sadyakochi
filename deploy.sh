#!/bin/bash

# EeOnam Bot Deployment Script
# This script helps deploy the bot to production

echo "🚀 EeOnam Bot Deployment Script"
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp .env.example .env
    echo "❗ Please edit .env file with your actual credentials before continuing!"
    exit 1
fi

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Initialize bot
echo "Initializing bot with menu items..."
python manage.py initialize_bot

# Collect static files (for production)
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser (optional)
echo ""
read -p "Do you want to create a Django admin superuser? (y/n): " create_user
if [ "$create_user" = "y" ]; then
    python manage.py createsuperuser
fi

echo ""
echo "✅ Deployment completed!"
echo ""
echo "🔧 Next steps:"
echo "   1. Configure your .env file with actual credentials"
echo "   2. Place your Google service account JSON file in the project root"
echo "   3. Set up your WhatsApp webhook URL"
echo "   4. Start the server with: python manage.py runserver"
echo ""
echo "📱 Webhook URL format: https://yourdomain.com/webhook/"
echo "🌐 Admin interface: https://yourdomain.com/admin/"
