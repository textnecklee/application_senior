"""
공부 세션 관련 API 라우트
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from models.study_session import StudySessionResponse
from models.database import (
    get_user_sessions, 
    get_user_daily_stats,
    get_user_weekly_stats,
    get_current_session
)

router = APIRouter()


@router.get("/sessions/{user_id}", response_model=List[StudySessionResponse])
async def get_sessions(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """사용자의 공부 세션 목록 조회"""
    try:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        sessions = get_user_sessions(user_id, start, end)
        
        # 응답 형식 변환
        response = []
        for session in sessions[:limit]:
            response.append({
                "id": session["id"],
                "user_id": session["user_id"],
                "start_time": session["start_time"].isoformat() if isinstance(session["start_time"], datetime) else session["start_time"],
                "end_time": session["end_time"].isoformat() if isinstance(session["end_time"], datetime) else session["end_time"],
                "total_time": session["total_time"],
                "focused_time": session["focused_time"],
                "unfocused_time": session["unfocused_time"],
                "created_at": session.get("created_at", datetime.now()).isoformat() if isinstance(session.get("created_at"), datetime) else session.get("created_at", "")
            })
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}/current")
async def get_current_user_session(user_id: str):
    """현재 진행 중인 세션 조회"""
    try:
        session = get_current_session(user_id)
        if not session:
            return None
        
        return {
            "id": session["id"],
            "user_id": session["user_id"],
            "start_time": session["start_time"].isoformat() if isinstance(session["start_time"], datetime) else session["start_time"],
            "end_time": session.get("end_time", ""),
            "total_time": session.get("total_time", 0),
            "focused_time": session.get("focused_time", 0),
            "unfocused_time": session.get("unfocused_time", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}/daily/{date}")
async def get_daily_stats(user_id: str, date: str):
    """특정 날짜의 통계 조회"""
    try:
        target_date = datetime.fromisoformat(date)
        stats = get_user_daily_stats(user_id, target_date)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}/weekly")
async def get_weekly_stats(
    user_id: str,
    week_start: Optional[str] = None
):
    """주간 통계 조회"""
    try:
        if week_start:
            start = datetime.fromisoformat(week_start)
        else:
            # 이번 주 월요일
            today = datetime.now()
            days_since_monday = today.weekday()
            start = today - timedelta(days=days_since_monday)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = get_user_weekly_stats(user_id, start)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

