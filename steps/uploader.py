"""Upload video to YouTube using YouTube Data API v3."""
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = Path(__file__).parent.parent / "token.json"
CLIENT_SECRET_PATH = Path(__file__).parent.parent / "client_secret.json"


def get_youtube_service():
    """Authenticate and return YouTube API service."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: Path | None = None,
    privacy: str = "private",
    publish_at: str | None = None,
) -> str:
    """Upload video to YouTube, return video ID.

    publish_at: ISO 8601 datetime string (e.g. '2026-03-30T09:00:00Z')
                If set, video is uploaded as private and auto-published at that time.
    """
    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "17",  # Sports
        },
        "status": {
            "privacyStatus": "private" if publish_at else privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Schedule for future publishing
    if publish_at:
        body["status"]["publishAt"] = publish_at

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = request.execute()
    video_id = response["id"]

    # Set thumbnail if provided
    if thumbnail_path and thumbnail_path.exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
        ).execute()

    return video_id
