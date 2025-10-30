# Frontend Dockerfile for Real Estate for the Young (React + Vite)
# 개발 서버 모드로 실행 -> 서버 이미지는 노드JS 20 이미지 사용
FROM node:20-alpine

# 작업 디렉토리 설정
WORKDIR /app/react

# package.json과 package-lock.json 복사
COPY react/package*.json ./

# 의존성 설치
RUN npm install

#COPY / ADD 소스 코드 복사 -  컨테이너에  복사
COPY react/ ./

# 포트 노출
EXPOSE 3000

# CMD / ENTRYPOSINT : Vite 개발 서버 실행 (--host 옵션으로 외부 접근 허용)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
