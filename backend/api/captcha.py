"""CAPTCHA API routes."""
from fastapi import APIRouter
from backend.services.captcha_service import CaptchaService

router = APIRouter(prefix="/api/captcha", tags=["captcha"])


@router.get("")
async def get_captcha():
    """Get a new CAPTCHA image."""
    result = CaptchaService.create_captcha()
    return result
