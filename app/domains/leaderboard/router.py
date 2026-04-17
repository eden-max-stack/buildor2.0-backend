from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from app.infrastructure.supabase_client import supabase

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

class LeaderboardUser(BaseModel):
    user_id: str
    rank: int
    name: str
    username: str
    score: float
    solved: int
    avatar: str
    trend: str = "same" # You can calculate this later based on historical data

@router.get("/", response_model=List[LeaderboardUser])
def get_leaderboard(category: str = Query("ALL", description="Tag name or ALL")):
    try:
        if category == "ALL":
            # Global: Sum all scores per user
            # FIX 1: Ask for 'email' instead of 'username'
            skills_res = supabase.table("student_category_skills").select("user_id, score, total_solved, users(full_name, email, avatar_url)").execute()
            
            user_totals = {}
            for row in skills_res.data:
                uid = row["user_id"]
                if uid not in user_totals:
                    # Safely handle missing user data
                    user_info = row.get("users") or {"full_name": "Unknown", "email": "unknown@domain.com", "avatar_url": ""}
                    
                    # Create a pseudo-username from the email (e.g. 'john.doe@gmail.com' -> 'john.doe')
                    raw_email = user_info.get("email", "unknown")
                    pseudo_username = raw_email.split("@")[0] if "@" in raw_email else "unknown"
                    
                    user_totals[uid] = {
                        "user_id": uid,
                        "name": user_info.get("full_name", "Unknown"),
                        "username": pseudo_username,
                        "avatar": user_info.get("avatar_url") or ("https://api.dicebear.com/7.x/avataaars/svg?seed=" + uid),
                        "score": 0.0,
                        "solved": 0
                    }
                user_totals[uid]["score"] += float(row["score"])
                user_totals[uid]["solved"] += int(row["total_solved"])
                
            sorted_users = sorted(list(user_totals.values()), key=lambda x: x["score"], reverse=True)
            
        else:
            # Category Specific
            # FIX 1: Ask for 'email' instead of 'username'
            skills_res = supabase.table("student_category_skills").select("user_id, score, total_solved, users(full_name, email, avatar_url)").eq("tag_name", category).execute()
            
            user_totals = []
            for row in skills_res.data:
                uid = row["user_id"] # FIX 2: Define uid here!
                user_info = row.get("users") or {"full_name": "Unknown", "email": "unknown@domain.com", "avatar_url": ""}
                
                # Create pseudo-username
                raw_email = user_info.get("email", "unknown")
                pseudo_username = raw_email.split("@")[0] if "@" in raw_email else "unknown"
                    
                # FIX 3: Use .append() since user_totals is a list here
                user_totals.append({ 
                    "user_id": uid,
                    "name": user_info.get("full_name", "Unknown"), 
                    "username": pseudo_username,
                    "avatar": user_info.get("avatar_url") or ("https://api.dicebear.com/7.x/avataaars/svg?seed=" + uid),
                    "score": float(row["score"]),
                    "solved": int(row["total_solved"])
                })
                
            sorted_users = sorted(user_totals, key=lambda x: x["score"], reverse=True)

        # Assign ranks
        results = []
        for index, user in enumerate(sorted_users):
            user["rank"] = index + 1
            user["trend"] = "up" if index < 3 else "same" # Placeholder logic
            results.append(user)
            
        return results[:100] # Return top 100

    except Exception as e:
        print(f"Leaderboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))