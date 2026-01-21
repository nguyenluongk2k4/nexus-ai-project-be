"""
Timeline API - Learning Schedule Management
"""

from typing import List, Optional
from uuid import UUID
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db
from modules.auth.api.deps import get_current_user_id


router = APIRouter(prefix="/api/timeline", tags=["timeline"])


# =====================================================
# Pydantic Models
# =====================================================

class TimelineItemResponse(BaseModel):
    id: str
    resourceId: str
    resourceName: str
    resourceType: str
    nodeName: str
    scheduledDate: str
    scheduledTime: Optional[str] = None  # HH:MM format
    deadline: Optional[str]
    priority: str
    status: str
    estimatedTime: Optional[int]  # minutes
    
    class Config:
        from_attributes = True


class TimelineListResponse(BaseModel):
    items: List[TimelineItemResponse]
    stats: dict


class AddTimelineRequest(BaseModel):
    resourceId: str
    scheduledDate: str  # YYYY-MM-DD
    deadline: Optional[str] = None
    priority: str = "medium"


class UpdateTimelineRequest(BaseModel):
    scheduledDate: Optional[str] = None
    scheduledTime: Optional[str] = None  # HH:MM format
    deadline: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


# =====================================================
# API Endpoints
# =====================================================

@router.get("", response_model=TimelineListResponse)
async def get_timeline_items(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all timeline items for current user"""
    
    result = await db.execute(
        text("""
            SELECT 
                ti.id,
                ti.resource_id,
                lr.title as resource_name,
                lr.resource_type,
                COALESCE(tsn.name, 'Unknown') as node_name,
                ti.scheduled_date,
                ti.scheduled_time,
                ti.deadline,
                ti.priority,
                COALESCE(lp.status, 'not_started') as status,
                lr.estimated_duration
            FROM timeline_items ti
            JOIN learning_resources lr ON ti.resource_id = lr.id
            LEFT JOIN template_skill_nodes tsn ON lr.skill_node_id = tsn.id
            LEFT JOIN learning_progress lp ON lp.resource_id = lr.id AND lp.user_id = :user_id
            WHERE ti.user_id = :user_id
            ORDER BY ti.scheduled_date ASC
        """),
        {"user_id": user_id}
    )
    
    rows = result.fetchall()
    
    items = []
    stats = {"total": 0, "not_started": 0, "in_progress": 0, "completed": 0}
    
    for row in rows:
        items.append(TimelineItemResponse(
            id=str(row.id),
            resourceId=str(row.resource_id),
            resourceName=row.resource_name or "Unknown",
            resourceType=row.resource_type or "article",
            nodeName=row.node_name,
            scheduledDate=row.scheduled_date.isoformat() if row.scheduled_date else "",
            scheduledTime=row.scheduled_time,
            deadline=row.deadline.isoformat() if row.deadline else None,
            priority=row.priority or "medium",
            status=row.status or "not_started",
            estimatedTime=row.estimated_duration
        ))
        
        stats["total"] += 1
        status = row.status or "not_started"
        if status in stats:
            stats[status] += 1
    
    return TimelineListResponse(items=items, stats=stats)


@router.post("", response_model=TimelineItemResponse, status_code=201)  
async def add_timeline_item(
    data: AddTimelineRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Add a resource to timeline"""
    
    # Verify resource exists
    resource = await db.execute(
        text("SELECT id, title, resource_type, estimated_duration, skill_node_id FROM learning_resources WHERE id = :id"),
        {"id": data.resourceId}
    )
    res = resource.fetchone()
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Get node name
    node_name = "Unknown"
    if res.skill_node_id:
        node = await db.execute(
            text("SELECT name FROM template_skill_nodes WHERE id = :id"),
            {"id": res.skill_node_id}
        )
        node_row = node.fetchone()
        if node_row:
            node_name = node_row.name
    
    # Parse dates
    scheduled = datetime.strptime(data.scheduledDate, "%Y-%m-%d").date()
    deadline = datetime.strptime(data.deadline, "%Y-%m-%d").date() if data.deadline else None
    
    # Insert timeline item
    result = await db.execute(
        text("""
            INSERT INTO timeline_items (user_id, resource_id, scheduled_date, deadline, priority)
            VALUES (:user_id, :resource_id, :scheduled, :deadline, :priority)
            RETURNING id
        """),
        {
            "user_id": user_id,
            "resource_id": data.resourceId,
            "scheduled": scheduled,
            "deadline": deadline,
            "priority": data.priority
        }
    )
    
    new_id = result.fetchone().id
    await db.commit()
    
    return TimelineItemResponse(
        id=str(new_id),
        resourceId=data.resourceId,
        resourceName=res.title,
        resourceType=res.resource_type or "article",
        nodeName=node_name,
        scheduledDate=data.scheduledDate,
        deadline=data.deadline,
        priority=data.priority,
        status="not_started",
        estimatedTime=res.estimated_duration
    )


@router.put("/{item_id}", response_model=dict)
async def update_timeline_item(
    item_id: str,
    data: UpdateTimelineRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a timeline item"""
    
    # Verify ownership
    existing = await db.execute(
        text("SELECT id FROM timeline_items WHERE id = :id AND user_id = :user_id"),
        {"id": item_id, "user_id": user_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Timeline item not found")
    
    # Build update query dynamically
    updates = []
    params = {"id": item_id}
    
    if data.scheduledDate:
        updates.append("scheduled_date = :scheduled")
        params["scheduled"] = datetime.strptime(data.scheduledDate, "%Y-%m-%d").date()
    
    if data.deadline:
        updates.append("deadline = :deadline")
        params["deadline"] = datetime.strptime(data.deadline, "%Y-%m-%d").date()
    
    if data.priority:
        updates.append("priority = :priority")
        params["priority"] = data.priority
    
    if data.scheduledTime:
        updates.append("scheduled_time = :scheduled_time")
        params["scheduled_time"] = data.scheduledTime
    
    if updates:
        await db.execute(
            text(f"UPDATE timeline_items SET {', '.join(updates)} WHERE id = :id"),
            params
        )
    
    # Update learning_progress status if provided
    if data.status:
        # Get resource_id first
        item = await db.execute(
            text("SELECT resource_id FROM timeline_items WHERE id = :id"),
            {"id": item_id}
        )
        resource_id = item.fetchone().resource_id
        
        # Update or insert learning_progress
        await db.execute(
            text("""
                INSERT INTO learning_progress (user_id, resource_id, status, started_at, completed_at)
                VALUES (:user_id, :resource_id, :status, 
                    CASE WHEN :status = 'in_progress' THEN NOW() ELSE NULL END,
                    CASE WHEN :status = 'completed' THEN NOW() ELSE NULL END)
                ON CONFLICT (user_id, resource_id) DO UPDATE SET
                    status = :status,
                    started_at = CASE WHEN :status = 'in_progress' AND learning_progress.started_at IS NULL THEN NOW() ELSE learning_progress.started_at END,
                    completed_at = CASE WHEN :status = 'completed' THEN NOW() ELSE NULL END,
                    updated_at = NOW()
            """),
            {"user_id": user_id, "resource_id": resource_id, "status": data.status}
        )
    
    await db.commit()
    return {"success": True, "message": "Timeline item updated"}


@router.delete("/{item_id}")
async def delete_timeline_item(
    item_id: str,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a timeline item"""
    
    result = await db.execute(
        text("DELETE FROM timeline_items WHERE id = :id AND user_id = :user_id RETURNING id"),
        {"id": item_id, "user_id": user_id}
    )
    
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Timeline item not found")
    
    await db.commit()
    return {"success": True, "message": "Timeline item deleted"}


@router.get("/resources", response_model=List[dict])
async def get_available_resources(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get learning resources from user's skill tree that are not completed"""
    
    # Try to get resources from user's skill tree first
    result = await db.execute(
        text("""
            SELECT DISTINCT
                lr.id,
                lr.title,
                lr.resource_type,
                lr.platform,
                lr.estimated_duration,
                usn.name as node_name,
                COALESCE(lp.status, 'not_started') as status
            FROM learning_resources lr
            -- Join to template nodes
            JOIN template_skill_nodes tsn ON lr.skill_node_id = tsn.id
            -- Join to user's skill nodes (that reference the template)
            JOIN user_skill_nodes usn ON usn.original_node_id = tsn.id
            -- Join to user's skill tree
            JOIN user_skill_trees ust ON usn.tree_id = ust.id AND ust.user_id = :user_id
            -- Left join to check learning progress
            LEFT JOIN learning_progress lp ON lp.resource_id = lr.id AND lp.user_id = :user_id
            WHERE 
                COALESCE(lp.status, 'not_started') != 'completed'
                AND usn.status != 'completed'
            ORDER BY usn.name, lr.title
            LIMIT 50
        """),
        {"user_id": user_id}
    )
    
    rows = result.fetchall()
    
    # Fallback: Get resources already in user's timeline
    if not rows:
        result = await db.execute(
            text("""
                SELECT DISTINCT
                    lr.id,
                    lr.title,
                    lr.resource_type,
                    lr.platform,
                    lr.estimated_duration,
                    COALESCE(tsn.name, 'General') as node_name,
                    COALESCE(lp.status, 'not_started') as status
                FROM timeline_items ti
                JOIN learning_resources lr ON ti.resource_id = lr.id
                LEFT JOIN template_skill_nodes tsn ON lr.skill_node_id = tsn.id
                LEFT JOIN learning_progress lp ON lp.resource_id = lr.id AND lp.user_id = :user_id
                WHERE ti.user_id = :user_id
                    AND COALESCE(lp.status, 'not_started') != 'completed'
                ORDER BY node_name, title
                LIMIT 30
            """),
            {"user_id": user_id}
        )
        rows = result.fetchall()
    
    return [
        {
            "id": str(row.id),
            "title": row.title,
            "resourceType": row.resource_type,
            "platform": row.platform,
            "estimatedDuration": row.estimated_duration,
            "nodeName": row.node_name or "General",
            "status": row.status
        }
        for row in rows
    ]


# =====================================================
# AI Auto-Scheduling Endpoint
# =====================================================

import json
import re
from datetime import timedelta

class AIScheduleRequest(BaseModel):
    prompt: str  # e.g. "Tôi rảnh 8h tối thứ 2,4,6"
    resourceIds: Optional[List[str]] = None  # Specific resources to schedule
    weeksAhead: int = 4  # How many weeks to generate


class ScheduleSuggestion(BaseModel):
    resourceId: str
    resourceName: str
    scheduledDate: str
    scheduledTime: str
    deadline: str
    priority: str


class AIScheduleResponse(BaseModel):
    parsed: dict
    suggestions: List[ScheduleSuggestion]
    message: str


@router.post("/ai-schedule", response_model=AIScheduleResponse)
async def ai_schedule(
    data: AIScheduleRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Parse natural language and generate schedule suggestions using AI"""
    from shared.llm.gemini_adapter import GeminiAdapter
    
    # Get available resources
    if data.resourceIds:
        placeholders = ", ".join([f"'{rid}'" for rid in data.resourceIds])
        query = f"""
            SELECT lr.id, lr.title, lr.estimated_duration, tsn.name as node_name
            FROM learning_resources lr
            LEFT JOIN template_skill_nodes tsn ON lr.skill_node_id = tsn.id
            WHERE lr.id IN ({placeholders})
            ORDER BY lr.title
        """
    else:
        # Only get resources from user's timeline that are not completed
        query = """
            SELECT DISTINCT lr.id, lr.title, lr.estimated_duration, 
                   COALESCE(tsn.name, 'General') as node_name
            FROM timeline_items ti
            JOIN learning_resources lr ON ti.resource_id = lr.id
            LEFT JOIN template_skill_nodes tsn ON lr.skill_node_id = tsn.id
            LEFT JOIN learning_progress lp ON lp.resource_id = lr.id AND lp.user_id = :user_id
            WHERE ti.user_id = :user_id
                AND COALESCE(lp.status, 'not_started') != 'completed'
            ORDER BY node_name, lr.title
            LIMIT 10
        """
    
    result = await db.execute(text(query), {"user_id": user_id})
    resources = result.fetchall()
    
    if not resources:
        raise HTTPException(status_code=400, detail="No resources available to schedule")
    
    # Create prompt for Gemini to parse schedule preferences
    parse_prompt = f'''
Bạn là AI assistant giúp xếp lịch học. Phân tích yêu cầu của user và trích xuất thông tin.

User nói: "{data.prompt}"

Trả về JSON với format:
{{
    "days_of_week": [0-6] (0=Monday, 6=Sunday),
    "time_start": "HH:MM" (24h format),
    "duration_minutes": number (default 60),
    "priority": "high" | "medium" | "low"
}}

Ví dụ:
- "8h tối thứ 2,4,6" -> {{"days_of_week": [0, 2, 4], "time_start": "20:00", "duration_minutes": 60, "priority": "medium"}}
- "sáng sớm 6h các ngày trong tuần" -> {{"days_of_week": [0,1,2,3,4], "time_start": "06:00", "duration_minutes": 60, "priority": "medium"}}

Chỉ trả về JSON, không có text khác.
'''
    
    try:
        llm = GeminiAdapter()
        response = await llm.generate(parse_prompt)
        
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not json_match:
            raise ValueError("Could not parse AI response")
        
        parsed = json.loads(json_match.group())
        
        # Validate parsed data
        days = parsed.get("days_of_week", [0, 2, 4])  # Default Mon, Wed, Fri
        time_start = parsed.get("time_start", "20:00")
        priority = parsed.get("priority", "medium")
        
    except Exception as e:
        # Fallback to default schedule
        parsed = {
            "days_of_week": [0, 2, 4],
            "time_start": "20:00",
            "duration_minutes": 60,
            "priority": "medium"
        }
        days = [0, 2, 4]
        time_start = "20:00"
        priority = "medium"
    
    # Generate schedule suggestions
    suggestions = []
    today = date.today()
    resource_index = 0
    
    for week in range(data.weeksAhead):
        for day in days:
            if resource_index >= len(resources):
                break
            
            # Calculate the date
            days_until = (day - today.weekday() + 7) % 7
            if days_until == 0 and week == 0:
                days_until = 7  # Skip to next week if today
            scheduled_date = today + timedelta(days=days_until + (week * 7))
            deadline_date = scheduled_date + timedelta(days=7)
            
            res = resources[resource_index]
            suggestions.append(ScheduleSuggestion(
                resourceId=str(res.id),
                resourceName=res.title,
                scheduledDate=scheduled_date.isoformat(),
                scheduledTime=time_start,
                deadline=deadline_date.isoformat(),
                priority=priority
            ))
            
            resource_index += 1
        
        if resource_index >= len(resources):
            break
    
    return AIScheduleResponse(
        parsed=parsed,
        suggestions=suggestions,
        message=f"Đã tạo {len(suggestions)} lịch học cho {len(resources)} tài liệu"
    )


@router.post("/ai-schedule/confirm")
async def confirm_ai_schedule(
    suggestions: List[ScheduleSuggestion],
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Confirm and insert AI-generated schedule suggestions"""
    
    created_count = 0
    
    for item in suggestions:
        try:
            scheduled = datetime.strptime(item.scheduledDate, "%Y-%m-%d").date()
            deadline = datetime.strptime(item.deadline, "%Y-%m-%d").date()
            
            await db.execute(
                text("""
                    INSERT INTO timeline_items (user_id, resource_id, scheduled_date, deadline, priority)
                    VALUES (:user_id, :resource_id, :scheduled, :deadline, :priority)
                """),
                {
                    "user_id": user_id,
                    "resource_id": item.resourceId,
                    "scheduled": scheduled,
                    "deadline": deadline,
                    "priority": item.priority
                }
            )
            created_count += 1
        except Exception as e:
            print(f"Error inserting item: {e}")
            continue
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Đã thêm {created_count} mục vào lịch học",
        "createdCount": created_count
    }

