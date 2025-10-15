import os
from config import USER_PREFERENCES

class EmailManagerCLI:
    def __init__(self, gmail_client):
        self.gmail_client = gmail_client
        self.preferences = USER_PREFERENCES.copy()
        
    def run(self):
        print("\n" + "="*60)
        print("         GMAIL CLEANUP - EMAIL MANAGER")
        print("="*60)
        
        while True:
            self.show_main_menu()
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                self.manage_blocked_senders()
            elif choice == '2':
                self.view_recent_emails()
            elif choice == '3':
                self.manage_filter_settings()
            elif choice == '4':
                self.save_settings()
                print("\n✓ Settings saved! Starting email cleanup...")
                return True  # Signal to start cleanup
            elif choice == '5':
                print("\nEmail cleanup cancelled.")
                return False
            else:
                print("\nInvalid choice. Please try again.")
                
    def show_main_menu(self):
        print("\n" + "-"*60)
        print("MAIN MENU")
        print("-"*60)
        print("1. Manage Blocked Senders")
        print("2. View Recent Emails")
        print("3. Filter Settings")
        print("4. Save Settings & Start Cleanup")
        print("5. Exit")
        
    def manage_blocked_senders(self):
        while True:
            print("\n" + "-"*60)
            print("BLOCKED SENDERS MANAGEMENT")
            print("-"*60)
            print("Current blocked senders:")
            
            if not self.preferences['blocked_senders']:
                print("  (No blocked senders)")
            else:
                for i, sender in enumerate(self.preferences['blocked_senders'], 1):
                    print(f"  {i}. {sender}")
                    
            print("\nOptions:")
            print("1. Add new blocked sender")
            print("2. Remove blocked sender")
            print("3. Clear all blocked senders")
            print("4. Back to main menu")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                self.add_blocked_sender()
            elif choice == '2':
                self.remove_blocked_sender()
            elif choice == '3':
                self.clear_all_blocked()
            elif choice == '4':
                break
            else:
                print("Invalid choice. Please try again.")
                
    def add_blocked_sender(self):
        sender = input("\nEnter email address to block: ").strip()
        if sender:
            if sender not in self.preferences['blocked_senders']:
                self.preferences['blocked_senders'].append(sender)
                print(f"✓ Added '{sender}' to blocked list")
            else:
                print(f"'{sender}' is already in the blocked list")
        else:
            print("Please enter a valid email address")
            
    def remove_blocked_sender(self):
        if not self.preferences['blocked_senders']:
            print("No blocked senders to remove")
            return
            
        print("\nSelect sender to remove:")
        for i, sender in enumerate(self.preferences['blocked_senders'], 1):
            print(f"{i}. {sender}")
            
        try:
            choice = int(input("\nEnter number to remove (0 to cancel): "))
            if choice == 0:
                return
            elif 1 <= choice <= len(self.preferences['blocked_senders']):
                removed = self.preferences['blocked_senders'].pop(choice - 1)
                print(f"✓ Removed '{removed}' from blocked list")
            else:
                print("Invalid selection")
        except ValueError:
            print("Please enter a valid number")
            
    def clear_all_blocked(self):
        if not self.preferences['blocked_senders']:
            print("No blocked senders to clear")
            return
            
        confirm = input("Are you sure you want to clear all blocked senders? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            self.preferences['blocked_senders'].clear()
            print("✓ Cleared all blocked senders")
        else:
            print("Operation cancelled")
            
    def view_recent_emails(self):
        print("\n" + "-"*60)
        print("RECENT EMAILS")
        print("-"*60)
        print("Loading recent emails...")
        
        try:
            emails = self.gmail_client.get_emails(query="in:inbox", max_results=20)
            
            if not emails:
                print("No emails found")
                return
                
            print(f"\nShowing {len(emails)} recent emails:")
            print("-"*60)
            
            email_senders = []
            for i, email in enumerate(emails, 1):
                try:
                    details = self.gmail_client.get_email_details(msg_id=email['id'])
                    headers = details['payload'].get('headers', [])
                    
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    
                    # Clean up sender (keep just email if it's in "Name <email>" format)
                    if '<' in sender and '>' in sender:
                        clean_sender = sender.split('<')[1].split('>')[0]
                    else:
                        clean_sender = sender
                    
                    email_senders.append(clean_sender)
                    
                    print(f"{i:2d}. From: {sender[:50]}")
                    print(f"    Subject: {subject[:60]}")
                    print()
                    
                except Exception:
                    continue
                    
            # Option to block sender from this list
            print("Options:")
            print("1. Block a sender from this list")
            print("2. Back to main menu")
            
            choice = input("\nEnter your choice (1-2): ").strip()
            
            if choice == '1':
                try:
                    sender_num = int(input(f"Enter email number to block (1-{len(email_senders)}): "))
                    if 1 <= sender_num <= len(email_senders):
                        sender_to_block = email_senders[sender_num - 1]
                        if sender_to_block not in self.preferences['blocked_senders']:
                            self.preferences['blocked_senders'].append(sender_to_block)
                            print(f"✓ Added '{sender_to_block}' to blocked list")
                        else:
                            print(f"'{sender_to_block}' is already blocked")
                    else:
                        print("Invalid selection")
                except ValueError:
                    print("Please enter a valid number")
                    
        except Exception as e:
            print(f"Error loading emails: {e}")
            
    def manage_filter_settings(self):
        while True:
            print("\n" + "-"*60)
            print("FILTER SETTINGS")
            print("-"*60)
            print(f"1. Delete promotional emails: {'✓' if self.preferences['delete_promotional'] else '✗'}")
            print(f"2. Delete spam emails: {'✓' if self.preferences['delete_spam'] else '✗'}")
            print(f"3. Delete newsletters: {'✓' if self.preferences['delete_newsletters'] else '✗'}")
            print(f"4. AI Confidence threshold: {self.preferences['confidence_threshold']:.2f}")
            print("5. Back to main menu")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                self.preferences['delete_promotional'] = not self.preferences['delete_promotional']
                print(f"✓ Delete promotional emails: {'ON' if self.preferences['delete_promotional'] else 'OFF'}")
            elif choice == '2':
                self.preferences['delete_spam'] = not self.preferences['delete_spam']
                print(f"✓ Delete spam emails: {'ON' if self.preferences['delete_spam'] else 'OFF'}")
            elif choice == '3':
                self.preferences['delete_newsletters'] = not self.preferences['delete_newsletters']
                print(f"✓ Delete newsletters: {'ON' if self.preferences['delete_newsletters'] else 'OFF'}")
            elif choice == '4':
                try:
                    threshold = float(input(f"Enter confidence threshold (0.0-1.0, current: {self.preferences['confidence_threshold']:.2f}): "))
                    if 0.0 <= threshold <= 1.0:
                        self.preferences['confidence_threshold'] = threshold
                        print(f"✓ Confidence threshold set to {threshold:.2f}")
                    else:
                        print("Please enter a value between 0.0 and 1.0")
                except ValueError:
                    print("Please enter a valid number")
            elif choice == '5':
                break
            else:
                print("Invalid choice. Please try again.")
                
    def save_settings(self):
        # Save to config file
        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        
        config_content = f'''import os
from dotenv import load_dotenv

load_dotenv()

"""
Configuration settings for email filtering
"""

# User preferences for email filtering
USER_PREFERENCES = {{
    # Senders to always delete (exact email matches or domains)
    'blocked_senders': {self.preferences['blocked_senders']},
    
    # Categories to delete
    'delete_promotional': {self.preferences['delete_promotional']},
    'delete_spam': {self.preferences['delete_spam']},
    'delete_newsletters': {self.preferences['delete_newsletters']},
    
    # Categories to always keep
    'keep_categories': {self.preferences['keep_categories']},
    
    # Confidence threshold (0.0-1.0) - higher means more conservative
    'confidence_threshold': {self.preferences['confidence_threshold']},
    
    # Set to None or a very large number to process all emails
    'max_emails_per_run': {self.preferences['max_emails_per_run']}
}}
'''
        
        with open(config_path, 'w') as f:
            f.write(config_content)
            
        print("✓ Settings saved successfully!")