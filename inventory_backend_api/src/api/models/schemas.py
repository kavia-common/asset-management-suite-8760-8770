from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, EmailStr


class RoleName(str, Enum):
    """System role names."""

    admin = "admin"
    user = "user"


class UserStatus(str, Enum):
    """User account status."""

    active = "active"
    disabled = "disabled"


class AssetType(str, Enum):
    """Types of managed assets/devices."""

    laptop = "laptop"
    desktop = "desktop"
    monitor = "monitor"
    phone = "phone"
    accessory = "accessory"
    other = "other"


class AllocationStatus(str, Enum):
    """Lifecycle status for allocations and transfers."""

    active = "active"
    returned = "returned"
    pending_transfer = "pending_transfer"
    transferred = "transferred"
    cancelled = "cancelled"


class AuditAction(str, Enum):
    """Audit log action types."""

    create = "create"
    update = "update"
    delete = "delete"
    allocate = "allocate"
    return_asset = "return"
    transfer_request = "transfer_request"
    transfer_approve = "transfer_approve"
    transfer_reject = "transfer_reject"
    login = "login"


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: Literal["bearer"] = Field("bearer", description="Token type")


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str = Field(..., description="Username")
    password: str = Field(..., min_length=6, description="Password")


class UserCreateRequest(BaseModel):
    """Create user request."""

    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., min_length=1, max_length=120, description="Full display name")
    password: str = Field(..., min_length=6, description="Initial password")
    roles: list[RoleName] = Field(default_factory=lambda: [RoleName.user], description="Assigned roles")


class UserUpdateRequest(BaseModel):
    """Update user request."""

    email: EmailStr | None = Field(None, description="User email")
    full_name: str | None = Field(None, min_length=1, max_length=120, description="Full display name")
    roles: list[RoleName] | None = Field(None, description="Assigned roles")
    status: UserStatus | None = Field(None, description="Account status")


class UserResponse(BaseModel):
    """User response model."""

    id: str = Field(..., description="User id")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email")
    full_name: str = Field(..., description="Full name")
    roles: list[RoleName] = Field(..., description="Roles")
    status: UserStatus = Field(..., description="Status")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")


class AssetCreateRequest(BaseModel):
    """Create asset/device request."""

    asset_tag: str = Field(..., min_length=1, max_length=64, description="Unique asset tag / barcode value")
    serial_number: str | None = Field(None, max_length=128, description="Serial number if available")
    type: AssetType = Field(..., description="Asset type")
    manufacturer: str | None = Field(None, max_length=80, description="Manufacturer")
    model: str | None = Field(None, max_length=80, description="Model")
    description: str | None = Field(None, max_length=500, description="Description/notes")
    location: str | None = Field(None, max_length=120, description="Storage/office location")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional arbitrary metadata")


class AssetUpdateRequest(BaseModel):
    """Update asset/device request."""

    serial_number: str | None = Field(None, max_length=128, description="Serial number")
    manufacturer: str | None = Field(None, max_length=80, description="Manufacturer")
    model: str | None = Field(None, max_length=80, description="Model")
    description: str | None = Field(None, max_length=500, description="Description/notes")
    location: str | None = Field(None, max_length=120, description="Storage/office location")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    active: bool | None = Field(None, description="Whether asset is active")


class AssetResponse(BaseModel):
    """Asset response model."""

    id: str = Field(..., description="Asset id")
    asset_tag: str = Field(..., description="Unique asset tag")
    serial_number: str | None = Field(None, description="Serial number")
    type: AssetType = Field(..., description="Type")
    manufacturer: str | None = Field(None, description="Manufacturer")
    model: str | None = Field(None, description="Model")
    description: str | None = Field(None, description="Description")
    location: str | None = Field(None, description="Location")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    active: bool = Field(..., description="Active flag")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")


class AllocateRequest(BaseModel):
    """Allocate an asset to a user."""

    asset_id: str = Field(..., description="Asset id")
    to_user_id: str = Field(..., description="User id to allocate to")
    notes: str | None = Field(None, max_length=500, description="Notes for allocation")


class ReturnRequest(BaseModel):
    """Return an allocated asset."""

    allocation_id: str = Field(..., description="Allocation id")
    notes: str | None = Field(None, max_length=500, description="Return notes")


class TransferRequestCreate(BaseModel):
    """Request transfer of an active allocation to another user."""

    allocation_id: str = Field(..., description="Allocation id")
    to_user_id: str = Field(..., description="New assignee user id")
    notes: str | None = Field(None, max_length=500, description="Transfer notes")


class TransferDecisionRequest(BaseModel):
    """Approve/reject a transfer request."""

    decision: Literal["approve", "reject"] = Field(..., description="Decision")
    notes: str | None = Field(None, max_length=500, description="Decision notes")


class AllocationResponse(BaseModel):
    """Allocation/transfer record response."""

    id: str = Field(..., description="Allocation id")
    asset_id: str = Field(..., description="Asset id")
    from_user_id: str | None = Field(None, description="Previous user id (for transfers)")
    to_user_id: str = Field(..., description="Current user id")
    status: AllocationStatus = Field(..., description="Status")
    notes: str | None = Field(None, description="Notes")
    requested_by: str | None = Field(None, description="User id who requested transfer")
    approved_by: str | None = Field(None, description="User id who approved transfer")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: str = Field(..., description="Audit id")
    actor_user_id: str | None = Field(None, description="Actor user id (if any)")
    action: AuditAction = Field(..., description="Action")
    entity_type: str = Field(..., description="Entity type e.g. user, asset, allocation")
    entity_id: str | None = Field(None, description="Entity id")
    detail: dict[str, Any] = Field(default_factory=dict, description="Action detail payload")
    created_at: datetime = Field(..., description="Timestamp")
