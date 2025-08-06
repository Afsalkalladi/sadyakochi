# Production Deployment Guide for EeOnam Bot

This guide covers deploying the EeOnam WhatsApp bot to production environments.

## 🚀 Deployment Platforms

### Recommended Platforms

1. **Render** (Easiest, Free Tier Available)
2. **Railway** (Simple, PostgreSQL included)
3. **DigitalOcean App Platform**
4. **Heroku** (Classic choice)

---

## 🌐 Render Deployment (Recommended)

### 1. Prepare Your Repository

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial EeOnam bot commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Add Production Requirements**
   Create `requirements-prod.txt`:
   ```
   Django==4.2.7
   requests==2.31.0
   python-dotenv==1.0.0
   gspread==5.12.0
   google-api-python-client==2.108.0
   google-auth==2.23.4
   google-auth-oauthlib==1.1.0
   google-auth-httplib2==0.1.1
   qrcode[pil]==7.4.2
   Pillow==10.1.0
   pytz==2023.3
   gunicorn==21.2.0
   psycopg2-binary==2.9.7
   whitenoise==6.6.0
   ```

### 2. Configure for Production

1. **Update settings.py** (add to end):
   ```python
   # Production settings
   if not DEBUG:
       DATABASES = {
           'default': {
               'ENGINE': 'django.db.backends.postgresql',
               'NAME': os.getenv('DATABASE_NAME'),
               'USER': os.getenv('DATABASE_USER'),
               'PASSWORD': os.getenv('DATABASE_PASSWORD'),
               'HOST': os.getenv('DATABASE_HOST'),
               'PORT': os.getenv('DATABASE_PORT', '5432'),
           }
       }
   
   # Static files with WhiteNoise
   MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
   STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   ```

2. **Create render.yaml**:
   ```yaml
   databases:
     - name: eeonam-db
       databaseName: eeonam
       user: eeonam
   
   services:
     - type: web
       name: eeonam-bot
       env: python
       buildCommand: "pip install -r requirements-prod.txt && python manage.py collectstatic --noinput && python manage.py migrate"
       startCommand: "gunicorn eeonam_project.wsgi:application"
       envVars:
         - key: DEBUG
           value: False
         - key: PYTHON_VERSION
           value: 3.11.0
         - fromDatabase:
             name: eeonam-db
             property: connectionString
   ```

### 3. Deploy to Render

1. **Connect Repository**
   - Go to https://render.com/
   - Sign up/login and connect GitHub
   - Select your EeOnam repository

2. **Configure Environment Variables**
   Add these in Render dashboard:
   ```env
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   ALLOWED_HOSTS=your-app-name.onrender.com
   BASE_URL=https://your-app-name.onrender.com
   
   WHATSAPP_ACCESS_TOKEN=your_token
   WHATSAPP_PHONE_NUMBER_ID=your_id
   WHATSAPP_VERIFY_TOKEN=your_verify_token
   
   GOOGLE_CREDENTIALS_JSON=./service-account.json
   GOOGLE_SHEET_ID=your_sheet_id
   GOOGLE_DRIVE_FOLDER_ID=your_folder_id
   
   UPI_ID=yourname@bank
   UPI_MERCHANT_NAME=EeOnam
   ```

3. **Upload Google Credentials**
   - Add your `service-account.json` file to your repository
   - ⚠️ **Make sure it's in `.gitignore` for security**
   - Alternative: Use Render's file upload feature

4. **Deploy**
   - Render will automatically deploy from your main branch
   - Monitor the build logs for any issues

---

## 🚄 Railway Deployment

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### 2. Initialize Project
```bash
railway init
railway add postgresql
```

### 3. Set Environment Variables
```bash
railway variables set DEBUG=False
railway variables set SECRET_KEY=your-secret-key
railway variables set ALLOWED_HOSTS=$RAILWAY_PUBLIC_DOMAIN
# ... add all other variables
```

