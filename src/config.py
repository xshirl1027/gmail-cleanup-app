import os
import json
from dotenv import load_dotenv

load_dotenv()

"""
Configuration settings for email filtering
"""

def load_user_preferences():
    """Load user preferences from JSON file"""
    config_dir = os.path.dirname(__file__)
    preferences_file = os.path.join(config_dir, 'user_preferences.json')
    
    try:
        with open(preferences_file, 'r') as f:
            preferences = json.load(f)
        return preferences
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading user preferences: {e}")
        # Return default preferences if file doesn't exist or is invalid
        return {
            'to_delete_senders': [],
            'delete_promotional': False,
            'delete_spam': True,
            'delete_newsletters': True,
            'keep_categories': [
                'personal',
                'work', 
                'financial',
                'travel',
                'health',
                'legal',
                'family'
            ],
            'confidence_threshold': 0.6,
            'max_emails_per_run': None
        }

def save_user_preferences(preferences):
    """Save user preferences to JSON file"""
    config_dir = os.path.dirname(__file__)
    preferences_file = os.path.join(config_dir, 'user_preferences.json')
    
    try:
        with open(preferences_file, 'w') as f:
            json.dump(preferences, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving user preferences: {e}")
        return False

# Load user preferences from JSON file
USER_PREFERENCES = load_user_preferences()

# Other configuration constants can be added here as needed.