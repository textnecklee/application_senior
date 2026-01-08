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
        self.client_sessions: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_sessions[websocket] = {
            "user_id": None,
            "session_start_datetime": None,
            "focused_time": 0.0,
            "unfocused_time": 0.0,
            "last_status": True
        }
        print(f"클라이언트 연결됨. 총 연결 수: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if websocket in self.client_sessions:
            session_info = self.client_sessions[websocket]
            if session_info["session_start_datetime"]:
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
    
    def _finalize_session(self, websocket: WebSocket, session_info: Dict):
        """세션 종료 및 데이터 저장"""
        if not session_info["session_start_datetime"]:
            return
        
        end_datetime = datetime.now()
        start_datetime = session_info["session_start_datetime"]
        
        # 0.01초 분해능으로 반올림
        focused_time = round(session_info["focused_time"], 2)
        unfocused_time = round(session_info["unfocused_time"], 2)
        total_time = round(focused_time + unfocused_time, 2)
        
        session_data = {
            "user_id": session_info["user_id"],
            "start_time": start_datetime,
            "end_time": end_datetime,
            "total_time": total_time,
            "focused_time": focused_time,
            "unfocused_time": unfocused_time
        }
        
        try:
            save_study_session(session_data)
            print(f"\n세션 데이터 저장 완료:")
            print(f"  사용자: {session_info['user_id']}")
            print(f"  총 시간: {total_time:.2f}초")
            if total_time > 0:
                print(f"  집중 시간: {focused_time:.2f}초 ({focused_time/total_time*100:.1f}%)")
                print(f"  비집중 시간: {unfocused_time:.2f}초 ({unfocused_time/total_time*100:.1f}%)")
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
            session_info["session_start_datetime"] = datetime.now()
            session_info["focused_time"] = 0.0
            session_info["unfocused_time"] = 0.0
            session_info["last_status"] = True
            
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
            duration = message.get("duration", 0.0)  # 클라이언트가 보낸 지속 시간
            
            if duration > 0:
                # 클라이언트가 계산한 지속 시간 사용
                if session_info["last_status"]:
                    session_info["focused_time"] += duration
                    print(f"✓ 집중 +{duration:.2f}초 (총 집중: {session_info['focused_time']:.2f}초)")
                else:
                    session_info["unfocused_time"] += duration
                    print(f"✗ 비집중 +{duration:.2f}초 (총 비집중: {session_info['unfocused_time']:.2f}초)")
            
            # 현재 상태로 업데이트
            session_info["last_status"] = is_focused
        
        elif msg_type == "session_end":
            # 세션 종료
            # 마지막 duration이 있으면 처리
            duration = message.get("duration", 0.0)
            if duration > 0:
                if session_info["last_status"]:
                    session_info["focused_time"] += duration
                else:
                    session_info["unfocused_time"] += duration
            
            self._finalize_session(websocket, session_info)
            
            # 0.01초 분해능으로 반올림
            focused_time = round(session_info["focused_time"], 2)
            unfocused_time = round(session_info["unfocused_time"], 2)
            total_time = round(focused_time + unfocused_time, 2)
            
            response = {
                "type": "session_ended",
                "message": "세션이 종료되었습니다.",
                "session_data": {
                    "total_time": total_time,
                    "focused_time": focused_time,
                    "unfocused_time": unfocused_time
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
