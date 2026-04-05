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
