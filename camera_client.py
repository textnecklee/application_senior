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
        
        # 간단한 눈 랜드마크 인덱스 (상하좌우 6개 점만 사용)
        # 왼쪽 눈
        self.LEFT_EYE = [
            362,  # 왼쪽 끝
            385,  # 오른쪽 끝
            387,  # 위쪽
            373,  # 아래쪽
            380,  # 위쪽 중간
            374   # 아래쪽 중간
        ]
        
        # 오른쪽 눈
        self.RIGHT_EYE = [
            33,   # 왼쪽 끝
            133,  # 오른쪽 끝
            159,  # 위쪽
            145,  # 아래쪽
            158,  # 위쪽 중간
            153   # 아래쪽 중간
        ]
        
        # 집중도 판단 기준
        self.ear_threshold = 0.21  # 눈 감김 기준
        self.ear_history = []
        self.history_size = 5
        
        # 얼굴 방향 판단용
        self.nose_index = 1
        self.left_eye_center = 33
        self.right_eye_center = 263
        
    def calculate_ear(self, landmarks, eye_indices):
        """눈 종횡비(Eye Aspect Ratio) 계산"""
        # 6개 점 방식: [0]=왼쪽끝, [1]=오른쪽끝, [2]=위, [3]=아래, [4]=위중간, [5]=아래중간
        
        # 수직 거리 2개
        vertical_1 = self._distance(landmarks[eye_indices[2]], landmarks[eye_indices[3]])
        vertical_2 = self._distance(landmarks[eye_indices[4]], landmarks[eye_indices[5]])
        
        # 수평 거리
        horizontal = self._distance(landmarks[eye_indices[0]], landmarks[eye_indices[1]])
        
        # EAR = (수직1 + 수직2) / (2 * 수평)
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear
    
    def _distance(self, point1, point2):
        """두 점 사이의 거리 계산"""
        return ((point1.x - point2.x)**2 + (point1.y - point2.y)**2)**0.5
    
    def calculate_head_pose(self, landmarks):
        """얼굴 방향 계산"""
        nose = landmarks[self.nose_index]
        left_eye = landmarks[self.left_eye_center]
        right_eye = landmarks[self.right_eye_center]
        
        eye_center_x = (left_eye.x + right_eye.x) / 2
        horizontal_offset = abs(nose.x - eye_center_x)
        
        return horizontal_offset
        
    def is_focused(self, landmarks) -> bool:
        """집중 상태 판단"""
        # 1. 양쪽 눈의 EAR 계산
        left_ear = self.calculate_ear(landmarks, self.LEFT_EYE)
        right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE)
        avg_ear = (left_ear + right_ear) / 2.0
        
        # 2. EAR 히스토리에 추가
        self.ear_history.append(avg_ear)
        if len(self.ear_history) > self.history_size:
            self.ear_history.pop(0)
        
        if len(self.ear_history) < self.history_size:
            return True
        
        # 3. 평균 EAR 계산
        avg_ear_value = sum(self.ear_history) / len(self.ear_history)
        
        # 4. 얼굴 방향 계산
        head_offset = self.calculate_head_pose(landmarks)
        
        # 5. 판단 기준
        eyes_open = avg_ear_value > self.ear_threshold  # 눈이 떠져 있음
        looking_forward = head_offset < 0.08  # 정면을 보고 있음
        
        # 디버그 출력
        print(f"EAR: {avg_ear_value:.3f} (눈{'열림' if eyes_open else '감김'}), "
              f"Head: {head_offset:.3f} ({'정면' if looking_forward else '측면'})")
        
        is_focused = eyes_open and looking_forward
        
        return is_focused


