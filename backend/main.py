"""
FastAPI 서버 메인 파일
라즈베리파이로부터 실시간 데이터를 받아 Supabase에 저장하고
Flutter 앱에 API를 제공합니다.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
import json
import os

from websocket_handler import ConnectionManager
from routes import study_sessions, leaderboard, stats
from models.database import init_supabase

app = FastAPI(title="Study Tracker API", version="1.0.0")

# CORS 설정 (Flutter 앱에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 연결 관리자
manager = ConnectionManager()

# 라우터 등록
app.include_router(study_sessions.router, prefix="/api", tags=["study-sessions"])
app.include_router(leaderboard.router, prefix="/api", tags=["leaderboard"])
app.include_router(stats.router, prefix="/api", tags=["stats"])


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 Supabase 초기화"""
    init_supabase()
    print("서버가 시작되었습니다.")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Study Tracker API", "status": "running"}


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트 - 라즈베리파이와의 실시간 통신"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await manager.handle_message(websocket, message)
            
            # [추가됨] 메시지 처리 중 연결이 끊겼다면 루프 종료
            if websocket not in manager.active_connections:
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 오류: {e}")
        # 이미 연결이 해제된 상태일 수 있으므로 안전하게 처리
        if websocket in manager.active_connections:
            manager.disconnect(websocket)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

