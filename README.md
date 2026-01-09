# 교육과정 관리 API

FastAPI를 사용한 교육과정 관리 API입니다. 대단원, 소단원, 성취기준, 지문을 계층적으로 조회할 수 있습니다.

## 프로젝트 구조

```
dev_dong/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 애플리케이션 진입점
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py          # API 라우터 통합
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── large_units.py          # 대단원 라우터
│   │           ├── small_units.py          # 소단원 라우터
│   │           ├── achievement_standards.py # 성취기준 라우터
│   │           ├── passages.py             # 지문 라우터
│   │           └── question_generation.py  # 문항 생성 라우터
│   ├── clients/                # LLM API 클라이언트
│   │   ├── __init__.py
│   │   ├── base.py             # LLM 클라이언트 기본 인터페이스
│   │   ├── gemini_client.py    # Gemini API 클라이언트
│   │   ├── openai_client.py    # OpenAI API 클라이언트
│   │   └── factory.py          # 클라이언트 팩토리
│   ├── prompts/                # 프롬프트 관리
│   │   ├── __init__.py
│   │   └── templates.py        # 프롬프트 템플릿
│   ├── services/               # 비즈니스 로직
│   │   ├── __init__.py
│   │   └── question_generation_service.py # 문항 생성 서비스
│   ├── tasks/                  # 비동기 작업
│   │   ├── __init__.py
│   │   └── question_generation_task.py    # 문항 생성 비동기 작업
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # 설정 관리
│   ├── models/
│   │   ├── __init__.py
│   │   └── curriculum.py       # 데이터 모델
│   └── schemas/
│       ├── __init__.py
│       ├── curriculum.py       # 교육과정 Pydantic 스키마
│       └── question_generation.py # 문항 생성 Pydantic 스키마
├── scripts/
│   ├── setup.sh                # 초기 설정 스크립트
│   ├── run.sh                  # 개발 모드 실행
│   ├── run_prod.sh             # 프로덕션 모드 실행
│   ├── install.sh              # 의존성 설치
│   ├── stop.sh                 # 서버 중지
│   └── test.sh                 # API 테스트
├── requirements.txt
├── .gitignore
└── README.md
```

## 설치 및 실행

### 방법 1: 스크립트 사용 (권장)

#### 초기 설정 (최초 1회만 실행)
```bash
./scripts/setup.sh
```

#### 개발 모드로 실행
```bash
./scripts/run.sh
```

#### 프로덕션 모드로 실행
```bash
./scripts/run_prod.sh
```

#### 의존성만 재설치
```bash
./scripts/install.sh
```

#### 서버 중지
```bash
./scripts/stop.sh
```

#### API 테스트
```bash
./scripts/test.sh
```

### 방법 2: 수동 실행

#### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

#### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

#### 3. 애플리케이션 실행

```bash
# 개발 모드
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

각 리소스별로 독립적인 라우터가 구성되어 있으며, 현재는 더미 데이터를 사용합니다. 추후 DB 조회로 변경 예정입니다.

### 대단원 (Large Units)

#### 1. 대단원 리스트 조회
```
GET /api/v1/large-units
```

**응답 예시:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "수와 연산",
      "description": "수와 연산에 대한 대단원"
    }
  ],
  "total": 3
}
```

#### 2. 대단원 상세 조회
```
GET /api/v1/large-units/{large_unit_id}
```

### 소단원 (Small Units)

#### 1. 소단원 리스트 조회
```
GET /api/v1/small-units?large_unit_id=1
```

**쿼리 파라미터:**
- `large_unit_id` (필수): 대단원 ID

**응답 예시:**
```json
{
  "items": [
    {
      "id": 1,
      "large_unit_id": 1,
      "name": "자연수의 덧셈",
      "description": "자연수의 덧셈에 대한 소단원"
    }
  ],
  "total": 1
}
```

#### 2. 소단원 상세 조회
```
GET /api/v1/small-units/{small_unit_id}
```

### 성취기준 (Achievement Standards)

#### 1. 성취기준 리스트 조회
```
GET /api/v1/achievement-standards?small_unit_id=1
```

**쿼리 파라미터:**
- `small_unit_id` (필수): 소단원 ID

