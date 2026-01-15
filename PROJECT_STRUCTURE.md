# 프로젝트 구조 설명서

## 개요

이 프로젝트는 **교육과정 관리 API**로, FastAPI를 기반으로 한 RESTful API 서버입니다. 대단원, 소단원, 성취기준, 지문을 계층적으로 조회하고, LLM을 활용한 문항 생성 기능을 제공합니다.

## 프로젝트 구조

```
dev_dong/
├── app/                          # 메인 애플리케이션 패키지
│   ├── __init__.py
│   ├── main.py                   # FastAPI 애플리케이션 진입점 및 설정
│   │
│   ├── api/                      # API 라우터 패키지
│   │   ├── __init__.py
│   │   └── v1/                   # API 버전 1
│   │       ├── __init__.py
│   │       ├── api.py            # 모든 엔드포인트 라우터 통합
│   │       └── endpoints/        # 각 리소스별 엔드포인트 라우터
│   │           ├── __init__.py
│   │           ├── large_units.py          # 대단원 라우터
│   │           ├── small_units.py          # 소단원 라우터
│   │           ├── achievement_standards.py # 성취기준 라우터
│   │           ├── passages.py             # 지문 라우터
│   │           └── question_generation.py  # 문항 생성 라우터
│   │
│   ├── clients/                  # LLM API 클라이언트 패키지
│   │   ├── __init__.py
│   │   ├── base.py               # LLM 클라이언트 기본 인터페이스 (추상 클래스)
│   │   ├── gemini_client.py      # Google Gemini API 클라이언트 구현
│   │   ├── openai_client.py      # OpenAI API 클라이언트 구현
│   │   ├── factory.py            # LLM 클라이언트 팩토리 (Provider별 클라이언트 생성)
│   │   └── api_key_manager.py    # API 키 관리 및 로테이션 로직
│   │
│   ├── core/                     # 핵심 설정 및 구성
│   │   ├── __init__.py
│   │   └── config.py             # 애플리케이션 설정 관리 (Pydantic Settings)
│   │
│   ├── db/                       # 데이터베이스 관련 패키지
│   │   ├── __init__.py
│   │   └── storage.py            # 데이터베이스 저장 로직 (문항 저장 등)
│   │
│   ├── models/                   # 데이터 모델 패키지
│   │   ├── __init__.py
│   │   └── curriculum.py         # 교육과정 도메인 모델 (ORM 모델)
│   │
│   ├── prompts/                  # 프롬프트 템플릿 패키지
│   │   ├── __init__.py
│   │   ├── templates.py          # 공통 프롬프트 템플릿 및 유틸리티
│   │   └── writing_prompts.py    # 작문 문항 생성용 프롬프트 템플릿
│   │
│   ├── schemas/                  # Pydantic 스키마 패키지 (요청/응답 검증)
│   │   ├── __init__.py
│   │   ├── curriculum.py         # 교육과정 관련 스키마
│   │   └── question_generation.py # 문항 생성 관련 스키마
│   │
│   ├── services/                 # 비즈니스 로직 서비스 패키지
│   │   ├── __init__.py
│   │   └── question_generation_service.py # 문항 생성 비즈니스 로직
│   │
│   ├── tasks/                    # 비동기 작업 패키지
│   │   ├── __init__.py
│   │   └── question_generation_task.py # 문항 생성 비동기 작업 (Celery 태스크)
│   │
│   ├── utils/                    # 유틸리티 함수 패키지
│   │   ├── __init__.py
│   │   └── file_path.py          # 파일 경로 처리 유틸리티
│   │
│   └── storage/                  # 파일 저장소 (로컬 파일 저장용)
│       └── files/                # 실제 파일 저장 디렉토리
│
├── scripts/                      # 실행 및 관리 스크립트
│   ├── setup.sh                  # 초기 설정 스크립트 (가상환경 생성, 의존성 설치)
│   ├── install.sh                # 의존성 설치 스크립트
│   ├── run.sh                    # 개발 모드 실행 스크립트 (--reload 옵션)
│   ├── run_prod.sh               # 프로덕션 모드 실행 스크립트 (workers 옵션)
│   ├── stop.sh                   # 서버 중지 스크립트
│   └── test.sh                   # API 테스트 스크립트
│
├── venv/                         # Python 가상환경 (gitignore 대상)
├── dev.html                      # 개발용 HTML 파일 (프론트엔드 테스트)
├── requirements.txt              # Python 패키지 의존성 목록
├── .env                          # 환경 변수 설정 파일 (gitignore 대상)
├── .gitignore                    # Git 무시 파일 목록
├── README.md                     # 프로젝트 설명 및 사용법
└── PROJECT_STRUCTURE.md          # 프로젝트 구조 설명서 (본 문서)
```

