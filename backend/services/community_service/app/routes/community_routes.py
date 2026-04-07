"""This file handles all the web requests related to communities."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.community import Community, generate_slug
from app.models.community_member import CommunityMember
from app.models.user import User
from app.schemas.community import ( CommunityCreate, CommunityResponse, CommunityUpdate, MemberResponse,)
from app.schemas.community import CommunityListPaginated

from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException, DuplicateException
from app.kafka_producer import kafka_producer

logger = logging.getLogger("community_service.routes")

router = APIRouter(prefix="/communities", tags=["Communities"])


async def _resolve_community(identifier: str, db: AsyncSession) -> Community:
    """Resolve community by ID (numeric) or slug."""
    if identifier.isdigit():
        result = await db.execute(select(Community).where(Community.id == int(identifier)))
    else:
        result = await db.execute(select(Community).where(Community.slug == identifier))
    community = result.scalars().first()
    if not community:
        raise NotFoundException("Community not found")
    return community


@router.post("", response_model=CommunityResponse)
async def create_community(
    body: CommunityCreate,
    current_user:User=Depends(get_current_user),
    db:AsyncSession=Depends(get_db),
):

    existing=await db.execute(
        select(Community).where(Community.name==body.name)
    )

    if existing.scalars().first():
        raise DuplicateException("Community name already exists")

    slug = generate_slug(body.name)
    # Ensure slug uniqueness
    slug_exists = await db.execute(select(Community).where(Community.slug == slug))
    counter = 1
    original_slug = slug
    while slug_exists.scalars().first():
        slug = f"{original_slug}-{counter}"
        counter += 1
        slug_exists = await db.execute(select(Community).where(Community.slug == slug))

    community=Community(
        name=body.name,
        slug=slug,
        description=body.description,
        created_by=current_user.id,
    )

    db.add(community)
    await db.flush()

    membership=CommunityMember(
        user_id=current_user.id,
        community_id=community.id,
        role="moderator",
    )

    db.add(membership)
    await db.commit()

    return{
        "id": community.id,
        "name": community.name,
        "slug": community.slug,
        "description": community.description,
        "created_by": community.created_by,
        "created_at": community.created_at,
        "member_count": 1,
    }

@router.get("/my")
async def my_communities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return communities the user owns and communities the user is a member of."""
    member_counts = (
        select(
            CommunityMember.community_id.label("community_id"),
            func.count(CommunityMember.id).label("member_count"),
        )
        .group_by(CommunityMember.community_id)
        .subquery()
    )

    # Communities created by the user
    owned_q = (
        select(Community, func.coalesce(member_counts.c.member_count, 0).label("member_count"))
        .outerjoin(member_counts, member_counts.c.community_id == Community.id)
        .where(Community.created_by == current_user.id)
        .order_by(Community.created_at.desc())
    )
    owned_rows = (await db.execute(owned_q)).all()

    # Communities the user is a member of (but did NOT create)
    member_q = (
        select(Community, func.coalesce(member_counts.c.member_count, 0).label("member_count"))
        .outerjoin(member_counts, member_counts.c.community_id == Community.id)
        .join(CommunityMember, CommunityMember.community_id == Community.id)
        .where(CommunityMember.user_id == current_user.id, Community.created_by != current_user.id)
        .order_by(Community.created_at.desc())
    )
    member_rows = (await db.execute(member_q)).all()

    def _to_dict(c, mc):
        return {
            "id": c.id, "name": c.name, "slug": c.slug, "description": c.description,
            "created_by": c.created_by, "created_at": c.created_at.isoformat(),
            "member_count": mc,
        }

    return {
        "owned": [_to_dict(c, mc) for c, mc in owned_rows],
        "member_of": [_to_dict(c, mc) for c, mc in member_rows],
    }


@router.get("", response_model=CommunityListPaginated)
async def list_communities(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    member_counts = (
        select(
            CommunityMember.community_id.label("community_id"),
            func.count(CommunityMember.id).label("member_count"),
        )
        .group_by(CommunityMember.community_id)
        .subquery()
    )

    query = (
        select(
            Community,
            func.coalesce(member_counts.c.member_count, 0).label("member_count"),
        )
        .outerjoin(member_counts, member_counts.c.community_id == Community.id)
    )

    if search:
        query = query.where(Community.name.ilike(f"%{search}%"))

    # Total count
    count_q = select(func.count()).select_from(Community)
    if search:
        count_q = count_q.where(Community.name.ilike(f"%{search}%"))
    total = (await db.execute(count_q)).scalar()

    query = query.order_by(Community.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(query)).all()

    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "created_by": c.created_by,
                "created_at": c.created_at,
                "member_count": member_count,
            }
            for c, member_count in rows
        ],
        "total": total,
    }


@router.get("/{community_id}", response_model=CommunityResponse)
async def get_community(community_id: str, db: AsyncSession = Depends(get_db)):
    community = await _resolve_community(community_id, db)

    member_count = (
        await db.execute(
            select(func.count(CommunityMember.id))
            .where(CommunityMember.community_id == community.id)
        )
    ).scalar()

    return {
        "id": community.id,
        "name": community.name,
        "slug": community.slug,
        "description": community.description,
        "created_by": community.created_by,
        "created_at": community.created_at,
        "member_count": member_count,
    }


