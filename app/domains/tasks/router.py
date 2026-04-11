from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.domains.profiles.models import get_current_user
from app.infrastructure.supabase_client import supabase

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


# ============================================
# PYDANTIC MODELS
# ============================================

class TaskCreatePayload(BaseModel):
    class_id: str
    assigned_to_user_id: str
    task_type: str  # "QUIZ" or "CUSTOM"
    reference_id: Optional[str] = None
    due_date: Optional[str] = None


class TaskUpdatePayload(BaseModel):
    status: Optional[str] = None
    due_date: Optional[str] = None
    task_type: Optional[str] = None


# ============================================
# ENDPOINTS
# ============================================

@router.post("/")
async def create_task(payload: TaskCreatePayload, current_user=Depends(get_current_user)):
    """Create a new task for a student in a class. Only trainers should do this."""
    try:
        # Verify the current user is the trainer of this class
        class_res = supabase.table("classes").select("trainer_id").eq("class_id", payload.class_id).execute()
        if not class_res.data:
            raise HTTPException(status_code=404, detail="Class not found")
        if class_res.data[0]["trainer_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Only the class trainer can create tasks")

        insert_data = {
            "class_id": payload.class_id,
            "assigned_to_user_id": payload.assigned_to_user_id,
            "task_type": payload.task_type,
        }
        if payload.reference_id:
            insert_data["reference_id"] = payload.reference_id
        if payload.due_date:
            insert_data["due_date"] = payload.due_date

        res = supabase.table("tasks").insert(insert_data).execute()

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create task")

        return {"message": "Task created", "task": res.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail="Error creating task")


@router.put("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdatePayload, current_user=Depends(get_current_user)):
    """Update a task's status or due date."""
    try:
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return {"message": "Nothing to update"}

        res = supabase.table("tasks").update(update_data).eq("task_id", task_id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Task not found")

        return {"message": "Task updated", "task": res.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail="Error updating task")


@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user=Depends(get_current_user)):
    """Delete a task."""
    try:
        res = supabase.table("tasks").delete().eq("task_id", task_id).execute()
        return {"message": "Task deleted"}
    except Exception as e:
        print(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail="Error deleting task")
