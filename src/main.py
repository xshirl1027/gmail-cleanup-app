import os
import re
import requests
from gmail_client import GmailClient
from config import load_user_preferences
from dotenv import load_dotenv
import base64
from email.mime.text import MIMEText
import time
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv()

def main():
    print("🚀 Starting Gmail Cleanup App...")
    
    # Initialize Gmail client
    print("🔐 Authenticating with Gmail...")
    
    try:
        gmail_client = GmailClient()
        if not gmail_client.authenticate():
            print("\n❌ Authentication failed.")
            print("💡 This could be due to:")
            print("   - Network connection issues")
            print("   - Gmail API service temporarily unavailable")
            print("   - Browser-related issues during OAuth")
            print("\n🔄 Try running the app again in a few minutes.")
            return

        print("✅ Authentication successful!")
        
        # Test basic Gmail API access
        print("🧪 Testing Gmail API connection...")
        test_emails = gmail_client.get_emails(query="in:inbox", max_results=1)
        if test_emails is None:
            print("⚠️ Gmail API test failed - continuing anyway")
        else:
            print(f"✅ Gmail API test successful ({len(test_emails)} test email(s) found)")
    
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        print("🔄 Please try running the app again.")
        return
    
    # Use web-based GUI (works without tkinter)
    print("Opening web-based interface...")
    from web_gui import WebGUI
    web_gui = WebGUI(gmail_client)
    should_start_cleanup = web_gui.run()
    
    print(f"🔍 Web GUI returned: should_start_cleanup = {should_start_cleanup}")
    
    # Check if user wants to start cleanup
    if should_start_cleanup:
        print("✅ Starting email cleanup process...")
        start_email_cleanup(gmail_client)
    else:
        print("❌ Cleanup cancelled by user")
        print("Goodbye!")




def start_email_cleanup(gmail_client):
    print("📧 Loading user preferences from JSON...")
    # Load fresh preferences from JSON file
    USER_PREFERENCES = load_user_preferences()
    print(f"📋 Loaded preferences: {len(USER_PREFERENCES.get('to_delete_senders', []))} senders to delete")
    
    # Retrieve emails with pagination
    print("📬 Retrieving emails from inbox...")
    query = "in:inbox"
    max_emails = USER_PREFERENCES.get('max_emails_per_run')
    
    if max_emails:
        print(f"📈 Limiting to {max_emails} emails per run")
    else:
        print("📈 No limit set - will process all emails")
    
    emails = gmail_client.get_emails(query=query, max_results=max_emails)

    if not emails:
        print("📭 No emails found in inbox.")
        print("💡 This could be because:")
        print("   - Your inbox is empty")
        print("   - There was an API error (check above for error messages)")
        print("   - Your Gmail account has no emails matching the query")
        return

    print(f"📊 Found {len(emails)} emails to analyze and process...")

    deleted_count = 0
    kept_count = 0
    to_delete_senders = USER_PREFERENCES.get('to_delete_senders', [])
    
    print(f"🎯 Delete senders list: {to_delete_senders}")

    for i, email in enumerate(emails):
        try:
            # Get email details
            details = gmail_client.get_email_details(msg_id=email['id'])
            headers = details['payload'].get('headers', [])
            
            # Extract sender and subject
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            
            # Clean up sender (extract email from "Name <email>" format)
            if '<' in sender and '>' in sender:
                clean_sender = sender.split('<')[1].split('>')[0].strip()
            else:
                clean_sender = sender.strip()
            
            # Check if sender is in delete list
            should_delete = False
            delete_reason = ""
            
            if clean_sender in to_delete_senders:
                should_delete = True
                delete_reason = f"Sender '{clean_sender}' is in delete list"
            else:
                # Check if domain is in delete list
                if '@' in clean_sender:
                    domain = clean_sender.split('@')[1]
                    for delete_sender in to_delete_senders:
                        if delete_sender == domain or clean_sender.endswith(f"@{delete_sender}"):
                            should_delete = True
                            delete_reason = f"Domain '{domain}' matches delete list"
                            break
            
            if should_delete:
                try:
                    # Move to trash
                    gmail_client.service.users().messages().trash(userId='me', id=email['id']).execute()
                    deleted_count += 1
                    print(f"✓ DELETED: {subject[:50]}... - {delete_reason} ({deleted_count} total)")
                except Exception as delete_error:
                    print(f"✗ FAILED TO DELETE: {subject[:50]}... - {delete_error}")
            else:
                kept_count += 1
                # Only show kept emails occasionally to reduce spam
                if (i + 1) % 20 == 0:
                    print(f"✗ KEPT: {subject[:50]}... - Sender not in delete list")
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"--- Processed {i + 1}/{len(emails)} emails (Deleted: {deleted_count}, Kept: {kept_count}) ---")
                
        except Exception as e:
            kept_count += 1
            print(f"✗ ERROR processing email {email['id']}: {e}")
            continue

    print(f"\n🎉 Finished processing {len(emails)} emails.")
    print(f"✓ Deleted: {deleted_count}")
    print(f"✓ Kept: {kept_count}")
    
    if deleted_count > 0:
        print(f"\n📧 {deleted_count} emails have been moved to trash.")
        print("You can restore them from Gmail's Trash if needed.")
    
    print("\n✅ Email cleanup completed!")

if __name__ == "__main__":
    main()