@router.put("/{community_id}", response_model=CommunityResponse)
async def update_community(
    community_id: str,
    body: CommunityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    community = await _resolve_community(community_id, db)

    # Only creator, community moderator, or global admin/mod can edit
    if current_user.role not in ("admin", "moderator") and current_user.id != community.created_by:
        # Check if user is a community-level moderator
        mem = (
            await db.execute(
                select(CommunityMember).where(
                    CommunityMember.community_id == community.id,
                    CommunityMember.user_id == current_user.id,
                    CommunityMember.role == "moderator",
                )
            )
        ).scalars().first()
        if not mem:
            raise ForbiddenException("Not authorized")

    if body.name is not None:
        existing = await db.execute(
            select(Community)
            .where(Community.name == body.name)
            .where(Community.id != community.id)
        )
        if existing.scalars().first():
            raise DuplicateException("Community name already exists")
        community.name = body.name
        # Regenerate slug from new name
        new_slug = generate_slug(body.name)
        slug_exists = await db.execute(
            select(Community).where(Community.slug == new_slug, Community.id != community.id)
        )
        counter = 1
        original_slug = new_slug
        while slug_exists.scalars().first():
            new_slug = f"{original_slug}-{counter}"
            counter += 1
            slug_exists = await db.execute(
                select(Community).where(Community.slug == new_slug, Community.id != community.id)
            )
        community.slug = new_slug
    if body.description is not None:
        community.description = body.description

    await db.commit()

    member_count = (
        await db.execute(
            select(func.count(CommunityMember.id))
            .where(CommunityMember.community_id == community.id)
        )
    ).scalar()

    return {
        "id": community.id,
        "name": community.name,
        "slug": community.slug,
        "description": community.description,
        "created_by": community.created_by,
        "created_at": community.created_at,
        "member_count": member_count,
    }


@router.delete("/{community_id}")
async def delete_community(
    community_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    community = await _resolve_community(community_id, db)

    if current_user.role not in ("admin",) and current_user.id != community.created_by:
        raise ForbiddenException("Not authorized — only creator or admin")

    # Notify all members before deleting
    members = (await db.execute(
        select(CommunityMember).where(CommunityMember.community_id == community.id)
    )).scalars().all()
    for member in members:
        if member.user_id != current_user.id:
            await kafka_producer.send("community-events", {
                "event": "community_deleted",
                "user_id": member.user_id,
                "type": "community_deleted",
                "message": f"The community '{community.name}' has been deleted",
                "reference_id": community.id,
            })

    await db.delete(community)
    await db.commit()
    return {"message": "Community deleted successfully"}


# ── Membership (Join / Leave) ─────────────────────────────────────


@router.post("/{community_id}/join")
async def join_community(
    community_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    community = await _resolve_community(community_id, db)

    existing = (
        await db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if existing:
        raise BadRequestException("Already a member")

    membership = CommunityMember(
        user_id=current_user.id,
        community_id=community.id,
        role="member",
    )
    db.add(membership)
    await db.commit()
    if community.created_by != current_user.id:
        await kafka_producer.send("community-events", {
            "event": "community_joined",
            "user_id": community.created_by,
            "type": "community_join",
            "message": f"{current_user.username} joined your community '{community.name}'",
            "reference_id": community.id,
        })
    return {"message": f"Joined community '{community.name}'"}


@router.delete("/{community_id}/leave")
async def leave_community(
    community_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    community = await _resolve_community(community_id, db)

    membership = (
        await db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if not membership:
        raise BadRequestException("Not a member")

    if community.created_by == current_user.id:
        raise BadRequestException("Community owner cannot leave. Delete the community instead.")

    await db.delete(membership)
    await db.commit()

    if community.created_by != current_user.id:
        await kafka_producer.send("community-events", {
            "event": "community_left",
            "user_id": community.created_by,
            "type": "community_leave",
            "message": f"{current_user.username} left your community '{community.name}'",
            "reference_id": community.id,
        })
    return {"message": "Left community"}


@router.get("/{community_id}/members", response_model=list[MemberResponse])
async def list_members(
    community_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    community = await _resolve_community(community_id, db)

    result = await db.execute(
        select(CommunityMember, User.username, User.avatar)
        .join(User, User.id == CommunityMember.user_id)
        .where(CommunityMember.community_id == community.id)
        .order_by(CommunityMember.joined_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "id": mem.id,
            "user_id": mem.user_id,
            "username": username,
            "avatar": avatar,
            "role": mem.role,
            "joined_at": mem.joined_at,
        }
        for mem, username, avatar in rows
    ]


# ── Community Moderation (promote member → moderator) ─────────────


@router.put("/{community_id}/members/{user_id}/role")
async def change_member_role(
    community_id: str,
    user_id: int,
    role: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if role not in ("member", "moderator"):
        raise BadRequestException("Role must be 'member' or 'moderator'")

    community = await _resolve_community(community_id, db)

    # Only community creator or global admin can change roles
    if current_user.role != "admin" and current_user.id != community.created_by:
        raise ForbiddenException("Only community creator or admin can change roles")

    membership = (
        await db.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == user_id,
            )
        )
    ).scalars().first()
    if not membership:
        raise NotFoundException("User is not a member of this community")

    membership.role = role
    await db.commit()

    if user_id != current_user.id:
        await kafka_producer.send("community-events", {
            "event": "member_role_changed",
            "user_id": user_id,
            "type": "role_change",
            "message": f"Your role in '{community.name}' was changed to '{role}'",
            "reference_id": community.id,
        })
    return {"message": f"User {user_id} role changed to '{role}' in community {community.id}"}