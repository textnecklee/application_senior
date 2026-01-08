"""
경쟁 리그 관련 API 라우트
"""

from fastapi import APIRouter, HTTPException
from typing import List
from models.database import get_leaderboard

router = APIRouter()


@router.get("/leaderboard/{period}")
async def get_leaderboard_data(period: str, limit: int = 100):
    """리더보드 데이터 조회
    
    Args:
        period: 'day', 'week', 'month' 중 하나
        limit: 반환할 최대 사용자 수
    """
    if period not in ["day", "week", "month"]:
        raise HTTPException(
            status_code=400, 
            detail="period는 'day', 'week', 'month' 중 하나여야 합니다."
        )
    
    try:
        leaderboard = get_leaderboard(period, limit)
        
        # 순위 추가
        for i, entry in enumerate(leaderboard, 1):
            entry["rank"] = i
        
        return {
            "period": period,
            "leaderboard": leaderboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

