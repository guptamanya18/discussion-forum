import logging
from fastapi import APIRouter, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import ForgotPasswordRequest, ResetPasswordRequest
from app.database import get_db
from app.services.auth_service import authenticate_user
from app.core.security import create_access_token,create_reset_token, verify_reset_token,hash_password
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException, NotAuthorizedException, BadRequestException
from app.core.email import send_reset_email
from app.models.user import User
from sqlalchemy import select

logger = logging.getLogger("user_service.auth")
router = APIRouter(tags=["Auth"])

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    db_user = await authenticate_user(username, password, db)

    if not db_user:
        raise NotAuthorizedException("Invalid credentials")

    if db_user.is_active == 0:
        raise NotAuthorizedException("Your account has been deactivated by an admin")

    token = create_access_token(data={"sub": str(db_user.id)})
    logger.info("User '%s' logged in successfully", username)

    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar": current_user.avatar,
        "name": current_user.name,
    }

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db:AsyncSession=Depends(get_db),
):
    # Always return the same message whether email exists or not
    # (prevents email enumeration attacks)
    generic_msg = "If an account with that email exists, a reset link has been sent."

    result=await db.execute(select(User).where(User.email==body.email))
    user=result.scalars().first()

    if not user:
        return {"message": generic_msg}
    
    token=create_reset_token(user.id)
    send_reset_email(user.email, user.username, token)

    return {"message": generic_msg}

@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession=Depends(get_db),
):
    user_id=verify_reset_token(body.token)

    if user_id is None:
        raise BadRequestException("Invalid or expired reset token")
    
    result=await db.execute(select(User).where(User.id==user_id))
    user=result.scalars().first()

    if not user:
        raise NotFoundException("User not found")
    
    user.hashed_password=hash_password(body.new_password)
    await db.commit()

    return {"message":"Password reset successful"}
