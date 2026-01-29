from typing import Optional
from pathlib import Path
from app.schemas.question_generation import QuestionGenerationRequest
from app.prompts.common_templates import COMMON_SYSTEM_PROMPT, COMMON_USER_PROMPT
from app.core.logger import logger

# difficulty.md 파일 읽어오기
current_dir = Path(__file__).parent
difficulty_path = current_dir / "difficulty.md"

with open(difficulty_path, "r", encoding="utf-8") as f:
    difficulty_content = f.read()
    logger.debug("difficulty_content: %s", difficulty_content)


class PromptTemplate:
    """프롬프트 템플릿 관리"""
    
    @classmethod
    def build_prompt(
        cls, 
        request: QuestionGenerationRequest,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None
    ) -> tuple[str, str]:
        """
        요청 데이터를 프롬프트 템플릿에 채워서 반환
        
        Args:
            request: 문항 생성 요청
            system_prompt: 시스템 프롬프트 (None이면 매체 타입에 따라 자동 선택)
            user_prompt_template: 사용자 프롬프트 템플릿 (None이면 매체 타입에 따라 자동 선택)
            
        Returns:
            (system_prompt, user_prompt) 튜플
        """

        logger.debug("question_type: %s", request.question_type)
        # 성취기준 정보 텍스트 생성 (여러 개일 수 있음)
        achievement_text = ""
        if request.curriculum_info and len(request.curriculum_info) > 0:
            for idx, ach in enumerate(request.curriculum_info, start=1):
                achievement_code = ach.achievement_code or ""
                achievement_content = ach.achievement_content or ""
                evaluation_content = ach.evaluation_content or ""
                achievement_text += (
                    f"성취기준 코드_{idx} : {achievement_code}\n"
                    f"성취기준_{idx} : {achievement_content}\n"
                    f"평가기준_{idx} : {evaluation_content}\n\n"
                )
        else:
            achievement_text = "성취기준 정보 없음"
        logger.debug("achievement_text: %s", achievement_text)

        if system_prompt is None:
            system_prompt_template = COMMON_SYSTEM_PROMPT

        if user_prompt_template is None:
            user_prompt_template = COMMON_USER_PROMPT


        # 사용자 프롬프트에 변수 채우기
        # 프롬프트에서는 항상 10문항씩 생성하도록 고정
        # question_count와 generation_count 둘 다 전달 (템플릿에 따라 다름)
        system_prompt = system_prompt_template.format(
            school_level=request.school_level,
            grade_level=request.grade_level,
            semester=request.semester,
            large_unit_name=request.large_unit,
            small_unit_name=request.small_unit,
            study_area=request.study_area,
            achievement_text=achievement_text,
            learning_objective=request.learning_objective,
            learning_activity=getattr(request, 'learning_activity', ''),
            learning_element=getattr(request, 'learning_element', ''),
            passage=request.passage,
            passage_title=request.passage_title if hasattr(request, 'passage_title') else None,
            passage_author=request.passage_author if hasattr(request, 'passage_author') else None,
            difficulty_content=difficulty_content
        )
        user_prompt = user_prompt_template.format(
            school_level=request.school_level,
            grade_level=request.grade_level,
            semester=request.semester,
            generation_count=request.generation_count,
            study_area=request.study_area,
            passage=request.passage,
            learning_objective=request.learning_objective,
            learning_activity=getattr(request, 'learning_activity', ''),
            learning_element=getattr(request, 'learning_element', '')
        )

        return system_prompt, user_prompt

