"""Admin API routes with permission protection."""
from fastapi import APIRouter, Depends, HTTPException
from backend.services.admin_service import AdminService
from backend.api.auth import get_current_user, require_permission
from backend.services.role_service import RoleService
from backend.services import trend_run_service, trend_run_queue

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _run_status_payload(run: dict | None) -> dict | None:
    """Project a run row to the public status fields, or None."""
    if run is None:
        return None
    return {
        "id": run["id"],
        "run_date": run["run_date"],
        "trigger_type": run["trigger_type"],
        "status": run["status"],
        "current_batch": run["current_batch"],
        "batch_count": run["batch_count"],
        "batch_total": run["batch_total"],
        "batch_completed": run["batch_completed"],
    }



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


@router.get("/trend-run")
async def get_trend_run(current_user: dict = Depends(get_current_user)):
    """Get the current/last trend-run status - requires system_statistics permission."""
    if not RoleService.user_has_permission(current_user["user_id"], "system_statistics"):
        raise HTTPException(status_code=403, detail="Insufficient permissions: system_statistics required")

    run = trend_run_service.get_active_run() or trend_run_service.get_latest_run()
    info = trend_run_service.get_trigger_info()
    return {
        "run": _run_status_payload(run),
        # Kept for backward compatibility: true only in the normal recovery window.
        "manual_trigger_available": info["on_schedule"],
        # A run is active -> the trigger button must be disabled.
        "run_active": info["run_active"],
        # True when now is the normal scheduled window (no confirmation needed).
        "on_schedule": info["on_schedule"],
        # Set when a trigger now would be off-schedule -> drives confirmation prompt.
        "off_schedule_reason": info["off_schedule_reason"],
        # Set when the trigger is blocked (a run is active) -> shown as the reason.
        "disabled_reason": info["disabled_reason"],
    }


@router.post("/trend-run/trigger")
async def trigger_trend_run(current_user: dict = Depends(get_current_user)):
    """Start a manual trend-prediction run - requires system_statistics permission.

    An admin may trigger a run at any time. The only hard block is concurrency:
    if a run is already active the request is rejected with 409 (one run at a
    time). Off-schedule triggering (weekend / before 17:00 / already ran today)
    is allowed; the frontend gathers explicit confirmation before calling this.
    """
    if not RoleService.user_has_permission(current_user["user_id"], "system_statistics"):
        raise HTTPException(status_code=403, detail="Insufficient permissions: system_statistics required")

    if trend_run_service.get_active_run() is not None:
        raise HTTPException(status_code=409, detail="A trend-prediction run is already in progress")

    run_id = trend_run_queue.start_run("manual")
    run = trend_run_service.get_latest_run()
    return {"run": _run_status_payload(run), "run_id": run_id}