class CameraClient:
    def __init__(self, server_url: str = "ws://localhost:8000/ws", user_id: str = "user1"):
        self.server_url = server_url
        self.user_id = user_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.detector = FocusDetector()
        self.session_started = False
    
    async def connect(self) -> bool:
        """서버에 WebSocket 연결"""
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
            return
        
        message = {
            "type": "session_start",
            "user_id": self.user_id,
            "timestamp": time.time()
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            self.session_started = True
            print(f"학습 세션이 시작되었습니다. (사용자: {self.user_id})")
        except Exception as e:
            print(f"세션 시작 실패: {e}")
    
    async def send_status_update(self, is_focused: bool, duration: float = 0.0):
        """집중 상태 업데이트 전송 (지속 시간 포함)"""
        if not self.websocket or not self.session_started:
            return
        
        message = {
            "type": "status_update",
            "is_focused": is_focused,
            "duration": duration,  # 이전 상태의 지속 시간
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
        
        try:
            await self.websocket.send(json.dumps(message))
            self.session_started = False
            print("학습 세션이 종료되었습니다.")
        except Exception as e:
            print(f"세션 종료 실패: {e}")
    
    async def run(self):
        """웹캠 실행 및 집중도 감지"""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("웹캠을 열 수 없습니다.")
            return
        
        print("웹캠이 시작되었습니다. 'q'를 눌러 종료하세요.")
        
        if not await self.connect():
            cap.release()
            return
        
        await self.start_session()
        
        # 상태 추적
        current_state = None
        confirmed_state = None
        confirmed_state_start = None  # 확정 상태 시작 시간
        
        state_change_time = None
        debounce_time = 0.5
        
        last_heartbeat_time = time.time()
        heartbeat_interval = 5.0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                results = self.detector.face_mesh.process(rgb_frame)
                
                is_focused = False
                
                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]
                    is_focused = self.detector.is_focused(face_landmarks.landmark)
                    
                    mp_drawing.draw_landmarks(
                        frame,
                        face_landmarks,
                        mp_face_mesh.FACEMESH_CONTOURS,
                        None,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
                    )
                else:
                    cv2.putText(frame, "No Face Detected", (10, 110),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                status_text = "Focused" if is_focused else "Unfocused"
                status_color = (0, 255, 0) if is_focused else (0, 0, 255)
                cv2.putText(frame, f"Status: {status_text}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
                cv2.putText(frame, f"User: {self.user_id}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                current_time = time.time()
                
                # 초기화
                if confirmed_state is None:
                    confirmed_state = is_focused
                    current_state = is_focused
                    confirmed_state_start = current_time
                    await self.send_status_update(is_focused, duration=0.0)
                    print(f"[초기 상태] {'Focused' if is_focused else 'Unfocused'}")
                
                # 현재 감지 상태 업데이트
                if current_state != is_focused:
                    current_state = is_focused
                    state_change_time = current_time
                
                # 디바운싱 확인
                if current_state != confirmed_state:
                    if state_change_time and (current_time - state_change_time >= debounce_time):
                        # 이전 상태의 지속 시간 계산
                        duration = state_change_time - confirmed_state_start
                        
                        print(f"[상태 변화 확정] {'Focused' if confirmed_state else 'Unfocused'} "
                              f"→ {'Focused' if current_state else 'Unfocused'} (지속시간: {duration:.2f}초)")
                        
                        # 새 상태와 이전 상태의 지속 시간 전송
                        await self.send_status_update(current_state, duration=duration)
                        
                        confirmed_state = current_state
                        confirmed_state_start = state_change_time
                
                # 하트비트
                if current_time - last_heartbeat_time >= heartbeat_interval:
                    await self.send_status_update(confirmed_state, duration=0.0)
                    last_heartbeat_time = current_time
                    print(f"[하트비트] {'Focused' if confirmed_state else 'Unfocused'}")
                
                cv2.imshow('Focus Detection', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\n프로그램이 중단되었습니다.")
        finally:
            # 마지막 상태의 지속 시간 전송
            if confirmed_state_start:
                final_duration = time.time() - confirmed_state_start
                await self.send_status_update(confirmed_state, duration=final_duration)
            
            await self.end_session()
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
