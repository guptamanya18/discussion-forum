from app.core.exceptions import BadRequestException, ForbiddenException

VALID_ROLES = {"member", "moderator", "admin"}


def validate_role(role: str) -> str:

    """
    Normalize and validate user role.

    - Converts role to lowercase and trims spaces
    - Ensures role is one of allowed roles (member, moderator, admin)
    - Raises error if invalid

    Used when creating or updating a user role.
    """

    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise BadRequestException(
            f"Invalid role. Allowed roles: {', '.join(sorted(VALID_ROLES))}"
        )
    return normalized


def ensure_role(current_user, *allowed_roles: str) -> None:
    """
    Ensure current user has one of the allowed roles.

    - Takes current_user and allowed roles
    - Raises ForbiddenException if user role not allowed

    Example:
    ensure_role(user, "admin") → only admin allowed
    ensure_role(user, "admin", "moderator") → both allowed
    """

    if current_user.role not in allowed_roles:
        raise ForbiddenException("Insufficient Permissions")


def ensure_owner_or_staff(current_user, owner_id: int) -> None:
    """
    Allow access if:
    - User is admin → always allowed
    - User is moderator → allowed for ANY resource
    - User is owner → allowed

    Else → Forbidden

    Used for update/edit operations.
    """

    if current_user.role == "admin":
        return
    if current_user.role == "moderator" and current_user.id != owner_id:
        return
    if current_user.id != owner_id:
        raise ForbiddenException("Insufficient Permissions")


def ensure_can_delete(current_user, owner_id: int, owner_role: str) -> None:
    """
    Delete permission rules:

    - Admin → can delete anything
    - Owner → can delete own content
    - Moderator → can delete content of members ONLY
      (cannot delete admin or other moderators' content)

    Else → Forbidden
    """
    if current_user.role == "admin":
        return
    if current_user.id == owner_id:
        return
    if current_user.role == "moderator" and owner_role not in ("admin", "moderator"):
        return
    raise ForbiddenException("Insufficient Permissions")
