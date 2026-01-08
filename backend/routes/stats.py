"""
통계 관련 API 라우트
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
from datetime import datetime, timedelta
from models.database import get_user_sessions, get_user_daily_stats

router = APIRouter()


@router.get("/stats/{user_id}/summary")
async def get_user_summary(user_id: str):
    """사용자 전체 통계 요약"""
    try:
        # 전체 세션 조회
        all_sessions = get_user_sessions(user_id)
        
        total_sessions = len(all_sessions)
        total_time = sum(s["total_time"] for s in all_sessions)
        total_focused_time = sum(s["focused_time"] for s in all_sessions)
        total_unfocused_time = sum(s["unfocused_time"] for s in all_sessions)
        
        # 오늘 통계
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_stats = get_user_daily_stats(user_id, today)
        
        # 이번 주 통계
        week_start = today - timedelta(days=today.weekday())
        week_sessions = [s for s in all_sessions 
                        if s["start_time"] >= week_start]
        week_time = sum(s["total_time"] for s in week_sessions)
        
        # 이번 달 통계
        month_start = today.replace(day=1)
        month_sessions = [s for s in all_sessions 
                         if s["start_time"] >= month_start]
        month_time = sum(s["total_time"] for s in month_sessions)
        
        return {
            "total_sessions": total_sessions,
            "total_time": total_time,
            "total_focused_time": total_focused_time,
            "total_unfocused_time": total_unfocused_time,
            "focus_ratio": total_focused_time / total_time if total_time > 0 else 0,
            "today": {
                "total_time": today_stats["total_time"],
                "focused_time": today_stats["focused_time"],
                "session_count": today_stats["session_count"]
            },
            "this_week": {
                "total_time": week_time,
                "session_count": len(week_sessions)
            },
            "this_month": {
                "total_time": month_time,
                "session_count": len(month_sessions)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

