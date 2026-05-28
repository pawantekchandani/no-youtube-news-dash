import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from newsdash.digest.brief_generator import generate_brief_markdown

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
CREDENTIALS_PATH = CONFIG_DIR / "google_credentials.json"
TOKEN_PATH = CONFIG_DIR / "google_token.json"
DEFAULT_FOLDER_NAME = "Newsdash Daily Briefs"

def get_drive_service():
    """Authenticate and build the Google Drive API client."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        
    # If there are no (valid) credentials available, let the user know they need to auth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Google Drive OAuth token...")
            try:
                creds.refresh(Request())
                TOKEN_PATH.write_text(creds.to_json())
            except Exception as e:
                logger.error(f"Failed to refresh OAuth token: {e}")
                creds = None
        else:
            creds = None

    if not creds:
        raise FileNotFoundError(
            f"Google Drive credentials not found or expired. Please run the one-time authentication script:\n"
            f"  uv run python -m newsdash.digest.auth_google"
        )

    return build("drive", "v3", credentials=creds)

def get_or_create_folder(service, folder_name: str) -> str:
    """Find a folder by name or create it if it doesn't exist, returning the Folder ID."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])

    if files:
        folder_id = files[0]['id']
        logger.info(f"Found existing Google Drive folder '{folder_name}' (ID: {folder_id})")
        return folder_id

    # Not found, let's create it
    logger.info(f"Creating new Google Drive folder: '{folder_name}'")
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    folder_id = folder.get('id')
    logger.info(f"Successfully created Google Drive folder '{folder_name}' (ID: {folder_id})")
    return folder_id

def markdown_to_html(md: str) -> str:
    """Converts standard newsdash markdown format to clean HTML for Google Doc conversion."""
    import re
    lines = md.split("\n")
    html_lines = []
    in_quote = False
    
    for line in lines:
        stripped = line.strip()
        
        # Handle blockquotes
        if stripped.startswith(">"):
            content = line.replace(">", "", 1).strip()
            # Convert bold and italic inside quote
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
            if not in_quote:
                html_lines.append("<blockquote>")
                in_quote = True
            html_lines.append(f"<p>{content}</p>")
            continue
        else:
            if in_quote:
                html_lines.append("</blockquote>")
                in_quote = False
        
        # Handle headers
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            html_lines.append(f"<h1>{title}</h1>")
        elif stripped.startswith("## "):
            header = stripped[3:].strip()
            html_lines.append(f"<h2>{header}</h2>")
        elif stripped == "---":
            html_lines.append("<hr>")
        else:
            # Handle inline markup for normal lines
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
            
            # Convert markdown links [text](url) to HTML links <a href="url">text</a>
            formatted = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', formatted)
            
            # Convert URL lines to real clickable links (backward compatibility)
            if formatted.strip().startswith("URL:"):
                url = formatted.replace("URL:", "", 1).strip()
                formatted = f"URL: <a href='{url}'>{url}</a>"
            
            if formatted.strip():
                html_lines.append(f"<p>{formatted}</p>")
            else:
                html_lines.append("<br>")
                
    if in_quote:
        html_lines.append("</blockquote>")
        
    return "<html><head><meta charset='utf-8'></head><body>" + "\n".join(html_lines) + "</body></html>"

def upload_brief(service, folder_id: str, filename: str, content: str) -> str:
    """Uploads the brief content, converting it to a Google Doc and overwriting if it exists."""
    # Find existing file by name in folder (without extension)
    escaped_filename = filename.replace("'", "\\'")
    query = f"name='{escaped_filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])

    # Convert markdown to html for high-fidelity conversion to Google Doc
    html_content = markdown_to_html(content)
    media = MediaInMemoryUpload(html_content.encode('utf-8'), mimetype='text/html', resumable=True)

    if files:
        # Overwrite existing
        file_id = files[0]['id']
        logger.info(f"Updating existing brief Google Doc: '{filename}' (ID: {file_id})")
        updated_file = service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        return updated_file.get('id')
    else:
        # Create new Google Doc
        logger.info(f"Uploading new brief Google Doc: '{filename}'")
        file_metadata = {
            'name': filename,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.document'  # Convert to Google Doc
        }
        new_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return new_file.get('id')

async def run_drive_upload(session: AsyncSession, folder_name: str = DEFAULT_FOLDER_NAME):
    """Generate the markdown news brief and upload it to Google Drive as a Google Doc."""
    try:
        # Get Drive service
        service = get_drive_service()
    except Exception as e:
        logger.error(f"Google Drive initialization failed: {e}. Check credentials/token setup.")
        return

    # Generate Markdown brief
    brief_content = await generate_brief_markdown(session)

    # Determine brief filename based on IST time (no file extension for Google Doc format)
    ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    date_str = ist_now.strftime('%Y-%m-%d')
    if ist_now.hour < 12:
        filename = f"brief_{date_str}_morning"
    else:
        filename = f"brief_{date_str}_evening"

    try:
        folder_id = get_or_create_folder(service, folder_name)
        file_id = upload_brief(service, folder_id, filename, brief_content)
        logger.info(f"Successfully uploaded news brief Google Doc '{filename}' to Google Drive folder '{folder_name}' (File ID: {file_id})")
    except Exception as e:
        logger.error(f"Failed to upload news brief to Google Drive: {e}", exc_info=True)


