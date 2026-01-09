from typing import Optional, List
from pydantic import BaseModel, Field


class CurriculumInfo(BaseModel):
    """교육과정 정보"""
    achievement_standard: str = Field(..., description="성취기준", example="[9국06-02]")
    grade_level: str = Field(..., description="대상학년", example="중학교 1학년")
    main_unit: str = Field(..., description="대단원", example="바람직한 언어생활")
    sub_unit: str = Field(..., description="소단원", example="매체로 소통하기")


class QuestionGenerationRequest(BaseModel):
    """문항 생성 요청 스키마"""
    passage: str = Field(..., description="원본 지문 텍스트")
    learning_objective: str = Field(..., description="학습목표")
    curriculum_info: CurriculumInfo = Field(..., description="교육과정 정보")
    generation_count: int = Field(..., ge=1, le=50, description="생성할 문항 수", example=15)
    media_type: str = Field(default="writing", description="매체 타입 (writing, speaking, listening, reading)", example="writing")
    file_paths: Optional[List[str]] = Field(
        None, 
        description="업로드할 파일 경로 리스트 (파일명 또는 상대 경로, grade_level에 따라 자동으로 분리된 폴더 사용)",
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
                "passage": "여기에 첫 번째 지문 텍스트를 입력합니다...",
                "learning_objective": "상호 작용적 매체의 특성과 소통 맥락을 이해하고 분석할 수 있는가?",
                "curriculum_info": {
                "achievement_standard": "9국06-02",
                "grade_level": "중학교 1학년",
                "main_unit": "바람직한 언어생활",
                "sub_unit": "매체로 소통하기"
                },
                "generation_count": 30,
                "media_type": "writing",
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
    original_used: bool = Field(..., description="제공 지문 사용여부")
    source_type: str = Field(..., description="지문 출처 타입", example="original")


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
    choices: List[Choice] = Field(..., description="선지 목록", min_length=4, max_length=5)
    correct_answer: str = Field(..., description="정답문항")
    explanation: str = Field(..., description="해설")
    db_question_id: Optional[int] = Field(None, description="데이터베이스에 저장된 문항 ID")


# LLM 응답용 모델 (기존 실험 코드 구조)
class LLMQuestion(BaseModel):
    """LLM이 생성하는 단일 문항 모델"""
    question_text: str = Field(..., description="문제 문장, 지문 제외")
    reference_text: Optional[str] = Field(default=None, description="보기 내용 (있는 경우)")
    choices: List[Choice] = Field(..., description="5개의 선지 목록")
    correct_answer: str = Field(..., description="정답 번호 (1,2,3,4,5) 여러개인경우 ,로구분")
    explanation: str = Field(..., description="정답 해설 및 오답 피하기를 포함한 해설")
    passage: Optional[str] = Field(default=None, description="필요한 경우 줄바꿈(\\n)을 포함하여 가독성 있게 작성해야 한다.")
    
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


class QuestionGenerationSuccessResponse(BaseModel):
    """문항 생성 성공 응답"""
    success: bool = Field(True, description="성공여부")
    total_questions: int = Field(..., description="생성된 문항 수")
    questions: List[Question] = Field(..., description="생성된 문항 목록")
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

