"""CAPTCHA service for generating and verifying captchas."""
import random
import string
import io
import base64
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont

DB_PATH = Path(__file__).parent.parent / "watchlist.db"
CAPTCHA_EXPIRY_MINUTES = 5
CAPTCHA_LENGTH = 6


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_code(length: int = CAPTCHA_LENGTH) -> str:
    """Generate a random CAPTCHA code avoiding ambiguous characters."""
    chars = string.ascii_uppercase.replace("O", "").replace("I", "").replace("L", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choice(chars) for _ in range(length))


def create_captcha_image(code: str) -> str:
    """Create a CAPTCHA image and return as base64 string."""
    width, height = 150, 50
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except:
        font = ImageFont.load_default()

    # Draw text with slight rotation
    x_start = 15
    for i, char in enumerate(code):
        angle = random.randint(-15, 15)
        char_x = x_start + i * 22 + random.randint(-3, 3)
        char_y = random.randint(5, 15)
        draw.text((char_x, char_y), char, fill="black", font=font)

    # Add some noise lines
    for _ in range(3):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill="gray", width=1)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


class CaptchaService:
    """Service for CAPTCHA operations."""

    @staticmethod
    def create_captcha() -> dict:
        """Create a new CAPTCHA. Returns dict with id, image (base64), and code."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            code = generate_code()
            cursor.execute(
                "INSERT INTO captchas (code, created_at) VALUES (?, ?)",
                (code, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            captcha_id = cursor.lastrowid
            image_base64 = create_captcha_image(code)
            return {
                "id": captcha_id,
                "image": f"data:image/png;base64,{image_base64}",
            }
        finally:
            conn.close()

    @staticmethod
    def verify_captcha(captcha_id: int, code: str) -> bool:
        """Verify a CAPTCHA code. Returns True if valid and not expired."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT code, created_at FROM captchas WHERE id = ?",
                (captcha_id,)
            ).fetchone()

            if not row:
                return False

            # Check expiry
            created_at = datetime.fromisoformat(row["created_at"])
            if datetime.now(timezone.utc) - created_at > timedelta(minutes=CAPTCHA_EXPIRY_MINUTES):
                return False

            # Case-insensitive comparison
            if row["code"].upper() != code.upper():
                return False

            # Invalidate the CAPTCHA (single-use)
            cursor.execute("DELETE FROM captchas WHERE id = ?", (captcha_id,))
            conn.commit()
            return True
        finally:
            conn.close()
