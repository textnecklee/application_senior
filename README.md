# Study Tracker - 학습 집중도 추적 시스템

라즈베리파이/웹캠을 사용하여 학습자의 집중도를 실시간으로 추적하고 통계를 제공하는 시스템입니다.

## 프로젝트 구조

```
app/
├── app.py                 # 애플리케이션 진입점
├── camera_client.py       # 웹캠 집중도 감지 클라이언트
├── requirements.txt       # Python 패키지 의존성
└── backend/
    ├── main.py           # FastAPI 서버 메인 파일
    ├── websocket_handler.py  # WebSocket 연결 관리
    ├── models/           # 데이터 모델
    │   ├── database.py
    │   └── study_session.py
    └── routes/           # API 라우트
        ├── study_sessions.py
        ├── stats.py
        └── leaderboard.py
```

## GitHub에서 사용하기

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/study-tracker.git
cd study-tracker/app
```

### 2. 환경 변수 설정

**중요**: `.env` 파일은 GitHub에 올라가지 않습니다. 다음 단계를 따라 설정하세요:

1. 프로젝트 루트에 `.env` 파일을 생성합니다:
   ```bash
   # Windows PowerShell
   New-Item .env
   
   # Linux/Mac
   touch .env
   ```

2. `.env` 파일에 다음 내용을 추가합니다:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

3. 실제 Supabase 프로젝트의 URL과 API Key로 값을 변경합니다.

**보안 주의사항**:
- ⚠️ `.env` 파일은 절대 GitHub에 커밋하지 마세요!
- `.gitignore` 파일에 이미 `.env`가 포함되어 있습니다.
- API Key를 공개 저장소에 올리면 보안 위험이 있습니다.

## 설치 방법

### 1. Python 패키지 설치

```bash
cd app
pip install -r requirements.txt
```

### 2. Supabase 설정

1. [Supabase](https://supabase.com)에서 무료 계정을 생성하고 프로젝트를 만듭니다.

2. Supabase 프로젝트에서 다음 정보를 확인합니다:
   - **Project URL** (예: `https://xxxxx.supabase.co`)
   - **API Key** (anon/public key)

3. 데이터베이스 테이블 생성:
   
   Supabase SQL Editor에서 다음 SQL을 실행하여 `study_sessions` 테이블을 생성합니다:
   
   ```sql
   -- 테이블 생성
   CREATE TABLE study_sessions (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     user_id TEXT NOT NULL,
     start_time TIMESTAMPTZ NOT NULL,
     end_time TIMESTAMPTZ NOT NULL,
     total_time DOUBLE PRECISION NOT NULL,
     focused_time DOUBLE PRECISION NOT NULL,
     unfocused_time DOUBLE PRECISION NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   
   -- 인덱스 생성 (성능 향상)
   CREATE INDEX idx_study_sessions_user_id ON study_sessions(user_id);
   CREATE INDEX idx_study_sessions_start_time ON study_sessions(start_time);
   ```

4. 환경 변수 설정:
   
   Windows (PowerShell):
   ```powershell
   $env:SUPABASE_URL="https://your-project.supabase.co"
   $env:SUPABASE_KEY="your-anon-key"
   ```
   
   Linux/Mac:
   ```bash
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_KEY="your-anon-key"
   ```
   
   또는 `.env` 파일을 생성하여 설정할 수 있습니다:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

## 사용 방법

### 1. 백엔드 서버 실행

터미널 1에서 백엔드 서버를 실행합니다:

```bash
cd app
python app.py
```

또는:

```bash
cd app/backend
python main.py
```

서버가 실행되면 `http://localhost:8000`에서 API를 사용할 수 있습니다.

- API 문서: `http://localhost:8000/docs`
- 헬스 체크: `http://localhost:8000/health`

### 2. 웹캠 클라이언트 실행

터미널 2에서 웹캠 집중도 감지 클라이언트를 실행합니다:

```bash
cd app
python camera_client.py
```

옵션:
- `--server`: 서버 WebSocket URL (기본값: `ws://localhost:8000/ws`)
- `--user`: 사용자 ID (기본값: `user1`)

예시:
```bash
python camera_client.py --user student1
python camera_client.py --server ws://192.168.1.100:8000/ws --user student1
```

**사용법:**
- 웹캠이 자동으로 시작됩니다
- 화면에 집중 상태가 표시됩니다 (집중 중/비집중)
- `q` 키를 눌러 종료합니다

### 3. Flutter 앱에서 API 사용

백엔드 서버가 실행 중이면 Flutter 앱에서 다음 API를 사용할 수 있습니다:

#### 세션 조회
```dart
// 사용자의 세션 목록
GET http://localhost:8000/api/sessions/{user_id}

// 현재 진행 중인 세션
GET http://localhost:8000/api/sessions/{user_id}/current

// 일일 통계
GET http://localhost:8000/api/sessions/{user_id}/daily/{date}

// 주간 통계
GET http://localhost:8000/api/sessions/{user_id}/weekly
```

#### 통계 요약
```dart
GET http://localhost:8000/api/stats/{user_id}/summary
```

#### 리더보드
```dart
// 일일/주간/월간 리더보드
GET http://localhost:8000/api/leaderboard/{period}?limit=100
```

## API 엔드포인트

### 세션 관련
- `GET /api/sessions/{user_id}` - 사용자 세션 목록
- `GET /api/sessions/{user_id}/current` - 현재 진행 중인 세션
- `GET /api/sessions/{user_id}/daily/{date}` - 일일 통계
- `GET /api/sessions/{user_id}/weekly` - 주간 통계

### 통계 관련
- `GET /api/stats/{user_id}/summary` - 사용자 전체 통계 요약

### 리더보드
- `GET /api/leaderboard/{period}` - 리더보드 (period: day, week, month)

## WebSocket 프로토콜

웹캠 클라이언트는 WebSocket을 통해 서버와 통신합니다:

### 메시지 타입

#### 1. 세션 시작
```json
{
  "type": "session_start",
  "user_id": "user1",
  "timestamp": 1234567890.123
}
```

#### 2. 상태 업데이트
```json
{
  "type": "status_update",
  "is_focused": true,
  "timestamp": 1234567890.123
}
```

#### 3. 세션 종료
```json
{
  "type": "session_end",
  "timestamp": 1234567890.123
}
```

## 집중도 감지 알고리즘

웹캠 클라이언트는 MediaPipe를 사용하여:
1. 얼굴 랜드마크 감지
2. 눈 종횡비(EAR - Eye Aspect Ratio) 계산
3. 눈 깜빡임 및 집중 상태 판단

집중 상태는 눈이 열려있는 시간과 깜빡임 빈도를 기반으로 판단됩니다.

## 개발 환경

- Python 3.8+
- FastAPI
- Supabase (PostgreSQL)
- MediaPipe
- OpenCV

## 문제 해결

### 웹캠이 열리지 않는 경우
- 다른 프로그램이 웹캠을 사용 중인지 확인
- 카메라 권한이 허용되어 있는지 확인

### 서버 연결 실패
- 백엔드 서버가 실행 중인지 확인
- 방화벽 설정 확인
- `--server` 옵션으로 올바른 URL 지정

### Supabase 연결 오류
- `SUPABASE_URL`과 `SUPABASE_KEY` 환경 변수가 올바르게 설정되었는지 확인
- Supabase 프로젝트의 API 키가 활성화되어 있는지 확인
- 데이터베이스 테이블이 올바르게 생성되었는지 확인
- Supabase 프로젝트의 네트워크 설정에서 IP 주소가 허용되어 있는지 확인