## 디렉토리별 상세 설명

### `/app` - 메인 애플리케이션 패키지

애플리케이션의 모든 코드가 위치하는 메인 패키지입니다.

#### `/app/main.py`
- FastAPI 애플리케이션 인스턴스 생성 및 설정
- CORS 미들웨어 설정
- API 라우터 등록 (`/api/v1` prefix)
- 전역 예외 핸들러 설정 (JSON 파싱 오류, 요청 검증 오류)
- 기본 엔드포인트 (`/`, `/health`)

#### `/app/api` - API 라우터 계층

**아키텍처 패턴**: RESTful API 디자인

- **`/app/api/v1/api.py`**: 모든 엔드포인트 라우터를 통합하여 하나의 `APIRouter` 인스턴스로 관리
- **`/app/api/v1/endpoints/`**: 각 리소스별로 독립적인 라우터 파일 분리
  - `large_units.py`: 대단원 관련 엔드포인트 (GET `/large-units`, `/large-units/{id}`)
  - `small_units.py`: 소단원 관련 엔드포인트 (GET `/small-units`, `/small-units/{id}`)
  - `achievement_standards.py`: 성취기준 관련 엔드포인트
  - `passages.py`: 지문 관련 엔드포인트
  - `question_generation.py`: 문항 생성 관련 엔드포인트 (POST `/question-generation`, `/batch`, GET `/providers`)

**설계 원칙**:
- 각 리소스별로 독립적인 라우터 파일로 분리하여 관심사 분리
- 버전 관리 (`v1`)로 API 호환성 유지
- FastAPI의 태그 기능으로 Swagger 문서 자동 생성

#### `/app/clients` - LLM API 클라이언트 계층

**아키텍처 패턴**: Strategy 패턴, Factory 패턴, Facade 패턴

- **`base.py`**: LLM 클라이언트 인터페이스 정의 (추상 기본 클래스)
  - 모든 LLM 클라이언트가 구현해야 하는 메서드 정의
  - API 호출, 파일 업로드, 타임아웃 처리 등의 공통 인터페이스

- **`gemini_client.py`**: Google Gemini API 클라이언트 구현
  - 구조화된 출력(JSON Schema) 지원
  - 파일 업로드 및 멀티모달 입력 지원
  - 타임아웃 및 재시도 로직

- **`openai_client.py`**: OpenAI API 클라이언트 구현
  - GPT 모델 지원
  - 구조화된 출력 지원

- **`factory.py`**: Provider별 클라이언트 생성 팩토리
  - `gemini` → `GeminiClient` 인스턴스 반환
  - `openai` → `OpenAIClient` 인스턴스 반환
  - 새로운 LLM Provider 추가 시 확장 가능

- **`api_key_manager.py`**: API 키 관리 및 로테이션
  - 여러 API 키 순환 사용 (Rate Limit 대응)
  - 로테이션 전략: `round_robin`, `random`, `failover`
  - 빠른 실패 전환 (Fast Failover): 여러 키 동시 시도

**설계 원칙**:
- 인터페이스 분리: 새로운 LLM Provider 추가 시 `base.py`를 상속받아 구현만 하면 됨
- 의존성 역전: 서비스 레이어는 추상 인터페이스에만 의존
- 단일 책임: 각 클래스는 하나의 LLM Provider만 담당

#### `/app/core` - 핵심 설정

- **`config.py`**: 애플리케이션 전역 설정 관리
  - Pydantic Settings를 사용한 타입 안전한 설정 관리
  - 환경 변수 자동 로드 (`.env` 파일)
  - LLM API 키, DB 설정, 타임아웃 설정 등

**주요 설정 항목**:
- 애플리케이션 정보 (이름, 버전)
- LLM API 설정 (Gemini, OpenAI API 키, 기본 Provider)
- API 키 로테이션 설정
- 데이터베이스 연결 설정
- 파일 저장소 경로 설정
- 비동기 작업 설정 (Celery)

#### `/app/db` - 데이터베이스 계층

- **`storage.py`**: 데이터베이스 저장 로직
  - 생성된 문항을 DB에 저장하는 함수
  - PyMySQL을 사용한 데이터베이스 연결 및 쿼리 실행

**현재 상태**: 문항 생성 후 DB 저장 기능이 구현되어 있으나, 교육과정 조회는 더미 데이터 사용 중

