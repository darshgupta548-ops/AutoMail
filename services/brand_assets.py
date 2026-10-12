"""Verified AUTO-MAIL institutional email logo assets in display order."""

TESSERACT_LOGO_URL = "https://res.cloudinary.com/vmt4lznh/image/upload/v1791796132/tess.png"
LOGO_CONFIGURATION = (
    ("SnT", "snt_logo_url", "S&T", "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png"),
    ("Tesseract", "tesseract_logo_url", "Tesseract", TESSERACT_LOGO_URL),
    ("Brahmand", "brahmand_logo_url", "Brahmand", "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png"),
    ("OSAIL", "osail_logo_url", "OSAIL", "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png"),
)
DEFAULT_ORGANIZATION_LOGOS = {field: url for _, field, _, url in LOGO_CONFIGURATION}
