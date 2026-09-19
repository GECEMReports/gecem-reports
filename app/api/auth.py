import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.base import TenantModel
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.utils.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if slug exists
    existing = await db.execute(select(TenantModel).where(TenantModel.slug == req.tenant_slug))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Tenant slug already exists")

    # Create tenant
    tenant = TenantModel(name=req.tenant_name, slug=req.tenant_slug)
    db.add(tenant)
    await db.flush()

    # Create user
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "role": user.role,
    })

    return TokenResponse(
        access_token=token,
        tenant_id=tenant.id,
        user_id=user.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
    })

    return TokenResponse(
        access_token=token,
        tenant_id=user.tenant_id,
        user_id=user.id,
    )