### 4. Deploy
```bash
railway up
```

---

## 🐙 DigitalOcean App Platform

### 1. Create App Spec (`.do/app.yaml`)
```yaml
name: eeonam-bot
services:
- name: web
  source_dir: /
  github:
    repo: your-username/eeonam-bot
    branch: main
  run_command: gunicorn eeonam_project.wsgi:application
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  
databases:
- name: eeonam-db
  engine: PG
  version: "13"
```

### 2. Environment Variables
Set in DigitalOcean dashboard under your app settings.

---

## 📱 WhatsApp Webhook Configuration

### 1. Meta Developer Console
1. Go to https://developers.facebook.com/
2. Select your WhatsApp Business app
3. Configure webhook URL: `https://yourdomain.com/webhook/`
4. Set verify token from your environment variables
5. Subscribe to `messages` webhook field

### 2. Test Webhook
```bash
curl -X GET "https://yourdomain.com/webhook/?hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=12345"
```

Should return: `12345`

---

## 🔍 Monitoring & Debugging

### Health Check
- URL: `https://yourdomain.com/health/`
- Should return: "EeOnam Bot is running!"

### Admin Interface
- URL: `https://yourdomain.com/admin/`
- Create superuser: `python manage.py createsuperuser`

### Logs
- Check your platform's logs dashboard
- Look for Django and WhatsApp API errors

### Test Order Flow
1. Message your WhatsApp Business number
2. Follow the complete order flow
3. Check Google Sheet for data sync
4. Test verification links

---

## 🔒 Security Checklist

- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY
- [ ] Secure Google credentials storage
- [ ] Environment variables properly set
- [ ] HTTPS enabled (automatic on most platforms)
- [ ] Database backups enabled
- [ ] Error monitoring configured

---

## 📊 Google Services in Production

### 1. Service Account Security
- Keep JSON credentials secure
- Use environment variables when possible
- Limit service account permissions

### 2. Rate Limits
- Google APIs have quotas
- Monitor usage in Google Cloud Console
- Implement retry logic for API calls

### 3. Sheet Performance
- Consider splitting data across multiple sheets for high volume
- Archive old orders periodically

---

## 🚨 Troubleshooting

### Common Production Issues

**1. Static Files Not Loading**
```python
# Add to settings.py
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

**2. Database Connection Issues**
- Check DATABASE_URL environment variable
- Verify database credentials
- Ensure database is accessible from app

**3. WhatsApp Webhook Failures**
- Verify webhook URL is accessible
- Check HTTPS certificate
- Validate verify token

**4. Google API Errors**
- Check service account permissions
- Verify API quotas not exceeded
- Ensure credentials file is accessible

### Environment Variables Template

```env
# Production Environment Variables
DEBUG=False
SECRET_KEY=your-super-secret-production-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
BASE_URL=https://yourdomain.com

# Database (auto-configured by platform)
DATABASE_URL=postgresql://...

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your_production_token
WHATSAPP_PHONE_NUMBER_ID=your_production_phone_id
WHATSAPP_VERIFY_TOKEN=your_production_verify_token

# Google
GOOGLE_CREDENTIALS_JSON=./service-account.json
GOOGLE_SHEET_ID=your_production_sheet_id
GOOGLE_DRIVE_FOLDER_ID=your_production_folder_id

# UPI
UPI_ID=yourproduction@upi
UPI_MERCHANT_NAME=EeOnam
```

---

## 🎉 Post-Deployment

1. **Test Complete Flow**
   - Send test WhatsApp messages
   - Verify order processing
   - Check Google integrations

2. **Monitor Performance**
   - Set up error tracking (Sentry)
   - Monitor response times
   - Watch for API rate limits

3. **Scale Planning**
   - Plan for high traffic during Onam
   - Consider additional server resources
   - Set up automated backups

**Your EeOnam bot is now ready for production! 🚀**
