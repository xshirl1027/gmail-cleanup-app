import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
from config import USER_PREFERENCES

class EmailManagerUI:
    def __init__(self, gmail_client):
        self.gmail_client = gmail_client
        self.root = tk.Tk()
        self.root.title("Gmail Cleanup - Email Manager")
        self.root.geometry("800x600")
        
        # Load current preferences
        self.preferences = USER_PREFERENCES.copy()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Blocked Senders Management
        self.setup_blocked_senders_tab(notebook)
        
        # Tab 2: Recent Emails Preview
        self.setup_recent_emails_tab(notebook)
        
        # Tab 3: Filter Settings
        self.setup_filter_settings_tab(notebook)
        
        # Bottom buttons
        self.setup_bottom_buttons()
        
    def setup_blocked_senders_tab(self, notebook):
        # Blocked Senders Tab
        blocked_frame = ttk.Frame(notebook)
        notebook.add(blocked_frame, text="Blocked Senders")
        
        # Title
        ttk.Label(blocked_frame, text="Manage Blocked Senders", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Current blocked senders list
        ttk.Label(blocked_frame, text="Currently Blocked Senders:").pack(anchor='w', padx=10)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(blocked_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.blocked_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.blocked_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.blocked_listbox.yview)
        
        # Populate current blocked senders
        self.refresh_blocked_list()
        
        # Add new sender section
        add_frame = ttk.Frame(blocked_frame)
        add_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(add_frame, text="Add new blocked sender:").pack(anchor='w')
        
        entry_frame = ttk.Frame(add_frame)
        entry_frame.pack(fill='x', pady=5)
        
        self.new_sender_entry = ttk.Entry(entry_frame)
        self.new_sender_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(entry_frame, text="Add", command=self.add_blocked_sender).pack(side='right', padx=(5,0))
        
        # Remove sender button
        button_frame = ttk.Frame(blocked_frame)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_blocked_sender).pack(side='left')
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_blocked).pack(side='left', padx=(5,0))
        
    def setup_recent_emails_tab(self, notebook):
        # Recent Emails Tab
        emails_frame = ttk.Frame(notebook)
        notebook.add(emails_frame, text="Recent Emails")
        
        ttk.Label(emails_frame, text="Recent Inbox Emails", font=('Arial', 14, 'bold')).pack(pady=10)
        ttk.Label(emails_frame, text="Click 'Refresh' to load recent emails, then double-click to block a sender:").pack(anchor='w', padx=10)
        
        # Refresh button
        ttk.Button(emails_frame, text="Refresh Recent Emails", command=self.refresh_recent_emails).pack(pady=5)
        
        # Treeview for emails
        columns = ('Sender', 'Subject', 'Date')
        self.emails_tree = ttk.Treeview(emails_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.emails_tree.heading(col, text=col)
            self.emails_tree.column(col, width=250)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(emails_frame, orient='vertical', command=self.emails_tree.yview)
        self.emails_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Pack treeview and scrollbar
        tree_frame = ttk.Frame(emails_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.emails_tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')
        
        # Double-click to block sender
        self.emails_tree.bind('<Double-1>', self.block_sender_from_email)
        
        # Instructions
        ttk.Label(emails_frame, text="Double-click on any email to add its sender to blocked list").pack(pady=5)
        
    def setup_filter_settings_tab(self, notebook):
        # Filter Settings Tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Filter Settings")
        
        ttk.Label(settings_frame, text="Email Filter Settings", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Checkboxes for filter options
        self.delete_promotional_var = tk.BooleanVar(value=self.preferences.get('delete_promotional', False))
        self.delete_spam_var = tk.BooleanVar(value=self.preferences.get('delete_spam', True))
        self.delete_newsletters_var = tk.BooleanVar(value=self.preferences.get('delete_newsletters', True))
        
        ttk.Checkbutton(settings_frame, text="Delete promotional emails", 
                       variable=self.delete_promotional_var).pack(anchor='w', padx=20, pady=5)
        ttk.Checkbutton(settings_frame, text="Delete spam emails", 
                       variable=self.delete_spam_var).pack(anchor='w', padx=20, pady=5)
        ttk.Checkbutton(settings_frame, text="Delete newsletters", 
                       variable=self.delete_newsletters_var).pack(anchor='w', padx=20, pady=5)
        
        # Confidence threshold
        ttk.Label(settings_frame, text="AI Confidence Threshold (0.0 - 1.0):").pack(anchor='w', padx=20, pady=(20,5))
        self.confidence_var = tk.DoubleVar(value=self.preferences.get('confidence_threshold', 0.6))
        confidence_scale = ttk.Scale(settings_frame, from_=0.0, to=1.0, variable=self.confidence_var, orient='horizontal')
        confidence_scale.pack(fill='x', padx=20, pady=5)
        
        # Display current value
        self.confidence_label = ttk.Label(settings_frame, text=f"Current: {self.confidence_var.get():.2f}")
        self.confidence_label.pack(anchor='w', padx=20)
        
        # Update label when scale changes
        confidence_scale.configure(command=self.update_confidence_label)
        
    def setup_bottom_buttons(self):
        # Bottom buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save & Start Cleanup", command=self.save_and_start_cleanup, 
                  style='Accent.TButton').pack(side='right', padx=(5,0))
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(side='right')
        ttk.Button(button_frame, text="Cancel", command=self.root.quit).pack(side='left')
        
    def refresh_blocked_list(self):
        self.blocked_listbox.delete(0, tk.END)
        for sender in self.preferences['blocked_senders']:
            self.blocked_listbox.insert(tk.END, sender)
            
    def add_blocked_sender(self):
        sender = self.new_sender_entry.get().strip()
        if sender and sender not in self.preferences['blocked_senders']:
            self.preferences['blocked_senders'].append(sender)
            self.refresh_blocked_list()
            self.new_sender_entry.delete(0, tk.END)
            messagebox.showinfo("Success", f"Added '{sender}' to blocked list")
        elif sender in self.preferences['blocked_senders']:
            messagebox.showwarning("Warning", f"'{sender}' is already in the blocked list")
        else:
            messagebox.showwarning("Warning", "Please enter a valid email address")
            
    def remove_blocked_sender(self):
        selection = self.blocked_listbox.curselection()
        if selection:
            sender = self.blocked_listbox.get(selection[0])
            self.preferences['blocked_senders'].remove(sender)
            self.refresh_blocked_list()
            messagebox.showinfo("Success", f"Removed '{sender}' from blocked list")
        else:
            messagebox.showwarning("Warning", "Please select a sender to remove")
            
    def clear_all_blocked(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all blocked senders?"):
            self.preferences['blocked_senders'].clear()
            self.refresh_blocked_list()
            messagebox.showinfo("Success", "Cleared all blocked senders")
            
    def refresh_recent_emails(self):
        try:
            # Clear existing items
            for item in self.emails_tree.get_children():
                self.emails_tree.delete(item)
                
            # Get recent emails
            emails = self.gmail_client.get_emails(query="in:inbox", max_results=50)
            
            for email in emails[:20]:  # Show first 20
                try:
                    details = self.gmail_client.get_email_details(msg_id=email['id'])
                    headers = details['payload'].get('headers', [])
                    
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
                    
                    # Clean up sender (keep just email if it's in "Name <email>" format)
                    if '<' in sender and '>' in sender:
                        sender = sender.split('<')[1].split('>')[0]
                    
                    self.emails_tree.insert('', 'end', values=(sender, subject[:50], date[:20]))
                except Exception as e:
                    continue
                    
            messagebox.showinfo("Success", f"Loaded recent emails")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load emails: {e}")
            
    def block_sender_from_email(self, event):
        selection = self.emails_tree.selection()
        if selection:
            item = self.emails_tree.item(selection[0])
            sender = item['values'][0]
            
            if sender not in self.preferences['blocked_senders']:
                self.preferences['blocked_senders'].append(sender)
                self.refresh_blocked_list()
                messagebox.showinfo("Success", f"Added '{sender}' to blocked list")
            else:
                messagebox.showinfo("Info", f"'{sender}' is already blocked")
                
    def update_confidence_label(self, value):
        self.confidence_label.config(text=f"Current: {float(value):.2f}")
        
    def save_settings(self):
        # Update preferences with UI values
        self.preferences['delete_promotional'] = self.delete_promotional_var.get()
        self.preferences['delete_spam'] = self.delete_spam_var.get()
        self.preferences['delete_newsletters'] = self.delete_newsletters_var.get()
        self.preferences['confidence_threshold'] = self.confidence_var.get()
        
        # Save to config file
        self.save_preferences_to_file()
        messagebox.showinfo("Success", "Settings saved successfully!")
        
    def save_preferences_to_file(self):
        # Update the config.py file with new preferences
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
            
    def save_and_start_cleanup(self):
        self.save_settings()
        self.root.quit()
        return True  # Signal to start cleanup
        
    def run(self):
        self.root.mainloop()
        return hasattr(self, '_start_cleanup')