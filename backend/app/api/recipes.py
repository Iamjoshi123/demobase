"""Demo recipe CRUD and test-run API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.workspace import Workspace
from app.models.recipe import DemoRecipe, RecipeCreate, RecipeRead

router = APIRouter(prefix="/workspaces/{workspace_id}/recipes", tags=["recipes"])


@router.post("", response_model=RecipeRead)
def create_recipe(
    workspace_id: str,
    data: RecipeCreate,
    db: Session = Depends(get_session),
):
    ws = db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    recipe = DemoRecipe(
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        trigger_phrases=data.trigger_phrases or "",
        steps_json=data.steps_json,
        priority=data.priority,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("", response_model=list[RecipeRead])
def list_recipes(workspace_id: str, db: Session = Depends(get_session)):
    return db.exec(
        select(DemoRecipe).where(
            DemoRecipe.workspace_id == workspace_id
        ).order_by(DemoRecipe.priority.desc())
    ).all()


@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(workspace_id: str, recipe_id: str, db: Session = Depends(get_session)):
    recipe = db.get(DemoRecipe, recipe_id)
    if not recipe or recipe.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    workspace_id: str,
    recipe_id: str,
    data: RecipeCreate,
    db: Session = Depends(get_session),
):
    recipe = db.get(DemoRecipe, recipe_id)
    if not recipe or recipe.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe.name = data.name
    recipe.description = data.description
    recipe.trigger_phrases = data.trigger_phrases or ""
    recipe.steps_json = data.steps_json
    recipe.priority = data.priority
    recipe.updated_at = datetime.now(timezone.utc)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}")
def delete_recipe(
    workspace_id: str,
    recipe_id: str,
    db: Session = Depends(get_session),
):
    recipe = db.get(DemoRecipe, recipe_id)
    if not recipe or recipe.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe.is_active = False
    db.add(recipe)
    db.commit()
    return {"status": "deactivated"}
