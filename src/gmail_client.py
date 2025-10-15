import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GmailClient:
    def __init__(self):
        self.service = None
        # Use the most comprehensive Gmail scope to avoid permission issues
        self.scopes = ['https://mail.google.com/']
        self.creds = None
        
        # Embedded OAuth2 credentials - users don't need to create their own
        self.client_config = {
            "installed": {
                "client_id": "695220780841-tclno1hte8j2c12krlq6vd13mqoq6fcg.apps.googleusercontent.com",
                "project_id": "free-your-email",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "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",
                "redirect_uris": ["http://localhost"]
            }
        }

    def authenticate(self):
        """Authenticate user using OAuth2 flow"""
        # Get the project root directory (one level up from src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(project_root, 'token.pickle')
        
        # Check if we have saved credentials
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                print("🔐 Gmail authentication required...")
                print("A browser window will open for you to sign in to your Gmail account.")
                print("This app will only access your Gmail to help clean up emails.")
                input("Press Enter to continue...")
                
                # Delete token.pickle if it exists to force new authentication with updated scopes
                if os.path.exists(token_path):
                    os.remove(token_path)
                    print("Removed old token to refresh permissions.")
                    
                # Use embedded credentials instead of file
                flow = InstalledAppFlow.from_client_config(
                    self.client_config, self.scopes)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('gmail', 'v1', credentials=self.creds)
        return True

    def get_emails(self, user_id='me', query='', max_results=None):
        """Get emails based on query with pagination support and retry logic"""
        import time
        from googleapiclient.errors import HttpError
        
        emails = []
        next_page_token = None
        total_fetched = 0
        retry_count = 0
        max_retries = 3
        
        print(f"🔍 Searching for emails with query: '{query}'")
        
        while True:
            try:
                # Use smaller batch size to avoid server overload
                batch_size = min(100, max_results - total_fetched if max_results else 100)
                
                # Request a batch of messages
                results = self.service.users().messages().list(
                    userId=user_id, 
                    q=query, 
                    pageToken=next_page_token,
                    maxResults=batch_size
                ).execute()
                
                batch = results.get('messages', [])
                if not batch:
                    print("📭 No more emails found")
                    break
                    
                emails.extend(batch)
                total_fetched += len(batch)
                
                # Print progress
                print(f"📨 Fetched {total_fetched} emails so far...")
                
                # Check if we've reached the maximum requested
                if max_results and total_fetched >= max_results:
                    emails = emails[:max_results]  # Trim to max requested
                    break
                    
                # Get next page token
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    print("✅ Reached end of emails")
                    break
                
                # Reset retry count on successful request
                retry_count = 0
                
                # Small delay to be nice to Gmail API
                time.sleep(0.1)
                    
            except HttpError as error:
                retry_count += 1
                print(f"⚠️ Gmail API error (attempt {retry_count}/{max_retries}): {error}")
                
                if retry_count >= max_retries:
                    print("❌ Max retries reached. Gmail API may be experiencing issues.")
                    if error.resp.status == 403:
                        print("📋 This might be a quota or permission issue.")
                        print("💡 Try again in a few minutes or check your Gmail API quotas.")
                    elif error.resp.status == 500:
                        print("🔧 Gmail servers returned 'Unknown Error' (HTTP 500)")
                        print("💭 This is usually a temporary issue on Google's side")
                        print("🔄 Solutions to try:")
                        print("   1. Wait 5-10 minutes and try again")
                        print("   2. Try with a smaller batch of emails")
                        print("   3. Check if Gmail web interface is working normally")
                        print("   4. Clear your token.pickle file and re-authenticate")
                    elif error.resp.status >= 500:
                        print("🔧 Gmail servers are experiencing issues. Try again later.")
                    break
                
                # Exponential backoff
                wait_time = 2 ** retry_count
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
                
            except Exception as error:
                print(f"❌ Unexpected error: {error}")
                break
                    
        print(f"📊 Total emails retrieved: {len(emails)}")
        return emails

    def get_email_details(self, user_id='me', msg_id=''):
        """Get detailed information about a specific email"""
        try:
            message = self.service.users().messages().get(userId=user_id, id=msg_id).execute()
            return message
        except Exception as error:
            print(f'An error occurred: {error}')
            return None

    def delete_email(self, user_id='me', msg_id=''):
        """Delete a specific email"""
        try:
            self.service.users().messages().delete(userId=user_id, id=msg_id).execute()
            return True
        except Exception as error:
            print(f'An error occurred during deletion: {error}')
            
            # Try trash instead of delete
            try:
                self.service.users().messages().trash(userId=user_id, id=msg_id).execute()
                print(f"Message {msg_id} moved to trash instead.")
                return True
            except Exception as trash_error:
                print(f"Failed to move to trash: {trash_error}")
                return False

    def batch_delete_emails(self, user_id='me', msg_ids=[]):
        """Delete multiple emails in batch"""
        if not msg_ids:
            return False
        
        try:
            body = {'ids': msg_ids}
            self.service.users().messages().batchDelete(userId=user_id, body=body).execute()
            print(f'Successfully deleted {len(msg_ids)} messages.')
            return True
        except Exception as error:
            print(f'An error occurred during batch delete: {error}')
            
            # Try batch trash instead
            try:
                for msg_id in msg_ids:
                    self.service.users().messages().trash(userId=user_id, id=msg_id).execute()
                print(f"Moved {len(msg_ids)} messages to trash instead.")
                return True
            except Exception as trash_error:
                print(f"Failed batch trash operation: {trash_error}")
                
                # If batch fails, try deleting individually
                success = 0
                for msg_id in msg_ids:
                    if self.delete_email(user_id=user_id, msg_id=msg_id):
                        success += 1
                
                if success > 0:
                    print(f"Successfully deleted {success} out of {len(msg_ids)} messages individually.")
                return success > 0