# Gmail Cleanup App

This project is a Python application that connects to your Gmail account and helps you clean up unwanted emails--freeing up your storage spaces. It allows you to specify a list of senders for deletion for your entire inbox.

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

<img width="1433" height="763" alt="Screenshot 2025-10-16 at 3 01 09 PM" src="https://github.com/user-attachments/assets/a1059fda-bcc4-43de-a9f4-bc87f09f53bb" />
<img width="1423" height="681" alt="Screenshot 2025-10-16 at 3 12 13 PM" src="https://github.com/user-attachments/assets/80cd3136-1b52-4b07-8fe9-bb181cb4410b" />
<img width="1141" height="774" alt="Screenshot 2025-10-16 at 3 01 36 PM" src="https://github.com/user-attachments/assets/57989b36-77be-4a2d-b850-a2a89c5f1a5a" />


## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.
