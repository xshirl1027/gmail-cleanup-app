import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GmailClient:
    def __init__(self):
        self.service = None
        # Update scopes to explicitly include all required permissions
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.labels',
            'https://mail.google.com/'  # Full access scope - includes delete
        ]
        self.creds = None

    def authenticate(self):
        """Authenticate user using OAuth2 flow"""
        # Get the project root directory (one level up from src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        credentials_path = os.path.join(project_root, 'credentials.json')
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
                if not os.path.exists(credentials_path):
                    print(f"Error: credentials.json not found at {credentials_path}")
                    print("Please follow the setup instructions to create OAuth2 credentials.")
                    return False
                
                # Delete token.pickle if it exists to force new authentication with updated scopes
                if os.path.exists(token_path):
                    os.remove(token_path)
                    print("Removed old token to refresh permissions.")
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, self.scopes)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('gmail', 'v1', credentials=self.creds)
        return True

    def get_emails(self, user_id='me', query='', max_results=None):
        """Get emails based on query with pagination support"""
        try:
            emails = []
            next_page_token = None
            total_fetched = 0
            
            while True:
                # Request a batch of messages
                results = self.service.users().messages().list(
                    userId=user_id, 
                    q=query, 
                    pageToken=next_page_token,
                    maxResults=500  # Maximum allowed by Gmail API
                ).execute()
                
                batch = results.get('messages', [])
                if not batch:
                    break
                    
                emails.extend(batch)
                total_fetched += len(batch)
                
                # Print progress
                print(f"Fetched {total_fetched} emails so far...")
                
                # Check if we've reached the maximum requested
                if max_results and total_fetched >= max_results:
                    emails = emails[:max_results]  # Trim to max requested
                    break
                    
                # Get next page token
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    break
                    
            return emails
        except Exception as error:
            print(f'An error occurred: {error}')
            return []

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