**응답 예시:**
```json
{
  "items": [
    {
      "id": 1,
      "small_unit_id": 1,
      "code": "1-1-1",
      "content": "자연수의 덧셈을 이해하고 계산할 수 있다.",
      "description": "자연수 덧셈 성취기준"
    }
  ],
  "total": 1
}
```

#### 2. 성취기준 상세 조회
```
GET /api/v1/achievement-standards/{achievement_standard_id}
```

### 지문 (Passages)

#### 1. 지문 리스트 조회
```
GET /api/v1/passages?achievement_standard_id=1
```

**쿼리 파라미터:**
- `achievement_standard_id` (필수): 성취기준 ID

**응답 예시:**
```json
{
  "items": [
    {
      "id": 1,
      "achievement_standard_id": 1,
      "title": "자연수의 덧셈 문제 1",
      "content": "3 + 5 = ?",
      "description": "자연수 덧셈 지문 1"
    }
  ],
  "total": 1
}
```

#### 2. 지문 상세 조회
```
GET /api/v1/passages/{passage_id}
```

## 사용 흐름

1. **대단원 선택**: `GET /api/v1/large-units`로 대단원 리스트 조회
2. **소단원 선택**: 선택한 대단원 ID로 `GET /api/v1/small-units?large_unit_id={id}` 호출
3. **성취기준 선택**: 선택한 소단원 ID로 `GET /api/v1/achievement-standards?small_unit_id={id}` 호출
4. **지문 조회**: 선택한 성취기준 ID로 `GET /api/v1/passages?achievement_standard_id={id}` 호출

## 개발 환경

- Python 3.8+
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.5.0

## 데이터 관리

현재 모든 엔드포인트는 더미 데이터를 사용합니다. 각 라우터 파일(`large_units.py`, `small_units.py`, `achievement_standards.py`, `passages.py`)에 `DUMMY_*` 상수로 정의되어 있으며, `TODO: DB 조회로 변경` 주석이 표시된 부분을 데이터베이스 쿼리로 교체하면 됩니다.

## 문항 생성 API

LLM API를 사용하여 교육 문항을 자동 생성하는 기능입니다.

### 엔드포인트

#### 1. 문항 생성
```
POST /api/v1/question-generation
```

**요청 헤더:**
- `token`: 인증 토큰 (선택사항)

**쿼리 파라미터:**
- `provider`: LLM 제공자 (gemini, openai) - 기본값: gemini
- `async_mode`: 비동기 모드 사용 여부 (true/false) - 기본값: false

**요청 본문:**
```json
{
  "passage": "원본 지문 텍스트",
  "learning_objective": "학습목표",
  "curriculum_info": {
    "achievement_standard": "[9국06-02]",
    "grade_level": "중학교 1학년",
    "main_unit": "바람직한 언어생활",
    "sub_unit": "매체로 소통하기"
  },
  "generation_count": 15,
  "media_type": "writing",
  "file_paths": ["textbook.pdf", "image1.jpg"],
  "file_display_names": ["교과서", "이미지 자료"]
}
```

**파라미터 설명:**
- `file_paths`: 파일명 또는 상대 경로 리스트 (env의 `FILE_STORAGE_PATH` 기준, 절대 경로도 가능)
- `file_display_names`: 파일 표시 이름 리스트 (`file_paths`와 동일한 순서)

#### 2. 배치 문항 생성
```
POST /api/v1/question-generation/batch
```

여러 문항 생성 요청을 한 번에 처리합니다. 최대 10개까지 동시 처리 가능합니다.

#### 3. 사용 가능한 LLM 제공자 조회
```
GET /api/v1/question-generation/providers
```

### 환경 변수 설정

`.env` 파일에 다음 변수를 설정하세요:

