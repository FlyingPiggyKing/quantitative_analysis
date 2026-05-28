"""Admin API routes with permission protection."""
from fastapi import APIRouter, Depends, HTTPException
from backend.services.admin_service import AdminService
from backend.api.auth import get_current_user, require_permission
from backend.services.role_service import RoleService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get admin statistics - requires system_statistics permission."""
    if not RoleService.user_has_permission(current_user["user_id"], "system_statistics"):
        raise HTTPException(status_code=403, detail="Insufficient permissions: system_statistics required")
    return AdminService.get_stats()


@router.get("/permissions")
async def check_permissions(
    permission: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if current user has a specific permission."""
    has_permission = RoleService.user_has_permission(current_user["user_id"], permission)
    return {"permission": permission, "has_permission": has_permission}
