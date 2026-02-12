from typing import Optional, List, Union
from pydantic import BaseModel, Field


class CurriculumInfo(BaseModel):
    """교육과정 정보"""
    achievement_code: Optional[str] = Field(None, description="성취기준 코드", example="9국06-02")
    achievement_content: Optional[str] = Field(None, description="성취기준 내용", example="자연수의 덧셈을 이해하고 계산할 수 있다.")
    evaluation_content: Optional[str] = Field(None, description="평가기준 내용", example="평가기준.")


class QuestionGeneration(BaseModel):
    """문항 생성 요청 스키마"""
    project_id: int = Field(..., description="프로젝트 ID")
    question_type: str = Field(..., description="문항유형(예:5지선다)")
    stem_directive: Optional[str] = Field(None, description="발문 유형(예:~로 옳은것은)")
    target_count: int = Field(..., description="문항수")
    use_negative_word: bool = Field(..., description="부정어 사용 여부")
    additional_prompt: Optional[str] = Field(None, description="추가 지시사항 (선택사항)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": 1,
                "question_type": "5지선다",
                "stem_directive": "~로 옳은것은",
                "target_count": 10,
                "use_negative_word": False,
                "additional_prompt": "추가 지시사항"
            }
        }



class QuestionGenerationRequest(BaseModel):
    """문항 생성 요청 스키마"""
    config_id: int = Field(..., description="설정 ID")
    project_id: int = Field(..., description="프로젝트 ID")
    project_name: Optional[str] = Field(None, description="프로젝트 이름 (메일 전송용)")
    passage: str = Field(..., description="원본 지문 텍스트")
    passage_title: Optional[str] = Field(None, description="작품 이름")
    passage_author: Optional[str] = Field(None, description="작품 저자")
    learning_objective: str = Field(..., description="학습목표")
    learning_activity: str = Field(default="", description="학습활동")
    learning_element: str = Field(default="", description="학습요소")
    school_level: str = Field(..., description="학교급(초등학교, 중학교, 고등학교)")
    grade_level: str = Field(..., description="대상학년")
    semester: str = Field(..., description="학기")
    large_unit: str = Field(..., description="대단원")
    small_unit: str = Field(..., description="소단원")

    curriculum_info: List[CurriculumInfo] = Field(..., description="교육과정 정보")
    generation_count: int = Field(..., ge=1, le=50, description="생성할 문항 수", example=15)
    study_area: str = Field(default="writing", description="매체 타입 (writing, speaking, listening, reading)", example="writing")
    
    # 문항 생성 관련 필드
    question_type: str = Field(..., description="문항유형(예:5지선다)")
    stem_directive: Optional[str] = Field(None, description="발문 유형(예:~로 옳은것은)")
    use_negative_word: bool = Field(default=False, description="부정어 사용 여부")
    additional_prompt: Optional[str] = Field(None, description="추가 지시사항 (선택사항)")
    file_paths: Optional[List[str]] = Field(
        None, 
        description="업로드할 파일 경로 리스트 (파일명 또는 상대 경로, school_level에 따라 자동으로 분리된 폴더 사용)",
        example=["textbook.pdf", "image1.jpg", "subfolder/document.pdf"]
    )
    file_display_names: Optional[List[str]] = Field(
        None, 
        description="파일 표시 이름 리스트 (file_paths와 동일한 순서)",
        example=["교과서", "이미지 자료", "보조 자료"]
    )

    class Config:
        json_schema_extra = {
            "example":   {
                "config_id": 1,
                "project_id": 1,
                "passage": "여기에 첫 번째 지문 텍스트를 입력합니다...",
                "learning_objective": "상호 작용적 매체의 특성과 소통 맥락을 이해하고 분석할 수 있는가?",
                "curriculum_info": [{
                "achievement_code": "9국06-02",
                "achievement_content": "자연수의 덧셈을 이해하고 계산할 수 있다.",
                "evaluation_content": "평가기준."
                }],
                "generation_count": 30,
                "study_area": "writing",
                "question_type": "5지선다",
                "stem_directive": "~로 옳은것은",
                "use_negative_word": False,
                "additional_prompt": "추가 지시사항",
                "file_paths": ["국어과_교과서론_1권 요약.md", "국어과_교과서론_2권 요약본.md"],
                "file_display_names": ["교과서론 1권", "교과서론 2권"]
            }
        }


