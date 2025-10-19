import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import base64

# Load environment variables
load_dotenv()

class EmailFilter:
    def __init__(self):
        # Configure Gemini AI
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        # Updated model name - use gemini-1.5-flash or gemini-1.5-pro
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def extract_email_content(self, gmail_client, message_id):
        """Extract readable content from Gmail message"""
        try:
            message = gmail_client.get_email_details(msg_id=message_id)
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            
            # Extract body content
            body = self._extract_body(message['payload'])
            
            # Extract Gmail labels/categories
            labels = message.get('labelIds', [])
            
            return {
                'sender': sender,
                'subject': subject,
                'body': body[:1000] if body else '',  # Limit body to 1000 chars
                'message_id': message_id,
                'labels': labels  # Include Gmail labels
            }
        except Exception as e:
            print(f"Error extracting email content: {e}")
            return None
    
    def _extract_body(self, payload):
        """Extract text body from email payload"""
        body = ""
        
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
                    elif part['mimeType'] == 'text/html' and not body:
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        except Exception as e:
            print(f"Error extracting body: {e}")
            return ""
        
        return body
    
    def should_delete_email(self, email_content, user_preferences):
        """Use Gemini AI to determine if email should be deleted"""
        
        prompt = f"""
        You are an email filtering assistant. Analyze the following email and determine if it should be DELETED based on the user's preferences.

        USER PREFERENCES:
        - Senders to always delete: {user_preferences.get('blocked_senders', [])}
        - Delete promotional emails: {user_preferences.get('delete_promotional', True)}
        - Delete spam emails: {user_preferences.get('delete_spam', True)}
        - Delete newsletters: {user_preferences.get('delete_newsletters', False)}
        - Keep important categories: {user_preferences.get('keep_categories', ['personal', 'work', 'financial', 'travel'])}

        EMAIL TO ANALYZE:
        From: {email_content['sender']}
        Subject: {email_content['subject']}
        Body Preview: {email_content['body'][:500]}...
        Gmail Labels: {email_content.get('labels', [])}

        INSTRUCTIONS:
        1. Check if sender is in blocked list
        2. Determine email category (promotional, spam, newsletter, personal, work, financial, travel, etc.)
        3. Assess importance and relevance
        4. Consider if this looks like automated marketing, spam, or unwanted content

        Respond with ONLY a JSON object in this exact format:
        {{
            "delete": true,
            "reason": "Brief explanation of why this email should or shouldn't be deleted",
            "category": "email category (promotional, spam, personal, work, etc.)",
            "confidence": 0.9
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Clean the response text
            response_text = response.text.strip()
            
            # Remove any markdown formatting if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            return self._fallback_filter(email_content, user_preferences)
        except Exception as e:
            print(f"Error with Gemini AI analysis: {e}")
            # Fallback to basic keyword filtering
            return self._fallback_filter(email_content, user_preferences)
    
    def _fallback_filter(self, email_content, user_preferences):
        """Fallback filtering logic if AI fails - now uses Gmail labels"""
        sender = email_content['sender'].lower()
        subject = email_content['subject'].lower()
        body = email_content['body'].lower()
        labels = email_content.get('labels', [])
        
        # Check blocked senders
        for blocked_sender in user_preferences.get('blocked_senders', []):
            if blocked_sender.lower() in sender:
                return {
                    "delete": True,
                    "reason": f"Sender {blocked_sender} is in blocked list",
                    "category": "blocked",
                    "confidence": 1.0
                }
        
        # Check Gmail promotional category using labels
        if user_preferences.get('delete_promotional', False):
            promotional_labels = ['CATEGORY_PROMOTIONS', 'PROMOTIONS']
            if any(label in labels for label in promotional_labels):
                return {
                    "delete": True,
                    "reason": "Email is in Gmail Promotional category",
                    "category": "promotional",
                    "confidence": 0.95
                }
        
        # Check Gmail social category using labels
        if user_preferences.get('delete_social', False):
            social_labels = ['CATEGORY_SOCIAL', 'SOCIAL']
            if any(label in labels for label in social_labels):
                return {
                    "delete": True,
                    "reason": "Email is in Gmail Social category",
                    "category": "social",
                    "confidence": 0.95
                }
        
        # Check for spam keywords
        spam_keywords = [
            'viagra', 'casino', 'lottery', 'winner', 'congratulations',
            'free money', 'click here', 'act now', 'limited time'
        ]
        
        content = f"{subject} {body}"
        
        if any(keyword in content for keyword in spam_keywords):
            return {
                "delete": True,
                "reason": "Contains spam keywords",
                "category": "spam",
                "confidence": 0.9
            }
        
        # Newsletter detection - more specific patterns
        newsletter_keywords = ['unsubscribe', 'newsletter', 'weekly digest', 'monthly update']
        newsletter_senders = ['newsletter@', 'noreply@', 'no-reply@', 'updates@', 'news@']
        
        if user_preferences.get('delete_newsletters', False):
            if any(keyword in content for keyword in newsletter_keywords):
                return {
                    "delete": True,
                    "reason": "Newsletter content detected",
                    "category": "newsletter",
                    "confidence": 0.8
                }
            
            if any(pattern in sender for pattern in newsletter_senders):
                return {
                    "delete": True,
                    "reason": "Newsletter sender pattern detected",
                    "category": "newsletter",
                    "confidence": 0.8
                }
        
        # Job-related emails - be more conservative
        job_keywords = ['job', 'career', 'position', 'hiring', 'interview', 'resume']
        if any(keyword in content for keyword in job_keywords):
            return {
                "delete": False,
                "reason": "Job-related email - keeping for review",
                "category": "career",
                "confidence": 0.8
            }
        
        return {
            "delete": False,
            "reason": "No deletion criteria met",
            "category": "unknown",
            "confidence": 0.5
        }


def filter_emails(gmail_client, emails, user_preferences):
    """
    Filter emails using AI to determine which should be deleted
    """
    email_filter = EmailFilter()
    emails_to_delete = []
    
    print(f"Analyzing {len(emails)} emails...")
    
    for i, email in enumerate(emails):
        try:
            # Extract email content
            email_content = email_filter.extract_email_content(gmail_client, email['id'])
            
            if email_content:
                # Use AI to determine if email should be deleted
                decision = email_filter.should_delete_email(email_content, user_preferences)
                
                if decision['delete'] and decision['confidence'] > 0.6:
                    emails_to_delete.append({
                        'id': email['id'],
                        'sender': email_content['sender'],
                        'subject': email_content['subject'],
                        'reason': decision['reason'],
                        'category': decision['category'],
                        'confidence': decision['confidence']
                    })
                    
                    print(f"✓ WILL DELETE: {email_content['subject'][:50]}... - {decision['reason']}")
                else:
                    print(f"✗ KEEPING: {email_content['subject'][:50]}... - {decision['reason']}")
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(emails)} emails...")
                
        except Exception as e:
            print(f"Error processing email {email['id']}: {e}")
            continue
    
    return emails_to_delete