"""
애플리케이션 진입점
백엔드 서버를 실행합니다.

사용법:
    python app.py
    또는
    cd backend && python main.py
"""

import sys
import os

# backend 디렉토리를 Python 경로에 추가
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

if __name__ == "__main__":
    import uvicorn
    # backend 디렉토리로 이동하여 import 경로 문제 해결
    os.chdir(backend_path)
    from main import app
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
