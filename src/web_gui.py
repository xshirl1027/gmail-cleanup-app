import http.server
import socketserver
import webbrowser
import json
import os
import time
from urllib.parse import parse_qs, urlparse
from config import USER_PREFERENCES, save_user_preferences

should_start_cleanup = False

class WebGUIHandler(http.server.BaseHTTPRequestHandler):
    gmail_client = None
    preferences = None

    def log_message(self, format, *args):
        # Suppress server logs
        pass

    def do_GET(self):
        if self.path == '/':
            self.serve_main_page()
        elif self.path == '/recent-senders':
            self.serve_recent_senders()
        elif self.path == '/close':
            self.handle_close()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/add-email':
            self.handle_add_email()
        elif self.path == '/remove-email':
            self.handle_remove_email()
        elif self.path == '/save-settings':
            self.handle_save_settings()
        elif self.path == '/cancel':
            self.handle_cancel()
        else:
            self.send_error(404)

    def serve_main_page(self):
        blocked_emails_html = ""
        for i, email in enumerate(self.preferences['to_delete_senders']):
            blocked_emails_html += f'<div class="email-item" data-email="{email}"><span>{email}</span><button onclick="removeEmail(\'{email}\')">×</button></div>'
        
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Gmail Cleanup - Emails to Delete</title>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f7fa; 
            color: #333;
        }}
        .container {{ 
            max-width: 700px; 
            margin: 0 auto; 
            background: white; 
            padding: 40px; 
            border-radius: 12px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); 
        }}
        h1 {{ 
            color: #2c3e50; 
            text-align: center; 
            margin-bottom: 30px;
            font-size: 24px;
        }}
        .add-section {{
            margin: 25px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        .input-group {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }}
        #email-input {{
            flex: 1;
            padding: 12px;
            border: 2px solid #e1e8ed;
            border-radius: 6px;
            font-size: 14px;
        }}
        #email-input:focus {{
            outline: none;
            border-color: #3498db;
        }}
        .add-btn {{
            padding: 12px 20px;
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }}
        .add-btn:hover {{
            background-color: #c0392b;
        }}
        .emails-list {{
            margin: 25px 0;
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #e1e8ed;
            border-radius: 6px;
            background-color: #fafafa;
        }}
        .email-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            border-bottom: 1px solid #e1e8ed;
            font-family: monospace;
            font-size: 13px;
        }}
        .email-item:last-child {{
            border-bottom: none;
        }}
        .email-item:hover {{
            background-color: #f1f3f4;
        }}
        .email-item button {{
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            cursor: pointer;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .email-item button:hover {{
            background: #c0392b;
        }}
        .counter {{
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
            margin: 15px 0;
        }}
        .empty-state {{
            text-align: center;
            color: #95a5a6;
            padding: 40px;
            font-style: italic;
        }}
        .checkbox-group {{ 
            margin: 20px 0; 
            display: flex;
            gap: 25px;
            flex-wrap: wrap;
        }}
        .checkbox-group label {{ 
            display: flex;
            align-items: center;
            font-size: 14px;
            cursor: pointer;
        }}
        .checkbox-group input[type="checkbox"] {{
            margin-right: 8px;
            transform: scale(1.1);
        }}
        .button-group {{ 
            text-align: center; 
            margin-top: 40px; 
            padding-top: 30px;
            border-top: 1px solid #ecf0f1;
        }}
        button {{ 
            padding: 12px 24px; 
            margin: 8px; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 14px; 
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        .success {{ 
            background-color: #27ae60; 
            color: white; 
            font-size: 16px;
            padding: 15px 30px;
        }}
        .success:hover {{
            background-color: #219a52;
        }}
        .danger {{ 
            background-color: #e74c3c; 
            color: white; 
        }}
        .danger:hover {{
            background-color: #c0392b;
        }}
        .secondary {{
            background-color: #95a5a6;
            color: white;
        }}
        .secondary:hover {{
            background-color: #7f8c8d;
        }}
        .help-text {{
            color: #7f8c8d;
            font-size: 12px;
            margin: 10px 0;
        }}
        .delete-warning {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 10px;
            border-radius: 6px;
            margin: 15px 0;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗑️ Gmail Cleanup - Emails to Delete</h1>
        
        <div class="add-section">
            <h3>Add Email to Delete</h3>
            <div class="input-group">
                <input type="email" id="email-input" placeholder="Enter email address to delete..." autofocus>
                <button class="add-btn" onclick="addEmail()">🗑️ Add to Delete</button>
            </div>
            <button class="secondary" onclick="loadRecentSenders()">📬 Load Recent Senders</button>
            <div class="help-text">Press Enter to add email • Click on recent senders to add them to delete list</div>
            <div class="delete-warning">
                ⚠️ <strong>Warning:</strong> Emails from these senders will be automatically deleted from your inbox.
            </div>
        </div>

        <div class="counter" id="counter">{len(self.preferences['to_delete_senders'])} emails to delete</div>
        
        <div class="emails-list" id="emails-list">
            {blocked_emails_html if blocked_emails_html else '<div class="empty-state">No emails to delete yet<br>Add some email addresses above to get started</div>'}
        </div>

        <div class="add-section">
            <h3>⚙️ Filter Settings</h3>
            <div class="checkbox-group">
                <label><input type="checkbox" id="delete-promotional" {"checked" if self.preferences.get('delete_promotional') else ""}> 🛍️ Delete promotional emails</label>
                <label><input type="checkbox" id="delete-spam" {"checked" if self.preferences.get('delete_spam') else ""}> 🚫 Delete spam emails</label>
                <label><input type="checkbox" id="delete-newsletters" {"checked" if self.preferences.get('delete_newsletters') else ""}> 📰 Delete newsletters</label>
            </div>
        </div>

        <div class="button-group">
            <button class="danger" onclick="cancel()">❌ Cancel</button>
            <button class="success" onclick="saveAndStart()">✅ Save & Start Cleanup</button>
        </div>
    </div>

    <script>
        let emailsToDelete = {json.dumps(self.preferences['to_delete_senders'])};

        function updateCounter() {{
            document.getElementById('counter').textContent = emailsToDelete.length + ' emails to delete';
        }}

        function updateEmailsList() {{
            const container = document.getElementById('emails-list');
            
            if (emailsToDelete.length === 0) {{
                container.innerHTML = '<div class="empty-state">No emails to delete yet<br>Add some email addresses above to get started</div>';
            }} else {{
                container.innerHTML = emailsToDelete.map(email => 
                    `<div class="email-item" data-email="${{email}}">
                        <span>${{email}}</span>
                        <button onclick="removeEmail('${{email}}')">×</button>
                    </div>`
                ).join('');
            }}
            
            updateCounter();
        }}

        function addEmail() {{
            const input = document.getElementById('email-input');
            const email = input.value.trim().toLowerCase();
            
            if (!email) {{
                return;
            }}
            
            if (!email.includes('@') || !email.includes('.')) {{
                alert('Please enter a valid email address');
                return;
            }}
            
            if (emailsToDelete.includes(email)) {{
                alert('Email already in delete list');
                input.value = '';
                return;
            }}
            
            fetch('/add-email', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{email: email}})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    emailsToDelete.push(email);
                    updateEmailsList();
                    input.value = '';
                    input.focus();
                }} else {{
                    alert('Error adding email: ' + data.error);
                }}
            }});
        }}

        function removeEmail(email) {{
            if (true) {{
                fetch('/remove-email', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{email: email}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        emailsToDelete = emailsToDelete.filter(e => e !== email);
                        updateEmailsList();
                    }} else {{
                        alert('Error removing email: ' + data.error);
                    }}
                }});
            }}
        }}

        function loadRecentSenders() {{
            const button = event.target;
            const originalText = button.textContent;
            button.textContent = '⏳ Loading...';
            button.disabled = true;
            
            fetch('/recent-senders')
                .then(response => response.json())
                .then(data => {{
                    if (data.senders && data.senders.length > 0) {{
                        const selection = prompt(
                            'Recent senders (will be added to DELETE list):\\n\\n' + 
                            data.senders.map((sender, i) => `${{i+1}}. ${{sender}}`).join('\\n') +
                            '\\n\\nEnter numbers to DELETE (e.g., 1,3,5) or type email addresses:'
                        );
                        
                        if (selection) {{
                            // Check if it's numbers or email addresses
                            if (/^[0-9,\\s]+$/.test(selection)) {{
                                // Numbers
                                const numbers = selection.split(',').map(n => parseInt(n.trim()) - 1);
                                numbers.forEach(index => {{
                                    if (index >= 0 && index < data.senders.length) {{
                                        const email = data.senders[index];
                                        if (!emailsToDelete.includes(email)) {{
                                            addEmailDirectly(email);
                                        }}
                                    }}
                                }});
                            }} else {{
                                // Email addresses
                                const emails = selection.split(',').map(e => e.trim());
                                emails.forEach(email => {{
                                    if (email.includes('@') && !emailsToDelete.includes(email)) {{
                                        addEmailDirectly(email);
                                    }}
                                }});
                            }}
                        }}
                    }} else {{
                        alert('No recent senders found');
                    }}
                    
                    button.textContent = originalText;
                    button.disabled = false;
                }})
                .catch(error => {{
                    alert('Error loading recent senders');
                    button.textContent = originalText;
                    button.disabled = false;
                }});
        }}

        function addEmailDirectly(email) {{
            fetch('/add-email', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{email: email}})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    emailsToDelete.push(email);
                    updateEmailsList();
                }}
            }});
        }}

        function saveAndStart() {{
            const settings = {{
                to_delete_senders: emailsToDelete,
                delete_promotional: document.getElementById('delete-promotional').checked,
                delete_spam: document.getElementById('delete-spam').checked,
                delete_newsletters: document.getElementById('delete-newsletters').checked
            }};

            const button = event.target;
            const originalText = button.textContent;
            button.textContent = '💾 Saving...';
            button.disabled = true;

            fetch('/save-settings', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(settings)
            }})
            .then(response => {{
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('text/html')) {{
                    // Success - HTML response means settings were saved
                    return response.text().then(html => {{
                        document.write(html);
                        document.close();
                    }});
                }} else {{
                    // Error - JSON response
                    return response.json().then(data => {{
                        alert('❌ Error: ' + data.error);
                        button.textContent = originalText;
                        button.disabled = false;
                    }});
                }}
            }})
            .catch(error => {{
                alert('❌ Error: ' + error);
                button.textContent = originalText;
                button.disabled = false;
            }});
        }}

        function cancel() {{
            if (confirm('❌ Cancel email cleanup?')) {{
                fetch('/cancel', {{
                    method: 'POST'
                }})
                .then(response => response.text())
                .then(html => {{
                    document.write(html);
                    document.close();
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    window.close();
                }});
            }}
        }}

        // Enter key to add email
        document.getElementById('email-input').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                addEmail();
            }}
        }});
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def handle_add_email(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            email = data['email'].strip().lower()
            
            if email and '@' in email and email not in self.preferences['to_delete_senders']:
                self.preferences['to_delete_senders'].append(email)
                # Save to JSON file immediately
                success = save_user_preferences(self.preferences)
                response = {'success': success}
            else:
                response = {'success': False, 'error': 'Invalid or duplicate email'}
            
        except Exception as e:
            response = {'success': False, 'error': str(e)}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def handle_remove_email(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            email = data['email']
            
            if email in self.preferences['to_delete_senders']:
                self.preferences['to_delete_senders'].remove(email)
                # Save to JSON file immediately
                success = save_user_preferences(self.preferences)
                response = {'success': success}
            else:
                response = {'success': False, 'error': 'Email not found'}
            
        except Exception as e:
            response = {'success': False, 'error': str(e)}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def serve_recent_senders(self):
        try:
            emails = self.gmail_client.get_emails(query="in:inbox", max_results=30)
            
            senders = set()
            for email in emails:
                try:
                    details = self.gmail_client.get_email_details(msg_id=email['id'])
                    headers = details['payload'].get('headers', [])
                    
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                    
                    if '<' in sender and '>' in sender:
                        clean_sender = sender.split('<')[1].split('>')[0].strip()
                    else:
                        clean_sender = sender.strip();
                        
                    if clean_sender and '@' in clean_sender and len(clean_sender) < 100:
                        senders.add(clean_sender)
                        
                except Exception:
                    continue
            
            response = {'senders': sorted(list(senders))[:15]}
            
        except Exception as e:
            response = {'senders': [], 'error': str(e)}
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def handle_save_settings(self):
        global should_start_cleanup
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            settings = json.loads(post_data.decode())
            
            self.preferences['to_delete_senders'] = settings['to_delete_senders']
            self.preferences['delete_promotional'] = settings['delete_promotional']
            self.preferences['delete_spam'] = settings['delete_spam']
            self.preferences['delete_newsletters'] = settings['delete_newsletters']
            
            # Save to JSON file
            success = save_user_preferences(self.preferences)
            
            should_start_cleanup = True
            
            if success:
                # Return success page that closes the window
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                close_html = '''
                <html>
                <head><title>Gmail Cleanup - Success</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>✅ Settings Saved Successfully!</h2>
                    <p>Starting email cleanup...</p>
                    <p>You can close this window.</p>
                    <script>
                        setTimeout(function() {
                            window.close();
                        }, 2000);
                    </script>
                </body>
                </html>
                '''
                self.wfile.write(close_html.encode())
            else:
                # Return error as JSON for JavaScript to handle
                response = {'success': False, 'error': 'Failed to save settings'}
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            response = {'success': False, 'error': str(e)}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

    def handle_close(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><script>window.close();</script><p>You can close this window.</p></body></html>')

    def handle_cancel(self):
        global should_start_cleanup
        should_start_cleanup = False  # Ensure cleanup doesn't start
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        cancel_html = '''
        <html>
        <head><title>Gmail Cleanup - Cancelled</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>❌ Email Cleanup Cancelled</h2>
            <p>No changes were made.</p>
            <p>You can close this window.</p>
            <script>
                setTimeout(function() {
                    window.close();
                }, 2000);
            </script>
        </body>
        </html>
        '''
        self.wfile.write(cancel_html.encode())

class WebGUI:
    def __init__(self, gmail_client):
        self.gmail_client = gmail_client
        self.port = 8080
        
    def run(self):
        global should_start_cleanup
        should_start_cleanup = False
        
        # Set up the handler class with gmail client and preferences
        WebGUIHandler.gmail_client = self.gmail_client
        WebGUIHandler.preferences = USER_PREFERENCES.copy()
        
        # Find an available port
        for port in range(8080, 8090):
            try:
                with socketserver.TCPServer(("", port), WebGUIHandler) as httpd:
                    self.port = port
                    print(f"🌐 Opening web interface at http://localhost:{port}")
                    
                    # Open browser
                    webbrowser.open(f'http://localhost:{port}')
                    
                    # Handle requests until user saves or cancels
                    while not should_start_cleanup:
                        httpd.handle_request()
                        
                    break
                    
            except OSError:
                continue
        
        return should_start_cleanup