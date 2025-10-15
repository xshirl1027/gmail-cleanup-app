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
    print("Authenticating with Gmail...")
    gmail_client = GmailClient()
    if not gmail_client.authenticate():
        print("\nAuthentication failed. Please run setup first:")
        print("python setup_oauth.py")
        return

    print("✓ Authentication successful!")
    
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

def get_list_unsubscribe_header(gmail_client, msg_id):
    """Extract List-Unsubscribe header from email (Gmail's built-in unsubscribe)"""
    try:
        message = gmail_client.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        headers = message['payload'].get('headers', [])
        
        # Look for List-Unsubscribe header
        list_unsubscribe = next((h['value'] for h in headers if h['name'].lower() == 'list-unsubscribe'), None)
        
        if list_unsubscribe:
            # Parse the List-Unsubscribe header
            # Format can be: <mailto:unsub@example.com>, <https://example.com/unsub>
            urls = re.findall(r'<([^>]+)>', list_unsubscribe)
            
            # Prefer HTTPS URLs over mailto
            http_urls = [url for url in urls if url.startswith('http')]
            if http_urls:
                return http_urls[0]
            
            # Return mailto if no HTTP URL found
            if urls:
                return urls[0]
        
        return None
        
    except Exception as e:
        print(f"Error extracting List-Unsubscribe header: {e}")
        return None

def extract_unsubscribe_link(email_content):
    """Extract unsubscribe link from email content as fallback"""
    if not email_content:
        return None
    
    # More comprehensive unsubscribe link patterns
    patterns = [
        # HTML anchor tags with unsubscribe
        r'<a[^>]*href=["\']([^"\']*unsubscribe[^"\']*)["\'][^>]*>.*?</a>',
        r'<a[^>]*href=["\']([^"\']*opt[_-]?out[^"\']*)["\'][^>]*>.*?</a>',
        r'<a[^>]*href=["\']([^"\']*remove[^"\']*)["\'][^>]*>.*?</a>',
        # Direct URLs
        r'https?://[^\s<>"\']*unsubscribe[^\s<>"\']*',
        r'https?://[^\s<>"\']*opt[_-]?out[^\s<>"\']*',
        r'https?://[^\s<>"\']*remove[^\s<>"\']*',
        # Email-specific patterns
        r'https?://[^\s<>"\']*preferences[^\s<>"\']*',
        r'https?://[^\s<>"\']*manage[_-]?subscription[^\s<>"\']*',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, email_content, re.IGNORECASE | re.DOTALL)
        if matches:
            # Clean up the URL (remove any trailing punctuation)
            url = matches[0].strip().rstrip('.,;!?)')
            if url.startswith('http'):
                return url
    
    return None

def get_email_content(gmail_client, msg_id):
    """Extract email content for unsubscribe link detection"""
    try:
        message = gmail_client.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message['payload']
        
        content = ""
        
        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html' and 'data' in part['body']:
                    data = part['body']['data']
                    content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
                elif part['mimeType'] == 'text/plain' and 'data' in part['body'] and not content:
                    data = part['body']['data']
                    content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            # Single part message
            if payload['mimeType'] in ['text/html', 'text/plain'] and 'data' in payload['body']:
                data = payload['body']['data']
                content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return content
    except Exception as e:
        print(f"Error extracting email content: {e}")
        return None