#### `/app/models` - 도메인 모델

- **`curriculum.py`**: 교육과정 도메인 모델
  - 대단원, 소단원, 성취기준, 지문 등의 데이터 모델 정의
  - ORM 모델 (현재는 더미 데이터 구조 정의)

**향후 계획**: SQLAlchemy ORM 모델로 전환 예정

#### `/app/schemas` - 요청/응답 스키마

**Pydantic 모델**: API 요청 및 응답 데이터 검증

- **`curriculum.py`**: 교육과정 관련 스키마
  - 대단원, 소단원, 성취기준, 지문의 요청/응답 스키마

- **`question_generation.py`**: 문항 생성 관련 스키마
  - 문항 생성 요청 스키마 (`QuestionGenerationRequest`)
  - 문항 생성 응답 스키마 (`QuestionGenerationResponse`)
  - 배치 요청 스키마
  - 유효성 검사 규칙 포함

#### `/app/prompts` - 프롬프트 템플릿

**프롬프트 엔지니어링**: LLM에 전달할 프롬프트 관리

- **`templates.py`**: 공통 프롬프트 템플릿 및 유틸리티 함수
  - 변수 기반 프롬프트 생성 함수
  - 프롬프트 포맷팅 유틸리티

- **`writing_prompts.py`**: 작문 문항 생성용 프롬프트
  - 작문 문항 생성에 특화된 프롬프트 템플릿
  - 학습 목표, 교육과정 정보 반영

**설계 원칙**:
- 프롬프트를 코드에서 분리하여 관리 용이성 향상
- 변수 기반 템플릿으로 재사용성 향상
- 각 문항 유형별로 독립적인 프롬프트 파일

#### `/app/services` - 비즈니스 로직 계층

**아키텍처 패턴**: Service Layer 패턴

- **`question_generation_service.py`**: 문항 생성 비즈니스 로직
  - 프롬프트 생성
  - LLM 클라이언트 호출
  - 응답 파싱 및 검증
  - 파일 경로 처리
  - 에러 처리 및 재시도 로직
  - 배치 처리 로직 (ThreadPoolExecutor 활용)

**책임**:
- API 레이어와 클라이언트 레이어 사이의 비즈니스 로직 처리
- 트랜잭션 관리
- 에러 처리 및 변환

#### `/app/tasks` - 비동기 작업

- **`question_generation_task.py`**: Celery 태스크 정의
  - 대규모 비동기 작업 처리를 위한 Celery 태스크
  - 현재는 FastAPI BackgroundTasks 사용, 향후 Celery 전환 가능

**비동기 처리 방식**:
1. FastAPI BackgroundTasks (기본, 소규모 작업용)
2. Celery (선택사항, 대규모 작업용)

#### `/app/utils` - 유틸리티 함수

- **`file_path.py`**: 파일 경로 처리 유틸리티
  - 학년 레벨에 따른 파일 경로 자동 생성
  - 상대 경로 및 절대 경로 처리
  - 파일 저장소 경로 관리

**주요 기능**:
- `grade_level` 값에 따른 디렉토리 자동 분류
  - 예: "중학교 1학년" → `middle_school_1/`
  - 예: "고등학교 2학년" → `high_school_2/`

### `/scripts` - 실행 스크립트

개발 및 운영 편의를 위한 셸 스크립트 모음.

- **`setup.sh`**: 초기 설정 (가상환경 생성, 의존성 설치)
- **`install.sh`**: 의존성 재설치
- **`run.sh`**: 개발 모드 실행 (`uvicorn --reload`)
- **`run_prod.sh`**: 프로덕션 모드 실행 (`uvicorn --workers 4`)
- **`stop.sh`**: 실행 중인 서버 중지
- **`test.sh`**: API 엔드포인트 테스트

### `/storage` - 파일 저장소

로컬 파일 저장 디렉토리. 학년별로 디렉토리가 자동 생성됨.

```
storage/
└── files/
    ├── middle_school_1/      # 중학교 1학년
    ├── middle_school_2/      # 중학교 2학년
    ├── high_school_1/        # 고등학교 1학년
    └── ...
```

## 아키텍처 패턴 및 설계 원칙

### 1. 계층화 아키텍처 (Layered Architecture)

```
API Layer (endpoints)
    ↓
Service Layer (services)
    ↓
Client Layer (clients)
    ↓
External API (Gemini, OpenAI)
```

각 계층은 명확한 책임을 가지며, 상위 계층은 하위 계층에만 의존합니다.

