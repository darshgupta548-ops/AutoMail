"""Cloudinary image upload boundary for AUTO-MAIL assets."""

import os

import cloudinary
import cloudinary.uploader


POSTER_FOLDER = "automail/posters"
BACKGROUND_FOLDER = "automail/backgrounds"

# Minimum recommended dimensions for background images (desktop email max width is 600px)
MIN_BACKGROUND_WIDTH = 1200
MIN_BACKGROUND_HEIGHT = 800


class AssetServiceError(Exception):
    """Raised when an external asset operation cannot be completed."""


class InvalidAssetError(AssetServiceError):
    """Raised when an uploaded file is not a usable image."""


class BackgroundDimensionWarning(AssetServiceError):
    """Warning raised when background image dimensions are too small."""
    def __init__(self, message, width=None, height=None):
        super().__init__(message)
        self.width = width
        self.height = height


def _configure_cloudinary():
    """Configure Cloudinary from server-side environment variables only."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    if not all((cloud_name, api_key, api_secret)):
        raise AssetServiceError("Cloudinary is not configured.")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


def _validate_image(file_storage):
    if file_storage is None or not file_storage.filename:
        raise InvalidAssetError("An image file is required.")
    if not (file_storage.mimetype or "").startswith("image/"):
        raise InvalidAssetError("Uploaded files must be images.")


def _check_background_dimensions(upload_result):
    """Check if background image dimensions meet minimum recommendations."""
    width = upload_result.get("width")
    height = upload_result.get("height")
    
    if width is None or height is None:
        # Cloudinary didn't return dimensions, skip warning
        return None
    
    if width < MIN_BACKGROUND_WIDTH or height < MIN_BACKGROUND_HEIGHT:
        message = (
            f"Background image dimensions ({width}x{height}) may be too small. "
            f"Recommended minimum: {MIN_BACKGROUND_WIDTH}x{MIN_BACKGROUND_HEIGHT}. "
            f"The image may appear pixelated or fail to cover the intended area."
        )
        return BackgroundDimensionWarning(message, width, height)
    
    return None


def upload_image(file_storage, folder, check_dimensions=False):
    """Upload an image and return its secure Cloudinary URL."""
    _validate_image(file_storage)
    _configure_cloudinary()

    try:
        result = cloudinary.uploader.upload(
            file_storage,
            folder=folder,
            resource_type="image",
        )
    except Exception as error:
        raise AssetServiceError("Image upload failed.") from error

    secure_url = result.get("secure_url") if isinstance(result, dict) else None
    if not isinstance(secure_url, str) or not secure_url.startswith("https://"):
        raise AssetServiceError("Cloudinary did not return a secure image URL.")
    
    # Check dimensions if requested (for background images)
    warning = None
    if check_dimensions and isinstance(result, dict):
        warning = _check_background_dimensions(result)
    
    return secure_url, warning


def upload_poster(file_storage):
    """Upload a poster to AUTO-MAIL's Cloudinary poster folder."""
    return upload_image(file_storage, POSTER_FOLDER, check_dimensions=False)[0]


def upload_background(file_storage):
    """Upload a background image to AUTO-MAIL's Cloudinary background folder."""
    url, warning = upload_image(file_storage, BACKGROUND_FOLDER, check_dimensions=True)
    return url, warning


def delete_cloudinary_asset(public_id):
    """Delete a Cloudinary asset by public ID."""
    _configure_cloudinary()
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        return result.get("result") == "ok"
    except Exception as error:
        raise AssetServiceError(f"Failed to delete Cloudinary asset: {str(error)}") from error


def extract_public_id_from_url(url):
    """Extract Cloudinary public ID from a secure URL."""
    if not url or not isinstance(url, str):
        return None
    # URL format: https://res.cloudinary.com/cloud_name/folder/public_id.ext
    parts = url.split("/")
    if len(parts) >= 2:
        filename = parts[-1]
        # Remove extension
        public_id = filename.rsplit(".", 1)[0] if "." in filename else filename
        # Reconstruct with folder if present
        if "automail/" in url:
            folder_parts = url.split("automail/")[1].split("/")
            if len(folder_parts) > 1:
                return f"automail/{folder_parts[0]}/{public_id}"
        return public_id
    return None
