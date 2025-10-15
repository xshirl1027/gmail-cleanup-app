# Gmail Cleanup App

This project is a Python application that connects to your Gmail account and helps you clean up unwanted emails. It allows you to specify a list of senders and keywords to identify promotional or spam emails for deletion.

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

4. **Set up Gmail API credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application" as the application type
   - Download the credentials file and save it as `credentials.json` in the project root
   - **Important**: Never share or commit this file publicly

## Usage

1. **Run the application:**
   ```
   python src/main.py
   ```

2. **Specify the senders and keywords:**
   - Modify the `main.py` file to include the list of senders and promotional keywords you want to filter out.

## Functionality

- **Authenticate with Gmail:** The application uses OAuth2 to authenticate and access your Gmail account.
- **Retrieve Emails:** It fetches emails from your inbox.
- **Filter Emails:** The application identifies emails from specified senders and those containing promotional keywords.
- **Delete Emails:** Unwanted emails are deleted based on the filtering criteria.

## Contributing

Feel free to submit issues or pull requests for improvements or bug fixes.