import os
import json
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

TOKEN_PATH = os.getenv('GOOGLE_OAUTH_TOKEN_PATH', 'token.json')

# Accept both credentials.json and client_secret.json
CANDIDATE_CREDENTIAL_FILES = [
    os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'),
    'client_secret.json'
]

def get_google_credentials():
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            logger.debug("🔄 Loading existing credentials from JSON token file...")
            with open(TOKEN_PATH, 'r') as token_file:
                token_data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            logger.debug("✅ Credentials loaded successfully from token.json")
        except Exception as e:
            logger.error(f"❌ Error loading token.json: {str(e)}")
            creds = None
    else:
        logger.warning("⚠️ token.json not found. OAuth flow will be required.")

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.debug("🔄 Refreshing expired credentials...")
            creds.refresh(Request())
            save_credentials(creds)
            logger.debug("✅ Credentials refreshed and saved.")
        except Exception as e:
            logger.error(f"❌ Error refreshing credentials: {str(e)}")
            creds = None

    if not creds or not creds.valid:
        logger.info("📢 Starting OAuth flow to get new credentials...")
        cred_file = next((f for f in CANDIDATE_CREDENTIAL_FILES if os.path.exists(f)), None)
        if not cred_file:
            raise FileNotFoundError("Missing credentials file: credentials.json or client_secret.json")
        logger.info(f"Using credentials file: {cred_file}")

        flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
        creds = flow.run_local_server(port=0)
        save_credentials(creds)
        logger.debug("✅ New credentials obtained and saved.")

    return creds

def save_credentials(creds):
    try:
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
        logger.debug(f"💾 Credentials saved to {TOKEN_PATH}")
    except Exception as e:
        logger.error(f"❌ Error saving credentials: {str(e)}")

if __name__ == "__main__":
    credentials = get_google_credentials()
    if credentials:
        print("✅ Google API authentication successful!")
    else:
        print("❌ Failed to authenticate with Google API.")