# Gmail Cleanup App

This project is a Python application that connects to your Gmail account and helps you clean up unwanted emails. It allows you to specify a list of senders for deletion for your entire inbox.

## Project Structure

```
gmail-cleanup-app
├── src
│   ├── main.py          # Entry point of the application
│   ├── gmail_client.py  # Handles Gmail API communication
│   ├── email_filter.py  # Functions for filtering emails
│   └── config.py       # Configuration settings and environment variable loading
├── requirements.txt     # Project dependencies
├── .env.example         # Template for environment variables
└── README.md            # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone https://github.com/yourusername/gmail-cleanup-app.git
   cd gmail-cleanup-app
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **No additional setup required!**
   - The app includes built-in Gmail API credentials
   - Just run the app and sign in with your Gmail account when prompted
   
   **Note**: If you get an "access_denied" error or message about "unverified app", see the Troubleshooting section below.

## Usage

1. **Run the application:**   
   ```bash
   python src/main.py
   ```

2. **First time setup:**
   - A web browser will open asking you to sign in to your Gmail account
   - Grant permission for the app to access your Gmail
   - The app will remember your authorization for future use

3. **Configure email filtering:**
   - Use the web interface to specify which email senders to block
   - Choose filtering options (promotional, spam, newsletters)
   - Click "Save & Start Cleanup" to begin

## Functionality

- **Authenticate with Gmail:** The application uses OAuth2 to authenticate and access your Gmail account.
- **Retrieve Emails:** It fetches emails from your inbox.
- **Filter Emails:** The application identifies emails from specified senders and those containing promotional keywords.
- **Delete Emails:** Unwanted emails are deleted based on the filtering criteria.

## Troubleshooting

### "Access Denied" or "Unverified App" Error

If you get an error message like "This app hasn't been verified by Google" or "access_denied (403)", this means the app is in testing mode. Here are your options:

**Option 1: Contact the Developer (Recommended)**
- Contact me to add your Gmail address as a test user
- This is the quickest solution

**Option 2: Use Your Own Google Cloud Project**
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project
- Enable the Gmail API
- Create OAuth2 credentials for "Desktop Application"
- Replace the embedded credentials in `src/gmail_client.py` with your own

**Option 3: Continue Despite Warning (Advanced Users)**
- On the Google sign-in page, click "Advanced"
- Click "Go to [app name] (unsafe)"
- This bypasses the verification warning

### Other Common Issues

**"Token has been expired or revoked"**
- Delete the `token.pickle` file and run the app again
- This will prompt you to re-authenticate

**"No emails found in inbox"**
- This might be a temporary Gmail API issue
- Wait a few minutes and try again
- Check that your Gmail account actually has emails in the inbox

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.
