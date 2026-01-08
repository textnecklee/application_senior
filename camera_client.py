"""
웹캠을 사용한 집중도 감지 클라이언트
노트북 웹캠으로 사용자의 집중 상태를 감지하고 서버로 전송합니다.
"""

import cv2
import mediapipe as mp
import websockets
import asyncio
import json
import time
from typing import Optional

# MediaPipe 얼굴 메시 설정
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils


class FocusDetector:
    """집중도 감지 클래스"""
    
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 눈 랜드마크 인덱스 (왼쪽 눈, 오른쪽 눈)
        self.LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        self.RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        
        # 집중도 판단 기준
        self.blink_threshold = 0.3  # 눈 깜빡임 임계값
        self.ear_history = []  # 눈 종횡비(EAR) 히스토리
        self.history_size = 5
        
    def calculate_ear(self, landmarks, eye_indices):
        """눈 종횡비(Eye Aspect Ratio) 계산"""
        # 눈의 수직 거리
        vertical_1 = self._distance(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
        vertical_2 = self._distance(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
        
        # 눈의 수평 거리
        horizontal = self._distance(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
        
        # EAR 계산
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear
    
    def _distance(self, point1, point2):
        """두 점 사이의 거리 계산"""
        return ((point1.x - point2.x)**2 + (point1.y - point2.y)**2)**0.5
    
    def is_focused(self, landmarks) -> bool:
        """집중 상태 판단"""
        # 왼쪽 눈과 오른쪽 눈의 EAR 계산
        left_ear = self.calculate_ear(landmarks, self.LEFT_EYE_INDICES)
        right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE_INDICES)
        
        # 평균 EAR
        avg_ear = (left_ear + right_ear) / 2.0
        
        # 히스토리에 추가
        self.ear_history.append(avg_ear)
        if len(self.ear_history) > self.history_size:
            self.ear_history.pop(0)
        
        # 평균 EAR이 임계값보다 높으면 집중 상태 (눈이 열려있음)
        # 너무 낮으면 눈을 감고 있거나 집중하지 않음
        if len(self.ear_history) < self.history_size:
            return True  # 초기에는 집중 상태로 간주
        
        avg_ear_value = sum(self.ear_history) / len(self.ear_history)
        is_focused = avg_ear_value > self.blink_threshold
        
        return is_focused


class CameraClient:
    """웹캠 클라이언트"""
    
    def __init__(self, server_url: str = "ws://localhost:8000/ws", user_id: str = "user1"):
        self.server_url = server_url
        self.user_id = user_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.detector = FocusDetector()
        self.session_started = False
        
    async def connect(self):
        """서버에 연결"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"서버에 연결되었습니다: {self.server_url}")
            return True
        except Exception as e:
            print(f"서버 연결 실패: {e}")
            return False
    
    async def start_session(self):
        """학습 세션 시작"""
        if not self.websocket:
            await self.connect()
        
        message = {
            "type": "session_start",
            "user_id": self.user_id,
            "timestamp": time.time()
        }
        
        await self.websocket.send(json.dumps(message))
        self.session_started = True
        print("학습 세션이 시작되었습니다.")
    
    async def send_status_update(self, is_focused: bool):
        """집중 상태 업데이트 전송"""
        if not self.websocket or not self.session_started:
            return
        
        message = {
            "type": "status_update",
            "is_focused": is_focused,
            "timestamp": time.time()
        }
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            print(f"상태 업데이트 전송 실패: {e}")
    
    async def end_session(self):
        """학습 세션 종료"""
        if not self.websocket or not self.session_started:
            return
        
        message = {
            "type": "session_end",
            "timestamp": time.time()
        }
        
        await self.websocket.send(json.dumps(message))
        self.session_started = False
        print("학습 세션이 종료되었습니다.")
    
    async def run(self):
        """웹캠 실행 및 집중도 감지"""
        # 웹캠 초기화
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("웹캠을 열 수 없습니다.")
            return
        
        print("웹캠이 시작되었습니다. 'q'를 눌러 종료하세요.")
        
        # 서버 연결
        if not await self.connect():
            cap.release()
            return
        
        # 세션 시작
        await self.start_session()
        
        last_update_time = time.time()
        update_interval = 1.0  # 1초마다 상태 업데이트
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 좌우 반전 (거울 효과)
                frame = cv2.flip(frame, 1)
                
                # RGB로 변환 (MediaPipe는 RGB 사용)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 얼굴 감지
                results = self.detector.face_mesh.process(rgb_frame)
                
                is_focused = True
                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]
                    is_focused = self.detector.is_focused(face_landmarks.landmark)
                    
                    # 얼굴 랜드마크 그리기 (선택사항)
                    mp_drawing.draw_landmarks(
                        frame,
                        face_landmarks,
                        mp_face_mesh.FACEMESH_CONTOURS,
                        None,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
                    )
                
                # 상태 표시
                status_text = "집중 중" if is_focused else "비집중"
                status_color = (0, 255, 0) if is_focused else (0, 0, 255)
                cv2.putText(frame, f"Status: {status_text}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
                cv2.putText(frame, f"User: {self.user_id}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 주기적으로 상태 업데이트 전송
                current_time = time.time()
                if current_time - last_update_time >= update_interval:
                    await self.send_status_update(is_focused)
                    last_update_time = current_time
                
                # 화면 표시
                cv2.imshow('Focus Detection', frame)
                
                # 'q' 키로 종료
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\n프로그램이 중단되었습니다.")
        finally:
            # 세션 종료
            await self.end_session()
            
            # 리소스 정리
            cap.release()
            cv2.destroyAllWindows()
            
            if self.websocket:
                await self.websocket.close()
            print("리소스가 정리되었습니다.")


async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='웹캠 집중도 감지 클라이언트')
    parser.add_argument('--server', type=str, default='ws://localhost:8000/ws',
                       help='서버 WebSocket URL (기본값: ws://localhost:8000/ws)')
    parser.add_argument('--user', type=str, default='user1',
                       help='사용자 ID (기본값: user1)')
    
    args = parser.parse_args()
    
    client = CameraClient(server_url=args.server, user_id=args.user)
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())

