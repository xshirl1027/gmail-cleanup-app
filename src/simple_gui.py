import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
from config import USER_PREFERENCES

class SimpleEmailGUI:
    def __init__(self, gmail_client):
        self.gmail_client = gmail_client
        self.root = tk.Tk()
        self.root.title("Gmail Cleanup - Blocked Senders Manager")
        self.root.geometry("600x500")
        
        # Load current preferences
        self.preferences = USER_PREFERENCES.copy()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main title
        title_label = ttk.Label(self.root, text="Gmail Cleanup - Blocked Senders", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Instructions
        instructions = ttk.Label(self.root, 
                               text="Paste email addresses (one per line) that you want to block:",
                               font=('Arial', 10))
        instructions.pack(pady=(0, 10))
        
        # Text area for pasting blocked senders
        text_frame = ttk.Frame(self.root)
        text_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        ttk.Label(text_frame, text="Blocked Senders:").pack(anchor='w')
        
        # Scrolled text widget for easy pasting
        self.blocked_text = scrolledtext.ScrolledText(text_frame, 
                                                     height=15, 
                                                     width=70,
                                                     font=('Consolas', 10))
        self.blocked_text.pack(fill='both', expand=True, pady=(5, 0))
        
        # Load current blocked senders into text area
        self.load_current_blocked_senders()
        
        # Quick settings frame
        settings_frame = ttk.LabelFrame(self.root, text="Quick Settings", padding=10)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        # Checkboxes for common settings
        self.delete_promotional_var = tk.BooleanVar(value=self.preferences.get('delete_promotional', False))
        self.delete_spam_var = tk.BooleanVar(value=self.preferences.get('delete_spam', True))
        self.delete_newsletters_var = tk.BooleanVar(value=self.preferences.get('delete_newsletters', True))
        
        checkbox_frame = ttk.Frame(settings_frame)
        checkbox_frame.pack(fill='x')
        
        ttk.Checkbutton(checkbox_frame, text="Delete promotional emails", 
                       variable=self.delete_promotional_var).pack(side='left', padx=(0, 20))
        ttk.Checkbutton(checkbox_frame, text="Delete spam emails", 
                       variable=self.delete_spam_var).pack(side='left', padx=(0, 20))
        ttk.Checkbutton(checkbox_frame, text="Delete newsletters", 
                       variable=self.delete_newsletters_var).pack(side='left')
        
        # Buttons frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', padx=20, pady=20)
        
        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side='left')
        
        ttk.Button(left_buttons, text="Clear All", 
                  command=self.clear_all_text).pack(side='left', padx=(0, 10))
        ttk.Button(left_buttons, text="Load Recent Senders", 
                  command=self.load_recent_senders).pack(side='left', padx=(0, 10))
        
        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side='right')
        
        ttk.Button(right_buttons, text="Cancel", 
                  command=self.cancel).pack(side='left', padx=(0, 10))
        ttk.Button(right_buttons, text="Save & Start Cleanup", 
                  command=self.save_and_start, 
                  style='Accent.TButton').pack(side='left')
        
        # Add some helpful text at the bottom
        help_text = ttk.Label(self.root, 
                             text="Tip: You can paste multiple email addresses at once, or use 'Load Recent Senders' to see recent inbox senders",
                             font=('Arial', 9), 
                             foreground='gray')
        help_text.pack(pady=(0, 10))
        
    def load_current_blocked_senders(self):
        """Load current blocked senders into the text area"""
        current_senders = '\n'.join(self.preferences['blocked_senders'])
        self.blocked_text.insert('1.0', current_senders)
        
    def clear_all_text(self):
        """Clear the text area"""
        if messagebox.askyesno("Confirm", "Clear all blocked senders from the list?"):
            self.blocked_text.delete('1.0', tk.END)
            
    def load_recent_senders(self):
        """Load recent email senders and let user select which to add"""
        try:
            # Get recent emails
            emails = self.gmail_client.get_emails(query="in:inbox", max_results=50)
            
            if not emails:
                messagebox.showinfo("Info", "No recent emails found")
                return
                
            # Extract unique senders
            senders = set()
            for email in emails[:20]:  # Check first 20 emails
                try:
                    details = self.gmail_client.get_email_details(msg_id=email['id'])
                    headers = details['payload'].get('headers', [])
                    
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                    
                    # Clean up sender (extract email from "Name <email>" format)
                    if '<' in sender and '>' in sender:
                        clean_sender = sender.split('<')[1].split('>')[0].strip()
                    else:
                        clean_sender = sender.strip()
                        
                    if clean_sender and '@' in clean_sender:
                        senders.add(clean_sender)
                        
                except Exception:
                    continue
                    
            if not senders:
                messagebox.showinfo("Info", "No email addresses found in recent emails")
                return
                
            # Show selection window
            self.show_sender_selection(list(senders))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recent senders: {e}")
            
    def show_sender_selection(self, senders):
        """Show a selection window for recent senders"""
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Senders to Block")
        selection_window.geometry("500x400")
        selection_window.transient(self.root)
        selection_window.grab_set()
        
        ttk.Label(selection_window, text="Select senders to add to blocked list:", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Frame for checkboxes
        checkbox_frame = ttk.Frame(selection_window)
        checkbox_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create a scrollable frame
        canvas = tk.Canvas(checkbox_frame)
        scrollbar = ttk.Scrollbar(checkbox_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Variables to track selections
        sender_vars = {}
        
        # Create checkboxes for each sender
        for sender in sorted(senders):
            var = tk.BooleanVar()
            sender_vars[sender] = var
            ttk.Checkbutton(scrollable_frame, text=sender, variable=var).pack(anchor='w', pady=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = ttk.Frame(selection_window)
        button_frame.pack(fill='x', padx=20, pady=10)
        
        def select_all():
            for var in sender_vars.values():
                var.set(True)
                
        def select_none():
            for var in sender_vars.values():
                var.set(False)
                
        def add_selected():
            selected_senders = [sender for sender, var in sender_vars.items() if var.get()]
            if selected_senders:
                current_text = self.blocked_text.get('1.0', tk.END).strip()
                if current_text:
                    new_text = current_text + '\n' + '\n'.join(selected_senders)
                else:
                    new_text = '\n'.join(selected_senders)
                    
                self.blocked_text.delete('1.0', tk.END)
                self.blocked_text.insert('1.0', new_text)
                
                messagebox.showinfo("Success", f"Added {len(selected_senders)} senders to blocked list")
            
            selection_window.destroy()
        
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side='left')
        ttk.Button(button_frame, text="Select None", command=select_none).pack(side='left', padx=(5,0))
        ttk.Button(button_frame, text="Cancel", command=selection_window.destroy).pack(side='right')
        ttk.Button(button_frame, text="Add Selected", command=add_selected).pack(side='right', padx=(0,5))
        
    def save_and_start(self):
        """Save settings and signal to start cleanup"""
        # Get blocked senders from text area
        text_content = self.blocked_text.get('1.0', tk.END).strip()
        # Parse email addresses (one per line, filter out empty lines)
        blocked_senders = []
        for line in text_content.split('\n'):
            email = line.strip()
            if email and '@' in email:
                blocked_senders.append(email)
        # Update preferences
        self.preferences['blocked_senders'] = blocked_senders
        self.preferences['delete_promotional'] = self.delete_promotional_var.get()
        self.preferences['delete_spam'] = self.delete_spam_var.get()
        self.preferences['delete_newsletters'] = self.delete_newsletters_var.get()
        # Save to config file
        self.save_preferences_to_file()
        messagebox.showinfo("Success", f"Saved {len(blocked_senders)} blocked senders. Starting cleanup...")
        # Set flag to start cleanup
        self.start_cleanup = True
        self.root.quit()
        self.root.destroy()
        
    def cancel(self):
        """Cancel without saving"""
        self.start_cleanup = False
        self.root.quit()
        self.root.destroy()
        
    def save_preferences_to_file(self):
        """Save preferences to config.py file"""
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
            
    def run(self):
        """Run the GUI and return whether to start cleanup"""
        self.start_cleanup = False
        self.root.mainloop()
        return getattr(self, 'start_cleanup', False)