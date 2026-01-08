"""
공부 세션 데이터 모델
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StudySession(BaseModel):
    """공부 세션 모델"""
    id: Optional[str] = None
    user_id: str
    start_time: datetime
    end_time: datetime
    total_time: float  # 초 단위
    focused_time: float  # 초 단위
    unfocused_time: float  # 초 단위
    created_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StudySessionCreate(BaseModel):
    """세션 생성 요청 모델"""
    user_id: str
    start_time: datetime
    end_time: datetime
    total_time: float
    focused_time: float
    unfocused_time: float


class StudySessionResponse(BaseModel):
    """세션 응답 모델"""
    id: str
    user_id: str
    start_time: str
    end_time: str
    total_time: float
    focused_time: float
    unfocused_time: float
    created_at: str

