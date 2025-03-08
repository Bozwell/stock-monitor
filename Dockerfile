FROM python:3.9-slim

WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# config 디렉토리를 볼륨으로 설정
#VOLUME ["/app/config"]

# 환경 변수 설정
ENV CONFIG_DIR=/app/config

# 실행 권한 설정
RUN chmod +x /app/main.py

CMD ["python", "main.py"] 