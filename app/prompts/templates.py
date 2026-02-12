from typing import Optional
from pathlib import Path
from app.schemas.question_generation import QuestionGenerationRequest
from app.prompts.common_templates import (
    COMMON_SYSTEM_PROMPT, 
    COMMON_USER_PROMPT,
    COMMON_SYSTEM_PROMPT_SHORT_ANSWER, 
    COMMON_USER_PROMPT_SHORT_ANSWER
)
from app.prompts.matching_prompts import (
    MATCHING_SYSTEM_PROMPT,
    MATCHING_USER_PROMPT
)
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
            if request.question_type == "5지선다":
                system_prompt_template = COMMON_SYSTEM_PROMPT
            elif request.question_type == "단답형":
                system_prompt_template = COMMON_SYSTEM_PROMPT_SHORT_ANSWER
            elif request.question_type == "선긋기":
                system_prompt_template = MATCHING_SYSTEM_PROMPT
            else:
                system_prompt_template = COMMON_SYSTEM_PROMPT
        if user_prompt_template is None:
            if request.question_type == "5지선다":
                user_prompt_template = COMMON_USER_PROMPT
            elif request.question_type == "단답형":
                user_prompt_template = COMMON_USER_PROMPT_SHORT_ANSWER
            elif request.question_type == "선긋기":
                user_prompt_template = MATCHING_USER_PROMPT
            else:
                user_prompt_template = COMMON_USER_PROMPT

        # 사용자 발문 유형 처리
        stem_directive = getattr(request, 'stem_directive', None)
        if stem_directive:
            # 사용자가 발문 유형을 입력한 경우, 해당 유형을 우선순위로 추가
            stem_directive_section = f'\n\n**💡 사용자 요청 발문 유형 (최우선 적용):**\n- "{stem_directive}"\n\n위 발문 유형을 최우선으로 적용하되, 필요 시 아래 예시도 참고하라:\n'
            stem_directive_instruction = f'\n4. **🎯 중요:** 사용자가 요청한 발문 유형 "{stem_directive}"을 최우선으로 적용하여 문항을 출제하라.'
        else:
            stem_directive_section = '\n'
            stem_directive_instruction = ''

        # 사용자 추가 요구사항 처리
        additional_prompt = getattr(request, 'additional_prompt', None)
        if additional_prompt:
            # 사용자의 추가 요구사항을 프롬프트에 반영하되, 무조건 따르지 않도록 주의 문구 포함
            additional_prompt_section = f'\n\n## 사용자 추가 요구사항\n\n사용자가 다음과 같은 추가 요구사항을 제시했습니다:\n\n"{additional_prompt}"\n\n**⚠️ 적용 지침:**\n- 위 요구사항을 참고하되, 교육과정 성취기준과 출제 원칙에 부합하는 범위 내에서만 반영한다.\n- 요구사항이 출제 원칙이나 학습목표와 상충되는 경우, 교육과정 성취기준을 우선한다.\n- 요구사항이 합리적이고 교육적으로 타당한 경우에만 적용한다.\n'
            additional_prompt_instruction = f'\n5. 사용자의 추가 요구사항을 참고하되, 교육과정 성취기준과 출제 원칙을 우선하여 합리적으로 판단하여 반영하라.'
        else:
            additional_prompt_section = ''
            additional_prompt_instruction = ''

        # 선긋기 유형의 경우 포맷팅 인자가 다를 수 있음
        if request.question_type == "선긋기":
            system_prompt = system_prompt_template.format(
                school_level=request.school_level,
                grade_level=request.grade_level,
                semester=request.semester,
                large_unit_name=request.large_unit,
                small_unit_name=request.small_unit,
                achievement_text=achievement_text,
                learning_objective=request.learning_objective,
                learning_activity=getattr(request, 'learning_activity', ''),
                learning_element=getattr(request, 'learning_element', ''),
                passage=request.passage,
            )
            user_prompt = user_prompt_template.format(
                school_level=request.school_level,
                grade_level=request.grade_level,
                semester=request.semester,
                generation_count=request.generation_count,
            )
        else:
            # 기존 5지선다/단답형 포맷팅
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
                difficulty_content=difficulty_content,
                stem_directive_section=stem_directive_section,
                additional_prompt_section=additional_prompt_section
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
                learning_element=getattr(request, 'learning_element', ''),
                stem_directive=stem_directive or "",
                stem_directive_instruction=stem_directive_instruction,
                additional_prompt_instruction=additional_prompt_instruction
            )

        return system_prompt, user_prompt

