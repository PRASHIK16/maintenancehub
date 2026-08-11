"""
File validation utilities.
Validates files by magic bytes (file signatures) rather than MIME type
from the client, which can be spoofed.
"""

# Magic byte signatures for allowed file types
MAGIC_SIGNATURES = {
    # Images
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # RIFF....WEBP — check further below
    # Documents
    b"%PDF": "application/pdf",
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "application/msword",  # .doc
    b"PK\x03\x04": "application/zip",  # .docx is a zip
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def validate_file_magic(file_obj):
    """
    Read the first 16 bytes of a file and check against known magic signatures.
    Returns the detected content type, or raises ValueError if not allowed.
    """
    file_obj.seek(0)
    header = file_obj.read(16)
    file_obj.seek(0)

    detected = None
    for magic, ctype in MAGIC_SIGNATURES.items():
        if header[:len(magic)] == magic:
            if magic == b"RIFF" and b"WEBP" in header[4:12]:
                detected = "image/webp"
            elif magic == b"PK\x03\x04":
                # Could be .docx — we accept both
                detected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                detected = ctype
            break

    if detected is None or detected not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"File type not permitted. Allowed types: JPEG, PNG, GIF, WebP, PDF, DOC, DOCX."
        )

    return detected
