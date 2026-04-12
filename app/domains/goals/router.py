from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.domains.profiles.models import get_current_user # Adjust import path
from app.infrastructure.supabase_client import supabase

# Using a clean /api/goals prefix
router = APIRouter(prefix="/api/goals", tags=["Goals"])

# ============================================
# PYDANTIC MODELS
# ============================================
class GoalCreatePayload(BaseModel):
    class_id: str
    title: str
    target_date: Optional[date] = None
    material_ids: List[str] # List of materials the user wants to complete for this goal

# ============================================
# ENDPOINTS
# ============================================

@router.get("/")
async def get_my_goals(limit: int = Query(10, ge=1, le=50), current_user = Depends(get_current_user)):
    """Get top N learning plan goals by target_date for the current user."""
    user_id = current_user.id
    try:
        # Fetch goals
        res = supabase.table("learning_plan_goals").select(
            "goal_id, title, target_date, class_id, classes(title)"
        ).eq("user_id", user_id).order("target_date", desc=False).limit(limit).execute()

        goals = []
        for g in (res.data or []):
            # Check completion status via goal_items
            items_res = supabase.table("goal_items").select(
                "material_id, is_completed"
            ).eq("goal_id", g["goal_id"]).execute()

            total = len(items_res.data) if items_res.data else 0
            completed = sum(1 for i in (items_res.data or []) if i.get("is_completed"))

            goals.append({
                "goal_id": g["goal_id"],
                "title": g["title"],
                "target_date": g["target_date"],
                "class_id": g["class_id"],
                "class_title": g["classes"]["title"] if g.get("classes") else None,
                "total_items": total,
                "completed_items": completed,
            })

        return goals

    except Exception as e:
        print(f"Error fetching goals: {e}")
        raise HTTPException(status_code=500, detail="Error fetching learning goals")


@router.post("/")
async def create_goal(payload: GoalCreatePayload, current_user = Depends(get_current_user)):
    """Create a new learning goal and attach specific materials to it."""
    user_id = current_user.id
    try:
        # 1. Insert the parent Goal record
        goal_data = {
            "user_id": user_id,
            "class_id": payload.class_id,
            "title": payload.title,
        }
        
        # Only add target_date if it was provided
        if payload.target_date:
            goal_data["target_date"] = payload.target_date.isoformat()

        goal_res = supabase.table("learning_plan_goals").insert(goal_data).execute()
        
        if not goal_res.data:
            raise ValueError("Failed to insert goal record")
            
        goal_id = goal_res.data[0]["goal_id"]

        # 2. Insert the Goal Items (the materials tied to this goal)
        if payload.material_ids:
            items_data = [
                {
                    "goal_id": goal_id,
                    "material_id": mat_id,
                    "is_completed": False
                }
                for mat_id in payload.material_ids
            ]
            supabase.table("goal_items").insert(items_data).execute()

        return {"message": "Goal created successfully", "goal_id": goal_id}

    except Exception as e:
        print(f"Error creating goal: {e}")
        raise HTTPException(status_code=500, detail="Error creating learning goal")
    
@router.put("/{goal_id}/complete", status_code=200)
async def complete_goal(goal_id: str, current_user = Depends(get_current_user)):
    """Mark all items in a goal as completed."""
    user_id = current_user.id
    try:
        # 1. Verify ownership
        goal_res = supabase.table("learning_plan_goals").select("user_id").eq("goal_id", goal_id).execute()
        if not goal_res.data:
            raise HTTPException(status_code=404, detail="Goal not found")
            
        if str(goal_res.data[0]["user_id"]) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized to modify this goal")

        # 2. Update all goal items to be completed
        res = supabase.table("goal_items").update({"is_completed": True}).eq("goal_id", goal_id).execute()

        return {"message": "Goal marked as complete"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing goal: {e}")
        raise HTTPException(status_code=500, detail="Error completing goal")    