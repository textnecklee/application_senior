"""
WebSocket 연결 관리 및 메시지 처리
"""

from fastapi import WebSocket
from typing import List, Dict, Optional
import json
import time
from datetime import datetime
from models.database import save_study_session, get_current_session
from models.study_session import StudySession


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_sessions: Dict[WebSocket, Dict] = {}  # 각 연결의 세션 정보
    
    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_sessions[websocket] = {
            "user_id": None,
            "session_start_time": None,
            "focused_time": 0.0,
            "unfocused_time": 0.0,
            "last_status": True,
            "last_status_time": None
        }
        print(f"클라이언트 연결됨. 총 연결 수: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 세션 종료 처리
        if websocket in self.client_sessions:
            session_info = self.client_sessions[websocket]
            if session_info["session_start_time"]:
                self._finalize_session(websocket, session_info)
            del self.client_sessions[websocket]
        
        print(f"클라이언트 연결 해제됨. 총 연결 수: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """특정 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """모든 클라이언트에게 브로드캐스트"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"브로드캐스트 실패: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    def _update_time_tracking(self, session_info: Dict, is_focused: bool, current_time: float):
        """시간 추적 업데이트"""
        if not session_info["session_start_time"]:
            return
        
        if session_info["last_status_time"]:
            elapsed = current_time - session_info["last_status_time"]
            if session_info["last_status"]:
                session_info["focused_time"] += elapsed
            else:
                session_info["unfocused_time"] += elapsed
        
        session_info["last_status"] = is_focused
        session_info["last_status_time"] = current_time
    
    def _finalize_session(self, websocket: WebSocket, session_info: Dict):
        """세션 종료 및 데이터 저장"""
        if not session_info["session_start_time"]:
            return
        
        current_time = time.time()
        # 마지막 시간 구간 업데이트
        self._update_time_tracking(session_info, session_info["last_status"], current_time)
        
        total_time = current_time - session_info["session_start_time"]
        
        session_data = {
            "user_id": session_info["user_id"],
            "start_time": datetime.fromtimestamp(session_info["session_start_time"]),
            "end_time": datetime.fromtimestamp(current_time),
            "total_time": total_time,
            "focused_time": session_info["focused_time"],
            "unfocused_time": session_info["unfocused_time"]
        }
        
        # Firebase에 저장
        try:
            save_study_session(session_data)
            print(f"세션 데이터 저장 완료: {session_data}")
        except Exception as e:
            print(f"세션 데이터 저장 실패: {e}")
    
    async def handle_message(self, websocket: WebSocket, message: Dict):
        """받은 메시지 처리"""
        msg_type = message.get("type")
        session_info = self.client_sessions.get(websocket)
        
        if not session_info:
            return
        
        if msg_type == "session_start":
            # 세션 시작
            session_info["user_id"] = message.get("user_id")
            session_info["session_start_time"] = time.time()
            session_info["focused_time"] = 0.0
            session_info["unfocused_time"] = 0.0
            session_info["last_status"] = True
            session_info["last_status_time"] = time.time()
            
            response = {
                "type": "session_started",
                "message": "세션이 시작되었습니다.",
                "timestamp": time.time()
            }
            await self.send_personal_message(json.dumps(response), websocket)
            print(f"세션 시작: 사용자 {session_info['user_id']}")
        
        elif msg_type == "status_update":
            # 집중 상태 업데이트
            is_focused = message.get("is_focused", True)
            current_time = message.get("timestamp", time.time())
            
            self._update_time_tracking(session_info, is_focused, current_time)
        
        elif msg_type == "session_end":
            # 세션 종료
            session_data = message.get("session_data", {})
            
            # 세션 정보 업데이트
            if session_data:
                session_info["focused_time"] = session_data.get("focused_time", session_info["focused_time"])
                session_info["unfocused_time"] = session_data.get("unfocused_time", session_info["unfocused_time"])
            
            self._finalize_session(websocket, session_info)
            
            response = {
                "type": "session_ended",
                "message": "세션이 종료되었습니다.",
                "session_data": {
                    "total_time": session_data.get("total_time", 0),
                    "focused_time": session_info["focused_time"],
                    "unfocused_time": session_info["unfocused_time"]
                },
                "timestamp": time.time()
            }
            await self.send_personal_message(json.dumps(response), websocket)
            print(f"세션 종료: 사용자 {session_info['user_id']}")
        
        elif msg_type == "ping":
            # 핑 응답
            response = {
                "type": "pong",
                "timestamp": time.time()
            }
            await self.send_personal_message(json.dumps(response), websocket)

