"""Cloudinary image upload boundary for AUTO-MAIL assets."""

import os

import cloudinary
import cloudinary.uploader


POSTER_FOLDER = "automail/posters"
BACKGROUND_FOLDER = "automail/backgrounds"


class AssetServiceError(Exception):
    """Raised when an external asset operation cannot be completed."""


class InvalidAssetError(AssetServiceError):
    """Raised when an uploaded file is not a usable image."""


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


def upload_image(file_storage, folder):
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
    return secure_url


def upload_poster(file_storage):
    """Upload a poster to AUTO-MAIL's Cloudinary poster folder."""
    return upload_image(file_storage, POSTER_FOLDER)


def upload_background(file_storage):
    """Upload a background image to AUTO-MAIL's Cloudinary background folder."""
    return upload_image(file_storage, BACKGROUND_FOLDER)