```env
# Gemini API (단일 키 또는 여러 키)
GEMINI_API_KEY=your_gemini_api_key
# 또는 여러 키 사용 (콤마로 구분)
GEMINI_API_KEYS=key1,key2,key3,key4,key5

# OpenAI API (선택사항)
OPENAI_API_KEY=your_openai_api_key

# 기본 LLM 제공자
DEFAULT_LLM_PROVIDER=gemini

# API 키 로테이션 전략
API_KEY_ROTATION_STRATEGY=round_robin  # round_robin, random, failover
MAX_PARALLEL_API_KEYS=5  # 병렬 처리에 사용할 최대 API 키 수

# 타임아웃 설정
API_CALL_TIMEOUT=60  # 단일 API 호출 타임아웃 (초)
API_RETRY_TIMEOUT=30  # 재시도 시 타임아웃 (초)
ENABLE_FAST_FAILOVER=True  # 빠른 실패 전환 활성화 (여러 키 동시 시도)

# 데이터베이스 설정 (DB 저장 사용 시)
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_DATABASE=your_database_name

# 파일 저장소 설정
FILE_STORAGE_PATH=./storage/files  # 파일 저장 폴더 경로 (상대 경로 또는 절대 경로)

# Celery 설정 (선택사항 - 대규모 비동기 처리용)
ENABLE_CELERY=False
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**파일 저장소 사용법:**
- `FILE_STORAGE_PATH`를 `.env` 파일에 설정하세요 (기본값: `./storage/files`)
- 요청 시 `file_paths`에 파일명 또는 상대 경로를 지정하면, 자동으로 `FILE_STORAGE_PATH`와 결합됩니다
- **중요**: `grade_level` 값에 따라 파일 경로가 자동으로 분리됩니다
  - 예: `grade_level`이 "중학교 1학년"이면 → `./storage/files/middle_school_1/textbook.pdf`
  - 예: `grade_level`이 "중학교 2학년"이면 → `./storage/files/middle_school_2/textbook.pdf`
  - 예: `grade_level`이 "고등학교 1학년"이면 → `./storage/files/high_school_1/textbook.pdf`
- 절대 경로를 지정한 경우 그대로 사용됩니다

**파일 저장소 구조 예시:**
```
storage/
  └── files/
      ├── middle_school_1/      # 중학교 1학년 파일
      │   ├── textbook.pdf
      │   └── image1.jpg
      ├── middle_school_2/      # 중학교 2학년 파일
      │   └── textbook.pdf
      └── high_school_1/        # 고등학교 1학년 파일
          └── textbook.pdf
```

### 주요 기능

#### 1. 여러 API 키 순환 사용
- 최대 5개의 Gemini API 키를 동시에 사용 가능
- Rate Limit 발생 시 자동으로 다음 키로 전환
- 라운드로빈, 랜덤, Failover 전략 지원

#### 2. 타임아웃 처리 및 빠른 실패 전환
- 각 API 호출에 타임아웃 설정 (기본 60초)
- 타임아웃 발생 시 자동으로 다음 키로 전환
- 빠른 실패 전환 모드: 여러 키를 동시에 시도하고 가장 빠른 응답 사용
- 느린 응답으로 인한 전체 지연 방지

#### 3. 병렬 처리
- 여러 API 키를 사용하여 동시에 문항 생성
- 배치 요청 시 자동으로 병렬 처리
- ThreadPoolExecutor를 사용한 효율적인 리소스 관리
- 각 작업에 개별 타임아웃 설정으로 느린 작업이 전체를 지연시키지 않음

#### 4. 데이터베이스 저장
- 생성된 문항을 자동으로 DB에 저장
- 저장된 `question_id`를 응답에 포함
- 배치 처리 시에도 모든 문항 저장

### 아키텍처 특징

1. **LLM 클라이언트 추상화**: 여러 LLM API를 쉽게 교체 가능
2. **프롬프트 템플릿 관리**: 변수 기반 프롬프트 생성
3. **비동기 처리**: FastAPI BackgroundTasks 또는 Celery 지원
4. **배치 처리**: 여러 요청을 동시에 처리
5. **에러 처리**: 상세한 에러 정보 제공

## 향후 개선 사항

- 데이터베이스 연동 (SQLAlchemy, PostgreSQL 등)
- 인증/인가 기능 추가
- 캐싱 기능 추가
- 로깅 시스템 구축
- 단위 테스트 작성
- Celery를 활용한 대규모 비동기 작업 처리
- LLM 응답 파싱 로직 개선

