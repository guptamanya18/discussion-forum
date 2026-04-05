from app.core.exceptions import BadRequestException, ForbiddenException

VALID_ROLES = {"member", "moderator", "admin"}


def validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise BadRequestException(
            f"Invalid role. Allowed roles: {', '.join(sorted(VALID_ROLES))}"
        )
    return normalized


def ensure_role(current_user, *allowed_roles: str) -> None:
    if current_user.role not in allowed_roles:
        raise ForbiddenException("Insufficient Permissions")


def ensure_owner_or_staff(current_user, owner_id: int) -> None:
    if current_user.role == "admin":
        return
    if current_user.role == "moderator" and current_user.id != owner_id:
        return
    if current_user.id != owner_id:
        raise ForbiddenException("Insufficient Permissions")


def ensure_can_delete(current_user, owner_id: int, owner_role: str) -> None:
    """Like ensure_owner_or_staff but moderators cannot delete admin content."""
    if current_user.role == "admin":
        return
    if current_user.id == owner_id:
        return
    if current_user.role == "moderator" and owner_role not in ("admin", "moderator"):
        return
    raise ForbiddenException("Insufficient Permissions")
