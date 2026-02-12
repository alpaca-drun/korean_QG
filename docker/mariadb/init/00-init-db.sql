-- 데이터베이스 초기화 스크립트
-- 이 스크립트는 컨테이너 최초 실행 시에만 실행됩니다
-- 데이터가 이미 있는 경우 자동으로 건너뜁니다

-- 환경 변수로 설정된 데이터베이스 사용
-- docker-compose.yml의 MYSQL_DATABASE 환경 변수 값이 자동으로 사용됩니다

-- 타임존 설정
SET TIME_ZONE='+09:00';

-- 문자셋 설정
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

