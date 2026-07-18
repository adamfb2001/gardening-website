"""Anonymous device registration (spec §6)."""

from fastapi import APIRouter, Request, status

from ..auth import issue_device_token
from ..models import DeviceRegistration

router = APIRouter(prefix="/v1/devices", tags=["devices"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeviceRegistration)
async def register_device(request: Request) -> DeviceRegistration:
    device_id, token, expires_at = issue_device_token(request.app.state.settings)
    return DeviceRegistration(device_id=device_id, token=token, expires_at=expires_at)