class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    code: str = Field(..., description="에러 코드", example="API_ERROR")
    message: str = Field(..., description="에러 메시지")
    details: Optional[str] = Field(None, description="에러 상세 정보")


class Choice(BaseModel):
    """선지 모델"""
    number: int = Field(..., description="문항번호", ge=1, le=5)
    text: str = Field(..., description="선지 내용")


class PassageInfo(BaseModel):
    """지문 정보"""
    original_used: Optional[bool] = Field(default=True, description="제공 지문 사용여부")
    source_type: Optional[str] = Field(default="original", description="지문 출처 타입", example="original, modified, none")
    
    @classmethod
    def model_validate(cls, value):
        """빈 문자열을 기본값으로 변환"""
        if isinstance(value, dict):
            # original_used가 빈 문자열이면 기본값 사용
            if value.get('original_used') == '':
                value['original_used'] = True
            # source_type이 빈 문자열이면 기본값 사용  
            if value.get('source_type') == '':
                value['source_type'] = 'original'
        return super().model_validate(value)


class QuestionText(BaseModel):
    """문제 텍스트"""
    text: str = Field(..., description="발문(문제)")
    modified_passage: Optional[str] = Field(None, description="변형지문")
    box_content: Optional[str] = Field(None, description="보기내용")


class Question(BaseModel):
    """생성된 문항 모델 (기존 구조 유지)"""
    question_id: str = Field(..., description="문제고유값")
    question_number: int = Field(..., description="문제번호")
    passage_info: PassageInfo = Field(..., description="지문 정보")
    question_text: QuestionText = Field(..., description="문제 텍스트")
    choices: Optional[List[Choice]] = Field(None, description="선지 목록 (5지선다: 4~5개, 단답형: null)")
    correct_answer: str = Field(..., description="정답 (5지선다: 번호, 단답형: 텍스트, 여러개인경우 ,로구분)")
    explanation: str = Field(..., description="해설")
    db_question_id: Optional[int] = Field(None, description="데이터베이스에 저장된 문항 ID")
    batch_index: Optional[Union[int, str]] = Field(None, description="배치 인덱스 (숫자 또는 'retry_N')")
    is_used: Optional[int] = Field(None, description="사용 여부 (1: 사용, 0: 여분)")
    llm_difficulty: Optional[int] = Field(None, description="LLM 난이도 (1: 쉬움, 2: 보통, 3: 어려움) - DB 저장 시 자동으로 '쉬움', '보통', '어려움'으로 변환됨")


# LLM 응답용 모델 (기존 실험 코드 구조)
class LLMQuestion(BaseModel):
    """LLM이 생성하는 단일 문항 모델"""
    question_text: str = Field(..., description="문제 문장, 지문 제외")
    reference_text: Optional[str] = Field(default=None, description="보기 내용 (있는 경우)")
    choices: Optional[List[Choice]] = Field(None, description="선지 목록 (5지선다: 5개, 단답형: null)")
    correct_answer: str = Field(..., description="정답 (5지선다: 번호 1~5, 단답형: 답안 텍스트, 복수 답안은 쉼표로 구분)")
    explanation: str = Field(..., description="정답 해설 및 오답 피하기를 포함한 해설")
    passage: Optional[str] = Field(default=None, description="필요한 경우 작성하며 줄바꿈(\\n)을 포함하여 가독성 있게 작성해야 한다.")
    llm_difficulty: Optional[int] = Field(default=None, description="문항 난이도 (1: 쉬움, 2: 보통, 3: 어려움)")
    
    class Config:
        # 빈 문자열을 None으로 변환
        str_strip_whitespace = True


class MultipleQuestion(BaseModel):
    """다중 문항 모델 - LLM이 한 번에 여러 문항을 생성할 때 사용"""
    questions: List[LLMQuestion] = Field(..., description="문제 목록")