### 2. 의존성 주입 (Dependency Injection)

- LLM 클라이언트는 Factory를 통해 생성
- 설정은 Pydantic Settings를 통해 중앙 관리
- 서비스는 클라이언트 인터페이스에 의존 (구현체가 아닌)

### 3. Strategy 패턴

- LLM Provider별로 다른 클라이언트 구현
- 런타임에 Provider 선택 가능
- 새로운 Provider 추가 시 기존 코드 수정 불필요

### 4. Factory 패턴

- `clients/factory.py`에서 Provider별 클라이언트 생성
- 클라이언트 생성 로직을 한 곳에 집중

### 5. Repository 패턴 (향후)

- 현재는 더미 데이터 사용
- 향후 DB 연동 시 Repository 패턴 적용 예정

### 6. 관심사의 분리 (Separation of Concerns)

- 각 모듈은 단일 책임을 가짐
- 라우터는 HTTP 요청/응답 처리만
- 서비스는 비즈니스 로직만
- 클라이언트는 API 호출만

## 데이터 흐름

### 문항 생성 요청 흐름

```
1. HTTP Request
   ↓
2. API Endpoint (question_generation.py)
   - 요청 검증 (Pydantic Schema)
   ↓
3. Service Layer (question_generation_service.py)
   - 프롬프트 생성
   - 파일 경로 처리
   ↓
4. Client Factory (factory.py)
   - Provider에 맞는 클라이언트 선택
   ↓
5. LLM Client (gemini_client.py 또는 openai_client.py)
   - API 키 관리 (api_key_manager.py)
   - API 호출
   - 타임아웃 및 재시도 처리
   ↓
6. Service Layer
   - 응답 파싱 및 검증
   ↓
7. DB Storage (storage.py)
   - 생성된 문항 저장 (선택사항)
   ↓
8. HTTP Response
```

### 교육과정 조회 흐름 (현재)

```
1. HTTP Request
   ↓
2. API Endpoint (large_units.py 등)
   ↓
3. 더미 데이터 반환 (향후 DB 조회로 변경)
   ↓
4. HTTP Response
```

## 의존성 관리

### 주요 의존성 (`requirements.txt`)

- **FastAPI**: 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 설정 관리
- **google-generativeai**: Gemini API 클라이언트
- **openai**: OpenAI API 클라이언트
- **httpx**: 비동기 HTTP 클라이언트
- **celery**: 비동기 작업 큐 (선택사항)
- **redis**: Celery 브로커 (선택사항)
- **pymysql**: MySQL 데이터베이스 연결

## 확장성 고려사항

### 1. 새로운 LLM Provider 추가

1. `app/clients/base.py`를 상속받아 새 클라이언트 구현
2. `app/clients/factory.py`에 Provider 등록
3. 환경 변수에 새 Provider의 API 키 추가

### 2. 새로운 문항 유형 추가

1. `app/prompts/`에 새 프롬프트 파일 추가
2. `app/schemas/question_generation.py`에 스키마 확장
3. `app/services/question_generation_service.py`에 로직 추가

### 3. 데이터베이스 연동

1. `app/models/`에 SQLAlchemy 모델 정의
2. `app/api/v1/endpoints/`의 더미 데이터를 DB 쿼리로 교체
3. `app/db/`에 Repository 패턴 구현

## 보안 고려사항

- API 키는 환경 변수로 관리 (`.env` 파일, gitignore 대상)
- 요청 검증은 Pydantic Schema로 자동 처리
- CORS 설정 (현재는 모든 Origin 허용, 프로덕션에서는 제한 필요)
- 타임아웃 설정으로 무한 대기 방지

## 성능 최적화

- **병렬 처리**: 배치 요청 시 ThreadPoolExecutor 사용
- **API 키 로테이션**: Rate Limit 회피
- **빠른 실패 전환**: 여러 API 키 동시 시도
- **비동기 처리**: FastAPI의 async/await 활용
- **타임아웃 설정**: 느린 응답으로 인한 전체 지연 방지

## 향후 개선 계획

1. **데이터베이스 연동**: SQLAlchemy ORM 적용
2. **인증/인가**: JWT 토큰 기반 인증 시스템
3. **캐싱**: Redis를 활용한 응답 캐싱
4. **로깅**: 구조화된 로깅 시스템 (Loguru 등)
5. **테스트**: 단위 테스트 및 통합 테스트 작성
6. **문서화**: API 문서 자동 생성 (Swagger/OpenAPI)
7. **모니터링**: Prometheus, Grafana 등 모니터링 도구 연동

