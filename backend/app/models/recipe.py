"""Demo recipe model - predefined walkthrough sequences."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class DemoRecipe(SQLModel, table=True):
    __tablename__ = "demo_recipes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspaces.id", index=True)
    name: str
    description: Optional[str] = None
    trigger_phrases: str = Field(default="")  # comma-separated phrases that trigger this recipe
    steps_json: str = Field(default="[]")  # JSON array of step objects
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)  # higher = preferred match
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecipeStep(SQLModel):
    """Schema for a single step inside a recipe."""
    action: str  # navigate, click, type, wait, screenshot, narrate
    target: Optional[str] = None  # CSS selector or URL
    value: Optional[str] = None  # text to type, narration text
    description: Optional[str] = None  # human-readable step description
    wait_ms: int = 1000


class RecipeCreate(SQLModel):
    name: str
    description: Optional[str] = None
    trigger_phrases: Optional[str] = None
    steps_json: str = "[]"
    priority: int = 0


class RecipeRead(SQLModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    trigger_phrases: str
    steps_json: str
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime
