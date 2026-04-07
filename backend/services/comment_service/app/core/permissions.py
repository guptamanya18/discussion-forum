from app.core.exceptions import BadRequestException, ForbiddenException

VALID_ROLES = {"member", "moderator", "admin"}


def validate_role(role: str) -> str:
    """
    Checks if the role name is actually allowed. 
    Just cleans up the text and checks it against our list.
    """
    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise BadRequestException(
            f"Invalid role. Allowed roles: {', '.join(sorted(VALID_ROLES))}"
        )
    return normalized


def ensure_role(current_user, *allowed_roles: str) -> None:
    """
    Kick the user out if they don't have the right job title (role).
    Used for simple 'Admin only' checks.
    """
    if current_user.role not in allowed_roles:
        raise ForbiddenException("Insufficient Permissions")


def ensure_owner_or_staff(current_user, owner_id: int) -> None:
    """
    Logic: You can edit if:
    1. You are an Admin.
    2. You are a Moderator.
    3. You are the person who actually wrote the post.
    """
    if current_user.role == "admin":
        return
    if current_user.role == "moderator" and current_user.id != owner_id:
        return
    if current_user.id != owner_id:
        raise ForbiddenException("Insufficient Permissions")


def ensure_can_delete(current_user, owner_id: int, owner_role: str) -> None:
    """
    Logic for deleting stuff (a bit stricter):
    - Admins: Can delete anything.
    - Owners: Can delete their own stuff.
    - Moderators: Can delete Member posts, but NOT Admin/Mod posts.
    """
    if current_user.role == "admin":
        return
    if current_user.id == owner_id:
        return
    if current_user.role == "moderator" and owner_role not in ("admin", "moderator"):
        return
    raise ForbiddenException("Insufficient Permissions")
