"""
AWS S3 service for transcript TXT file uploads.

Usage:
    from app.services.s3_service import upload_transcript_to_s3
    s3_url = upload_transcript_to_s3(meeting_id=8, text_content="...")

S3 object path: transcripts/{meeting_id}/transcript_{timestamp}.txt
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-import boto3 so the app starts even if boto3 is not installed
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False
    logger.warning("[S3] boto3 not installed — S3 upload disabled. Run: pip install boto3")


def _get_s3_client():
    """Build an S3 client from environment variables via app config."""
    from app.core.config import settings

    if not _BOTO3_AVAILABLE:
        return None

    if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY,
                settings.AWS_REGION, settings.AWS_S3_BUCKET_NAME]):
        logger.warning("[S3] AWS credentials not fully configured — skipping upload.")
        return None

    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def upload_transcript_to_s3(meeting_id: int, text_content: str) -> Optional[str]:
    """
    Upload a transcript TXT file to S3.

    Args:
        meeting_id:    The meeting ID (used in the S3 key path).
        text_content:  The full transcript text (UTF-8, Hindi/Devanagari safe).

    Returns:
        The S3 object URL on success, or None on failure.
        Failures are logged but never raised — existing functionality is unaffected.
    """
    client = _get_s3_client()
    if client is None:
        return None

    from app.core.config import settings

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"transcripts/{meeting_id}/transcript_{timestamp}.txt"

    try:
        client.put_object(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            Key=s3_key,
            Body=text_content.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"[S3] Uploaded transcript for meeting {meeting_id}: {url}")
        return url

    except Exception as e:
        # Never let S3 errors break transcript generation
        logger.error(f"[S3] Upload failed for meeting {meeting_id}: {e}")
        return None
