"""
Supabase 데이터베이스 연동 모듈
"""

from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (여러 위치에서 검색)
_current_file = Path(__file__).resolve()
_possible_paths = [
    _current_file.parent.parent.parent / ".env",  # app/.env
    _current_file.parent.parent / ".env",          # backend/.env
    Path.cwd() / ".env",                           # 현재 작업 디렉토리
]

for _env_path in _possible_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        break
else:
    load_dotenv()  # 기본 동작

# Supabase 초기화 플래그
_supabase_initialized = False
_supabase_client: Optional[Client] = None


def init_supabase():
    """Supabase 초기화"""
    global _supabase_initialized, _supabase_client
    
    if _supabase_initialized:
        return
    
    # Supabase 인증 정보 (환경 변수에서 읽기)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL과 SUPABASE_KEY 환경 변수를 설정해주세요.\n"
            "Supabase 프로젝트 설정에서 URL과 anon key를 확인할 수 있습니다."
        )
    
    _supabase_client = create_client(supabase_url, supabase_key)
    _supabase_initialized = True
    print("Supabase가 초기화되었습니다.")


def get_db() -> Client:
    """Supabase 클라이언트 인스턴스 반환"""
    if not _supabase_initialized:
        init_supabase()
    return _supabase_client


def save_study_session(session_data: Dict) -> str:
    """공부 세션 데이터를 Supabase에 저장"""
    db = get_db()
    
    # datetime 객체를 ISO 형식 문자열로 변환
    session_record = {
        "user_id": session_data["user_id"],
        "start_time": session_data["start_time"].isoformat() if isinstance(session_data["start_time"], datetime) else session_data["start_time"],
        "end_time": session_data["end_time"].isoformat() if isinstance(session_data["end_time"], datetime) else session_data["end_time"],
        "total_time": session_data["total_time"],
        "focused_time": session_data["focused_time"],
        "unfocused_time": session_data["unfocused_time"],
        "created_at": datetime.now().isoformat()
    }
    
    response = db.table("study_sessions").insert(session_record).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]["id"]
    raise Exception("세션 저장 실패")


def get_user_sessions(user_id: str, start_date: Optional[datetime] = None, 
                     end_date: Optional[datetime] = None) -> List[Dict]:
    """사용자의 공부 세션 목록 조회"""
    db = get_db()
    
    query = db.table("study_sessions").select("*").eq("user_id", user_id)
    
    if start_date:
        query = query.gte("start_time", start_date.isoformat())
    if end_date:
        query = query.lte("start_time", end_date.isoformat())
    
    query = query.order("start_time", desc=True)
    
    response = query.execute()
    
    sessions = []
    for session in response.data:
        # ISO 형식 문자열을 datetime 객체로 변환
        session["start_time"] = datetime.fromisoformat(session["start_time"].replace("Z", "+00:00"))
        session["end_time"] = datetime.fromisoformat(session["end_time"].replace("Z", "+00:00"))
        if session.get("created_at"):
            session["created_at"] = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        sessions.append(session)
    
    return sessions


def get_user_daily_stats(user_id: str, date: datetime) -> Dict:
    """사용자의 특정 날짜 통계 조회"""
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    sessions = get_user_sessions(user_id, start_of_day, end_of_day)
    
    total_time = sum(s["total_time"] for s in sessions)
    focused_time = sum(s["focused_time"] for s in sessions)
    unfocused_time = sum(s["unfocused_time"] for s in sessions)
    
    return {
        "date": date.date().isoformat(),
        "total_time": total_time,
        "focused_time": focused_time,
        "unfocused_time": unfocused_time,
        "session_count": len(sessions)
    }


def get_user_weekly_stats(user_id: str, week_start: datetime) -> List[Dict]:
    """사용자의 주간 통계 조회"""
    week_end = week_start + timedelta(days=7)
    sessions = get_user_sessions(user_id, week_start, week_end)
    
    # 날짜별로 그룹화
    daily_stats = {}
    for session in sessions:
        session_date = session["start_time"].date()
        if session_date not in daily_stats:
            daily_stats[session_date] = {
                "date": session_date.isoformat(),
                "total_time": 0,
                "focused_time": 0,
                "unfocused_time": 0,
                "session_count": 0
            }
        
        daily_stats[session_date]["total_time"] += session["total_time"]
        daily_stats[session_date]["focused_time"] += session["focused_time"]
        daily_stats[session_date]["unfocused_time"] += session["unfocused_time"]
        daily_stats[session_date]["session_count"] += 1
    
    # 날짜 순으로 정렬
    return sorted(daily_stats.values(), key=lambda x: x["date"])


def get_leaderboard(period: str = "day", limit: int = 100) -> List[Dict]:
    """리더보드 데이터 조회
    
    Args:
        period: 'day', 'week', 'month' 중 하나
        limit: 반환할 최대 사용자 수
    """
    db = get_db()
    
    # 기간에 따른 시작 날짜 계산
    now = datetime.now()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 해당 기간의 모든 세션 조회
    response = db.table("study_sessions")\
        .select("*")\
        .gte("start_time", start_date.isoformat())\
        .execute()
    
    # 사용자별로 집계
    user_stats = {}
    for session in response.data:
        user_id = session["user_id"]
        
        if user_id not in user_stats:
            user_stats[user_id] = {
                "user_id": user_id,
                "total_time": 0,
                "focused_time": 0,
                "session_count": 0
            }
        
        user_stats[user_id]["total_time"] += session["total_time"]
        user_stats[user_id]["focused_time"] += session["focused_time"]
        user_stats[user_id]["session_count"] += 1
    
    # 총 시간 기준으로 정렬
    leaderboard = sorted(user_stats.values(), key=lambda x: x["total_time"], reverse=True)
    return leaderboard[:limit]


def get_current_session(user_id: str) -> Optional[Dict]:
    """현재 진행 중인 세션 조회"""
    db = get_db()
    
    response = db.table("study_sessions")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("start_time", desc=True)\
        .limit(1)\
        .execute()
    
    if response.data and len(response.data) > 0:
        session = response.data[0]
        # ISO 형식 문자열을 datetime 객체로 변환
        session["start_time"] = datetime.fromisoformat(session["start_time"].replace("Z", "+00:00"))
        if session.get("end_time"):
            session["end_time"] = datetime.fromisoformat(session["end_time"].replace("Z", "+00:00"))
        if session.get("created_at"):
            session["created_at"] = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        # 세션이 아직 종료되지 않았는지 확인
        if "end_time" in session and session["end_time"]:
            return session
    return None
