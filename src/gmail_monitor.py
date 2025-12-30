# src/gmail_monitor.py
"""
Gmail Integration Service for Hugo AI Agent.
Monitors a Gmail inbox for supplier emails and triggers processing.

Uses OAuth2 for secure access to Gmail API.
Scalable design: Can be extended to use Pub/Sub for real-time notifications.
"""

import os
import sys
import time
import base64
import email
from email import policy
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scope - read-only access to emails
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configuration
CREDENTIALS_FILE = PROJECT_ROOT / 'gmail_api_credentials.json'
TOKEN_FILE = PROJECT_ROOT / 'gmail_token.json'
EMAIL_DIR = PROJECT_ROOT / 'data' / 'emails'
POLL_INTERVAL = 30  # seconds between checks

# Track processed message IDs to avoid duplicates
processed_message_ids = set()


def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth2.
    First run will open a browser for user consent.
    Subsequent runs use cached token.
    """
    creds = None
    
    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=8090)
        
        # Save token for future runs
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)


def get_supplier_emails(service, after_date=None):
    """
    Fetch emails from suppliers.
    Filters emails that look like supplier communications.
    
    Args:
        service: Gmail API service instance
        after_date: Only fetch emails after this date
    
    Returns:
        List of email messages
    """
    try:
        # Build query for supplier emails
        query_parts = []
        
        # Look for common supplier email patterns
        supplier_keywords = [
            'subject:(delay OR discontinuation OR quality OR shipment OR price OR order)',
            'from:(supplier OR vendor OR sales OR dispatch)',
        ]
        
        # Only get recent emails
        if after_date:
            query_parts.append(f'after:{after_date.strftime("%Y/%m/%d")}')
        
        query = ' '.join(query_parts) if query_parts else 'is:unread'
        
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        return results.get('messages', [])
        
    except HttpError as error:
        print(f"❌ Gmail API error: {error}")
        return []


def download_email(service, message_id):
    """
    Download a specific email and save as .eml file.
    
    Args:
        service: Gmail API service instance
        message_id: Gmail message ID
    
    Returns:
        Path to saved email file, or None if failed
    """
    global processed_message_ids
    
    # Skip if already processed
    if message_id in processed_message_ids:
        return None
    
    try:
        # Get full message
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='raw'
        ).execute()
        
        # Decode raw email
        raw_email = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        email_message = email.message_from_bytes(raw_email, policy=policy.default)
        
        # Generate filename from subject
        subject = email_message['Subject'] or 'no_subject'
        # Clean subject for filename
        safe_subject = "".join(c if c.isalnum() or c in ' _-' else '_' for c in subject)
        safe_subject = safe_subject[:50].strip()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gmail_{timestamp}_{safe_subject}.eml"
        filepath = EMAIL_DIR / filename
        
        # Save email
        EMAIL_DIR.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(raw_email)
        
        # Mark as processed
        processed_message_ids.add(message_id)
        
        print(f"📥 Downloaded: {filename}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error downloading email: {e}")
        return None


def monitor_inbox(callback=None):
    """
    Main monitoring loop.
    Polls Gmail every POLL_INTERVAL seconds for new emails.
    
    Args:
        callback: Optional function to call when new email is processed
    """
    print("🔄 Authenticating with Gmail...")
    service = authenticate_gmail()
    print("✅ Gmail authentication successful!")
    
    # Only check emails from today
    check_from = datetime.now() - timedelta(days=1)
    
    print(f"📧 Monitoring Gmail inbox (polling every {POLL_INTERVAL}s)...")
    print("   Press Ctrl+C to stop\n")
    
    while True:
        try:
            messages = get_supplier_emails(service, after_date=check_from)
            
            for msg in messages:
                filepath = download_email(service, msg['id'])
                
                if filepath and callback:
                    callback(filepath)
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n👋 Gmail monitoring stopped.")
            break
        except Exception as e:
            print(f"⚠️ Error in monitoring loop: {e}")
            time.sleep(POLL_INTERVAL)


def process_gmail_email(filepath):
    """
    Callback function to process downloaded email through Hugo.
    """
    from src.workflow import app
    from src.email_tools import store_email_metadata
    from src.issue_tools import create_issue_from_email
    
    try:
        # Read email content
        with open(filepath, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        
        # Extract content
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()
        
        content = f"From: {msg['From']}\nSubject: {msg['Subject']}\n\n{body}"
        filename = filepath.name
        
        print(f"\n📩 Processing: {filename}")
        print("🤖 Hugo is analyzing...")
        
        # Run workflow
        initial_state = {
            "email_content": content,
            "filename": filename,
            "extraction": {},
            "final_report": ""
        }
        
        result = app.invoke(initial_state)
        extraction = result.get("extraction", {})
        
        # Store metadata
        store_email_metadata(
            filename=filename,
            sender=msg['From'] or "",
            subject=msg['Subject'] or "",
            extraction=extraction,
            summary=result.get("final_report", "")
        )
        
        # Create issue if critical
        risk_score = extraction.get("risk_score", 1)
        if risk_score >= 4:
            issue_id = create_issue_from_email(
                filename=filename,
                intent=extraction.get("intent", "OTHER"),
                risk_score=risk_score,
                part_id=extraction.get("part_id"),
                order_id=extraction.get("order_id"),
                reasoning=extraction.get("reasoning")
            )
            if issue_id:
                print(f"🎫 Issue created: {issue_id}")
        
        print("✅ Email processed!")
        
    except Exception as e:
        print(f"❌ Error processing email: {e}")


if __name__ == "__main__":
    monitor_inbox(callback=process_gmail_email)