def attempt_unsubscribe(unsubscribe_link, sender_email, method="header"):
    """Attempt unsubscribe using Gmail's List-Unsubscribe or fallback method"""
    try:
        if unsubscribe_link.startswith('mailto:'):
            # Handle mailto unsubscribe (would need email sending capability)
            print(f"   📧 Mailto unsubscribe found: {unsubscribe_link}")
            return True, "Mailto unsubscribe detected (requires email sending)"
        
        print(f"   📍 Found {method} unsubscribe link: {unsubscribe_link[:100]}...")
        
        # Better headers to mimic real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Create a session to handle cookies
        session = requests.Session()
        session.headers.update(headers)
        
        # First, try a GET request
        response = session.get(unsubscribe_link, timeout=15, allow_redirects=True)
        
        print(f"   📊 GET response: {response.status_code}")
        
        if response.status_code == 200:
            # Check if the page contains a form or confirmation
            page_content = response.text.lower()
            
            # Look for common unsubscribe confirmation patterns
            success_patterns = [
                'unsubscribed',
                'removed from list',
                'subscription cancelled',
                'email preferences updated',
                'successfully removed',
                'no longer receive',
                'subscription canceled',
                'opted out',
                'will not receive'
            ]
            
            if any(pattern in page_content for pattern in success_patterns):
                return True, f"Unsubscribe confirmed ({method})"
            
            # Look for forms that might need to be submitted
            if '<form' in page_content and ('unsubscribe' in page_content or 'remove' in page_content or 'opt' in page_content):
                # Try to find and submit the form (basic attempt)
                try:
                    # This is a simple attempt - real form handling would be more complex
                    form_action = re.search(r'<form[^>]*action=["\']([^"\']*)["\']', page_content)
                    if form_action:
                        form_url = form_action.group(1)
                        if not form_url.startswith('http'):
                            # Relative URL - construct full URL
                            parsed_url = urlparse(unsubscribe_link)
                            form_url = f"{parsed_url.scheme}://{parsed_url.netloc}{form_url}"
                        
                        # Try POST request to form
                        form_response = session.post(form_url, timeout=15, allow_redirects=True)
                        print(f"   📝 Form POST response: {form_response.status_code}")
                        
                        if form_response.status_code == 200:
                            return True, f"Form submitted successfully ({method})"
                
                except Exception as form_error:
                    print(f"   ❌ Form submission failed: {form_error}")
            
            return True, f"Page loaded (HTTP {response.status_code}) - may require manual confirmation ({method})"
        else:
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "Request timeout (15s)"
    except requests.exceptions.SSLError:
        return False, "SSL certificate error"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def start_email_cleanup(gmail_client):
    print("📧 Loading user preferences from JSON...")
    # Load fresh preferences from JSON file
    USER_PREFERENCES = load_user_preferences()
    print(f"📋 Loaded preferences: {len(USER_PREFERENCES.get('to_delete_senders', []))} senders to delete")
    
    # Retrieve emails with pagination
    print("📬 Retrieving emails from inbox...")
    query = "in:inbox"
    max_emails = USER_PREFERENCES.get('max_emails_per_run')
    emails = gmail_client.get_emails(query=query, max_results=max_emails)

    if not emails:
        print("📭 No emails found in inbox.")
        return

    print(f"📊 Found {len(emails)} emails to analyze and process...")

    deleted_count = 0
    kept_count = 0
    unsubscribed_count = 0
    to_delete_senders = USER_PREFERENCES.get('to_delete_senders', [])
    should_unsubscribe = USER_PREFERENCES.get('unsubscribe_emails', False)
    
    print(f"🎯 Delete senders list: {to_delete_senders}")
    print(f"🔄 Unsubscribe enabled: {should_unsubscribe}")
    
    # Keep track of senders we've already attempted to unsubscribe from
    unsubscribed_senders = set()

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
            
            # Attempt to unsubscribe before deleting (only once per sender)
            if should_delete and should_unsubscribe and clean_sender not in unsubscribed_senders:
                print(f"🔄 Attempting to unsubscribe from {clean_sender}...")
                
                # First try Gmail's List-Unsubscribe header (most reliable)
                list_unsubscribe_url = get_list_unsubscribe_header(gmail_client, email['id'])
                
                if list_unsubscribe_url:
                    success, message = attempt_unsubscribe(list_unsubscribe_url, clean_sender, "Gmail header")
                    if success:
                        print(f"   ✅ {message}")
                        unsubscribed_count += 1
                    else:
                        print(f"   ❌ Gmail header failed: {message}")
                        # Fallback to email content parsing
                        email_content = get_email_content(gmail_client, email['id'])
                        fallback_link = extract_unsubscribe_link(email_content)
                        if fallback_link:
                            success, message = attempt_unsubscribe(fallback_link, clean_sender, "email content")
                            if success:
                                print(f"   ✅ Fallback successful: {message}")
                                unsubscribed_count += 1
                            else:
                                print(f"   ❌ Fallback failed: {message}")
                        else:
                            print(f"   ❌ No fallback unsubscribe link found")
                else:
                    # No List-Unsubscribe header, try email content
                    email_content = get_email_content(gmail_client, email['id'])
                    unsubscribe_link = extract_unsubscribe_link(email_content)
                    if unsubscribe_link:
                        success, message = attempt_unsubscribe(unsubscribe_link, clean_sender, "email content")
                        if success:
                            print(f"   ✅ {message}")
                            unsubscribed_count += 1
                        else:
                            print(f"   ❌ Failed: {message}")
                    else:
                        print(f"   ❌ No unsubscribe method found")
                
                # Add a small delay between unsubscribe attempts
                time.sleep(2)
                
                # Mark this sender as processed (whether successful or not)
                unsubscribed_senders.add(clean_sender)
            
            if should_delete:
                try:
                    # Move to trash
                    gmail_client.service.users().messages().trash(userId='me', id=email['id']).execute()
                    deleted_count += 1
                    unsubscribe_note = " (after unsubscribe attempt)" if should_unsubscribe and clean_sender in unsubscribed_senders else ""
                    print(f"✓ DELETED: {subject[:50]}... - {delete_reason}{unsubscribe_note} ({deleted_count} total)")
                except Exception as delete_error:
                    print(f"✗ FAILED TO DELETE: {subject[:50]}... - {delete_error}")
            else:
                kept_count += 1
                # Only show kept emails occasionally to reduce spam
                if (i + 1) % 20 == 0:
                    print(f"✗ KEPT: {subject[:50]}... - Sender not in delete list")
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"--- Processed {i + 1}/{len(emails)} emails (Deleted: {deleted_count}, Kept: {kept_count}, Unsubscribed: {unsubscribed_count}) ---")
                
        except Exception as e:
            kept_count += 1
            print(f"✗ ERROR processing email {email['id']}: {e}")
            continue

    print(f"\n🎉 Finished processing {len(emails)} emails.")
    print(f"✓ Deleted: {deleted_count}")
    print(f"✓ Kept: {kept_count}")
    
    if should_unsubscribe:
        print(f"✓ Unsubscribe attempts: {unsubscribed_count}")
        print(f"✓ Unique senders processed for unsubscribe: {len(unsubscribed_senders)}")
        print(f"\n⚠️  Note: Using Gmail's List-Unsubscribe header when available.")
        print(f"   This is the same mechanism Gmail's unsubscribe button uses.")
    
    if deleted_count > 0:
        print(f"\n📧 {deleted_count} emails have been moved to trash.")
        print("You can restore them from Gmail's Trash if needed.")
    
    print("\n✅ Email cleanup completed!")

if __name__ == "__main__":
    main()