class QuestionGenerationErrorResponse(BaseModel):
    """문항 생성 실패 응답"""
    success: bool = Field(False, description="성공여부")
    error: ErrorDetail = Field(..., description="에러 정보")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "API_ERROR",
                    "message": "Gemini API 호출 중 오류가 발생했습니다.",
                    "details": "Rate limit exceeded"
                }
            }
        }


class BatchInfo(BaseModel):
    """배치 생성 정보"""
    batch_number: Union[int, str] = Field(..., description="배치 번호 (숫자 또는 '재요청_N')")
    requested_count: int = Field(..., description="요청한 문항 수")
    generated_count: int = Field(..., description="생성된 문항 수")
    input_tokens: int = Field(0, description="입력 토큰 수")
    output_tokens: int = Field(0, description="출력 토큰 수")
    total_tokens: int = Field(0, description="총 토큰 수")
    duration_seconds: float = Field(0, description="소요 시간 (초)")
    error: Optional[str] = Field(None, description="에러 메시지 (있는 경우)")


class GenerationMetadata(BaseModel):
    """문항 생성 메타데이터"""
    request_index: int = Field(..., description="요청 인덱스")
    achievement_code: str = Field(..., description="성취기준 코드")
    school_level: Optional[str] = Field(None, description="학교급")
    total_questions: int = Field(..., description="총 생성된 문항 수")
    requested_count: int = Field(..., description="요청한 문항 수")
    generated_at: str = Field(..., description="생성 시각 (YYYYMMDD_HHMMSS)")
    batches: List[BatchInfo] = Field(..., description="배치별 상세 정보")


class QuestionGenerationSuccessResponse(BaseModel):
    """문항 생성 성공 응답"""
    success: bool = Field(True, description="성공여부")
    total_questions: int = Field(..., description="생성된 문항 수")
    questions: List[Question] = Field(..., description="생성된 문항 목록")
    metadata: Optional[GenerationMetadata] = Field(None, description="생성 메타데이터 (배치 정보, 토큰 사용량 등)")
    message: Optional[str] = Field(None, description="추가 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_questions": 30,
                "questions": [
                    {
                        "question_id": "123",
                        "question_number": 1,
                        "passage_info": {
                            "original_used": False,
                            "source_type": "modified"
                        },
                        "question_text": {
                            "text": "다음은 민호가 학급 누리집에 올린 글의 일부이다. 물음에 답하시오.",
                            "modified_passage": "안녕하세요, 여러분! 이번 주 금요일 우리 반 대청소인 거 다들 알고 있죠?",
                            "box_content": "[보기]\n㉠ 실시간 상호 작용성\n㉡ 비언어적 표현의 제한"
                        },
                        "choices": [
                            {"number": 1, "text": "민호는 수용자와 실시간으로 소통하고 있다."},
                            {"number": 2, "text": "글의 수정이 불가능한 매체를 활용하고 있다."},
                            {"number": 3, "text": "다수에게 정보를 전달하기에 부적절한 매체이다."},
                            {"number": 4, "text": "공식적인 상황에만 사용 가능한 매체이다."},
                            {"number": 5, "text": "정보의 확산 속도가 매우 느린 매체이다."}
                        ],
                        "correct_answer": "1",
                        "explanation": "학급 누리집은 댓글 기능을 통해 생산자와 수용자가 실시간으로 의견을 주고받을 수 있는 상호 작용적 특성을 가집니다."
                    }
                ]
            }
        }


class BatchJobStartResponse(BaseModel):
    """배치 작업 시작 응답 (백그라운드 처리용)"""
    success: bool = Field(..., description="작업 시작 성공 여부")
    message: str = Field(..., description="응답 메시지")
    batch_count: int = Field(..., description="처리할 배치 요청 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "배치 문항 생성이 백그라운드에서 시작되었습니다. 완료 후 DB에 자동 저장됩니다.",
                "batch_count": 3
            }
        }


class BatchJobErrorResponse(BaseModel):
    """배치 작업 시작 실패 응답"""
    success: bool = Field(False, description="작업 시작 실패")
    message: str = Field(..., description="오류 메시지")
    error: Optional[ErrorDetail] = Field(None, description="에러 상세 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "배치 작업 시작 중 오류가 발생했습니다.",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "요청 데이터가 올바르지 않습니다."
                }
            }
        }

