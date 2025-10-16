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

def check_content_filtering(gmail_client, email_id, subject, sender, clean_sender, delete_promotional, delete_spam, delete_newsletters):
    """
    Check if email should be deleted based on content filtering criteria
    Returns (should_delete: bool, reason: str)
    """
    subject_lower = subject.lower()
    sender_lower = sender.lower()
    
    # Check if email is in Promotional folder/label
    if delete_promotional:
        try:
            # Get email details to check labels (using minimal format for efficiency)
            message = gmail_client.service.users().messages().get(
                userId='me', 
                id=email_id, 
                format='minimal'
            ).execute()
            labels = message.get('labelIds', [])
            
            # Check for promotional labels
            promotional_labels = ['CATEGORY_PROMOTIONS', 'PROMOTIONS']
            for label in labels:
                if label in promotional_labels:
                    return True, "Gmail Promotional folder"
        except Exception as e:
            print(f"   ⚠️  Warning: Could not check promotional folder for email {email_id}: {e}")
    
    # Spam keywords  
    spam_keywords = [
        'viagra', 'casino', 'lottery', 'winner', 'congratulations', 'prize',
        'free money', 'click here', 'act now', 'urgent', 'limited time only',
        'no obligation', 'risk free', 'guarantee', 'make money fast'
    ]
    
    # Newsletter indicators
    newsletter_keywords = [
        'newsletter', 'weekly update', 'monthly digest', 'subscribe', 'unsubscribe',
        'mailing list', 'email list', 'bulletin', 'digest', 'update'
    ]
    
    # Newsletter sender patterns
    newsletter_senders = [
        'newsletter@', 'noreply@', 'no-reply@', 'updates@', 'news@', 
        'marketing@', 'promo@', 'offers@', 'notifications@'
    ]
    
    # Check for spam content
    if delete_spam:
        for keyword in spam_keywords:
            if keyword in subject_lower or keyword in sender_lower:
                return True, f"Spam content detected: '{keyword}'"
    
    # Check for newsletters
    if delete_newsletters:
        # Check newsletter keywords in subject/sender
        for keyword in newsletter_keywords:
            if keyword in subject_lower or keyword in sender_lower:
                return True, f"Newsletter content detected: '{keyword}'"
        
        # Check newsletter sender patterns
        for pattern in newsletter_senders:
            if pattern in clean_sender.lower():
                return True, f"Newsletter sender pattern: '{pattern}'"
    
    return False, ""

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
    
    # Build Gmail search queries based on user preferences
    print("📬 Building Gmail search queries based on user preferences...")
    
    search_queries = []
    
    # 1. Search for emails from specific senders to delete
    to_delete_senders = USER_PREFERENCES.get('to_delete_senders', [])
    if to_delete_senders:
        # Build query for specific senders
        sender_queries = []
        for sender in to_delete_senders:
            if '@' in sender:
                sender_queries.append(f'from:"{sender}"')
            else:
                # If it's just a domain, search for emails from that domain
                sender_queries.append(f'from:"@{sender}"')
        
        if sender_queries:
            sender_query = "(" + " OR ".join(sender_queries) + ")"
            search_queries.append(sender_query)
            print(f"🎯 Added sender filter: {len(to_delete_senders)} senders")
    
    # 2. Search promotional emails if enabled
    if USER_PREFERENCES.get('delete_promotional', False):
        search_queries.append("category:promotions")
        print("🛍️  Added promotional folder filter")
    
    # 3. Search for spam-like emails if enabled
    if USER_PREFERENCES.get('delete_spam', False):
        spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'congratulations', 'prize', 'free money']
        spam_query = "(" + " OR ".join([f'subject:"{keyword}"' for keyword in spam_keywords]) + ")"
        search_queries.append(spam_query)
        print("� Added spam keyword filter")
    
    # 4. Search for newsletter emails if enabled  
    if USER_PREFERENCES.get('delete_newsletters', False):
        # More specific newsletter patterns to avoid false positives
        newsletter_query = '(from:"newsletter@" OR from:"unsubscribe@" OR from:"mailings@" OR from:"digest@" OR subject:"newsletter" OR subject:"unsubscribe" OR subject:"weekly digest" OR subject:"monthly update")'
        search_queries.append(newsletter_query)
        print("📰 Added newsletter pattern filter (conservative)")
    
    if not search_queries:
        print("❌ No filtering criteria enabled - nothing to delete")
        return
    
    # Combine all queries with OR
    final_query = " OR ".join(search_queries)
    print(f"🔍 Final Gmail search query: {final_query}")
    
    max_emails = USER_PREFERENCES.get('max_emails_per_run')
    if max_emails:
        print(f"📈 Limiting to {max_emails} emails per run")
    else:
        print("📈 No limit set - will process all matching emails")
    
    # Get emails using Gmail's native filtering
    print("📨 Searching emails using Gmail's native filters...")
    emails = gmail_client.get_emails(query=final_query, max_results=max_emails)
    
    if not emails:
        print("✨ No emails found matching the filter criteria!")
        return
    
    print(f"📊 Found {len(emails)} emails matching filter criteria")

    if not emails:
        print("📭 No emails found in inbox.")
        print("💡 This could be because:")
        print("   - Your inbox is empty")
        print("   - There was an API error (check above for error messages)")
        print("   - Your Gmail account has no emails matching the query")
        return

    # Since Gmail has already filtered emails based on our search criteria,
    # all returned emails match our deletion criteria
    print(f"\n🔄 Analyzing {len(emails)} pre-filtered emails for deletion...")
    print("💡 All these emails already match your deletion criteria via Gmail search")

    emails_to_delete = []
    
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
            
            # Determine why this email was matched (for display purposes)
            delete_reason = "Matched Gmail search filters"
            to_delete_senders = USER_PREFERENCES.get('to_delete_senders', [])
            
            if clean_sender in to_delete_senders:
                delete_reason = f"Sender '{clean_sender}' in delete list"
            elif '@' in clean_sender:
                domain = clean_sender.split('@')[1] if '@' in clean_sender else ''
                if any(clean_sender.endswith(f"@{ds}") or domain == ds for ds in to_delete_senders):
                    delete_reason = f"Domain '{domain}' in delete list"
                elif clean_sender.startswith('noreply@') or clean_sender.startswith('no-reply@'):
                    delete_reason = "Newsletter sender pattern (noreply)"
                elif clean_sender.startswith('newsletter@') or clean_sender.startswith('unsubscribe@'):
                    delete_reason = "Newsletter sender pattern"
                elif clean_sender.startswith('mailings@') or clean_sender.startswith('digest@'):
                    delete_reason = "Newsletter/Digest sender"
                elif USER_PREFERENCES.get('delete_promotional', False) and ('promotional' in subject.lower() or 'unsubscribe' in subject.lower()):
                    delete_reason = "Promotional content in subject"
            
            # Add to deletion list
            emails_to_delete.append({
                'id': email['id'],
                'sender': clean_sender,
                'subject': subject,
                'reason': delete_reason
            })
            
            print(f"🗑️  MARKED FOR DELETION: {subject[:60]}... - {delete_reason}")
            
            # Progress indicator
            if (i + 1) % 25 == 0:
                print(f"--- Processed {i + 1}/{len(emails)} emails ---")
                
        except Exception as e:
            print(f"✗ ERROR processing email {email['id']}: {e}")
            continue

    # Show filtering results
    print(f"\n📋 FILTERING COMPLETE:")
    print(f"   📧 Total emails found by Gmail search: {len(emails)}")
    print(f"   🗑️  Emails queued for deletion: {len(emails_to_delete)}")
    print(f"   ✅ All emails matched deletion criteria (Gmail pre-filtered)")
    
    if not emails_to_delete:
        print("\n🎉 No emails match your deletion criteria. Nothing to delete!")
        return
    
    # Show preview of emails to be deleted
    print(f"\n📝 EMAILS TO BE DELETED:")
    for i, email_info in enumerate(emails_to_delete[:10]):  # Show first 10
        print(f"   {i+1:2d}. {email_info['subject'][:50]}... (from {email_info['sender']}) - {email_info['reason']}")
    
    if len(emails_to_delete) > 10:
        print(f"   ... and {len(emails_to_delete) - 10} more emails")
    
    # Confirmation prompt
    print(f"\n⚠️  WARNING: This will permanently move {len(emails_to_delete)} emails to trash!")
    print("   (You can restore them from Gmail's Trash folder if needed)")
    
    confirm = input("\n❓ Proceed with deletion? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("❌ Deletion cancelled by user.")
        return
    
    # PHASE 2: Delete all marked emails
    print(f"\n🗑️  Phase 2: Deleting {len(emails_to_delete)} emails...")
    
    deleted_count = 0
    failed_count = 0
    
    for i, email_info in enumerate(emails_to_delete):
        try:
            # Move to trash
            gmail_client.service.users().messages().trash(userId='me', id=email_info['id']).execute()
            deleted_count += 1
            
            # Show progress every 10 deletions
            if deleted_count % 10 == 0:
                print(f"   ✓ Deleted {deleted_count}/{len(emails_to_delete)} emails...")
                
        except Exception as delete_error:
            failed_count += 1
            print(f"   ✗ FAILED to delete: {email_info['subject'][:30]}... - {delete_error}")

    # Final results
    print(f"\n🎉 CLEANUP COMPLETED!")
    print(f"   ✅ Successfully deleted: {deleted_count} emails")
    print(f"   ❌ Failed to delete: {failed_count} emails")
    print(f"   � Gmail search targeted only matching emails")
    
    if deleted_count > 0:
        print(f"\n📧 {deleted_count} emails have been moved to trash.")
        print("   You can restore them from Gmail's Trash folder if needed.")
    
    print("\n✅ Email cleanup completed!")

if __name__ == "__main__":
    main()