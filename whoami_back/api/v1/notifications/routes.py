from typing import Dict, List

from fastapi import APIRouter, Body, Depends

from whoami_back.api.v1.notifications import base_url, commands
from whoami_back.api.v1.users.commands import get_current_active_user

router = APIRouter(prefix=base_url, tags=["notifications"])


@router.get("")
async def get_notifications(user: Dict = Depends(get_current_active_user)):
    """
    Get notifications of the given user.
    Return 10 latest notifications (including read ones) if unread is less than
    10 OR return all unread notifications if unreads are more than 10.
    """
    notifications = await commands.get_latest_notifications(user["id"])

    return {"notifications": notifications}


@router.patch("/mark-as-read")
async def mark_notifications_read(
    notification_ids: List = Body(..., embed=True),
    *,
    user: Dict = Depends(get_current_active_user),
):
    await commands.mark_notifications_read(user["id"], notification_ids)


@router.patch("/{notification_id}")
async def update_notification_action(
    notification_id: str,
    *,
    new_action_id: str = Body(..., embed=True),
    user: Dict = Depends(get_current_active_user),
):
    updated_notification = await commands.update_notification_action(
        user["id"], notification_id, new_action_id
    )

    return {"updated_notification": updated_notification}


def add_router(app):
    app.include_router(router)
