from datetime import datetime
from pydantic import BaseModel, Field


# ── Classification Category ──

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None
    category_type: str = "business"
    description: str | None = None
    keywords: str | None = None
    regulatory_ref: str | None = None
    version: str = "v1.0"
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None
    category_type: str | None = None
    description: str | None = None
    keywords: str | None = None
    regulatory_ref: str | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    category_type: str
    description: str | None = None
    keywords: str | None = None
    regulatory_ref: str | None = None
    version: str
    sort_order: int
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryTreeNode(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    category_type: str
    children_count: int = 0


# ── Tiering Rule ──

class TieringRuleCreate(BaseModel):
    tier_level: str = Field(min_length=2, max_length=10)
    tier_name: str = Field(min_length=1, max_length=50)
    rule_type: str = "keyword"
    rule_content: str
    priority: int = 0
    regulatory_basis: str | None = None
    version: str = "v1.0"


class TieringRuleUpdate(BaseModel):
    tier_level: str | None = Field(default=None, min_length=2, max_length=10)
    tier_name: str | None = Field(default=None, min_length=1, max_length=50)
    rule_type: str | None = None
    rule_content: str | None = None
    priority: int | None = None
    regulatory_basis: str | None = None
    is_active: bool | None = None


class TieringRuleResponse(BaseModel):
    id: int
    tier_level: str
    tier_name: str
    rule_type: str
    rule_content: str
    priority: int
    regulatory_basis: str | None = None
    version: str
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
