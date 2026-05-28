"""
One-time Google OAuth2 setup for Drive API access.
Run this once:
    uv run python -m newsdash.digest.auth_google
"""
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
CREDENTIALS_PATH = CONFIG_DIR / "google_credentials.json"
TOKEN_PATH = CONFIG_DIR / "google_token.json"

def main():
    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: Google credentials file not found at {CREDENTIALS_PATH}", file=sys.stderr)
        print("Please follow the setup instructions in the implementation plan:", file=sys.stderr)
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)", file=sys.stderr)
        print("2. Create a desktop client OAuth 2.0 credential.", file=sys.stderr)
        print("3. Download and save the JSON file to this location.", file=sys.stderr)
        sys.exit(1)

    print("Starting one-time Google OAuth flow...")
    print("This will open a browser window to authenticate with Google.")
    
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Save the token to disk
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    
    print("\nSUCCESS!")
    print(f"Token saved successfully to {TOKEN_PATH}")
    print("You can now close your browser and run your app normally.")

if __name__ == "__main__":
    main()
