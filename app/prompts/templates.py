from typing import Dict, Any, Optional
from app.schemas.question_generation import QuestionGenerationRequest
from app.prompts.writing_prompts import WRITING_SYSTEM_PROMPT, WRITING_USER_PROMPT_TEMPLATE


class PromptTemplate:
    """프롬프트 템플릿 관리"""
    
    BASE_TEMPLATE = """
당신은 교육 문항 생성 전문가입니다. 주어진 지문과 교육과정 정보를 바탕으로 고품질의 객관식 문항을 생성해주세요.

## 지문
{passage}

## 학습목표
{learning_objective}

## 교육과정 정보
- 성취기준: {achievement_standard}
- 대상학년: {grade_level}
- 대단원: {main_unit}
- 소단원: {sub_unit}

## 요구사항
1. 생성할 문항 수: {generation_count}개
2. 각 문항은 4-5개의 선지를 가져야 합니다.
3. 정답과 해설을 포함해야 합니다.
4. 지문을 원본 그대로 사용하거나 변형하여 사용할 수 있습니다.
5. 보기를 포함할 수 있습니다.

## 출력 형식
JSON 형식으로 출력해주세요:
{{
  "questions": [
    {{
      "question_id": "고유ID",
      "question_number": 1,
      "passage_info": {{
        "original_used": true/false,
        "source_type": "original/modified/none"
      }},
      "question_text": {{
        "text": "발문 내용",
        "modified_passage": "변형된 지문 (있는 경우)",
        "box_content": "보기 내용 (있는 경우)"
      }},
      "choices": [
        {{"number": 1, "text": "선지1"}},
        {{"number": 2, "text": "선지2"}},
        {{"number": 3, "text": "선지3"}},
        {{"number": 4, "text": "선지4"}},
        {{"number": 5, "text": "선지5"}}
      ],
      "correct_answer": "정답 번호",
      "explanation": "해설"
    }}
  ]
}}
"""
    
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
        # 매체 타입에 따라 프롬프트 선택
        if system_prompt is None:
            if request.media_type == "writing":
                system_prompt = WRITING_SYSTEM_PROMPT
            else:
                # 기본 프롬프트 (다른 매체 타입은 추후 추가)
                system_prompt = cls.BASE_TEMPLATE
        
        # media_type에 따라 프롬프트 템플릿 변경
        if user_prompt_template is None:
            if request.media_type == "writing":
                user_prompt_template = WRITING_USER_PROMPT_TEMPLATE
            else:
                # 기본 템플릿
                user_prompt_template = cls.BASE_TEMPLATE
        
        # 사용자 프롬프트에 변수 채우기
        # 프롬프트에서는 항상 10문항씩 생성하도록 고정
        # question_count와 generation_count 둘 다 전달 (템플릿에 따라 다름)
        user_prompt = user_prompt_template.format(
            question_count=10,  # 항상 10문항 고정 (WRITING_USER_PROMPT_TEMPLATE용)
            generation_count=10,  # 항상 10문항 고정 (BASE_TEMPLATE용)
            passage=request.passage,
            learning_objective=request.learning_objective,
            achievement_standard=request.curriculum_info.achievement_standard,
            grade_level=request.curriculum_info.grade_level,
            main_unit=request.curriculum_info.main_unit,
            sub_unit=request.curriculum_info.sub_unit
        )
        
        return system_prompt, user_prompt
    
    @classmethod
    def build_custom_prompt(
        cls,
        passage: str,
        learning_objective: str,
        curriculum_info: Dict[str, Any],
        generation_count: int,
        custom_instructions: str = ""
    ) -> str:
        """
        커스텀 프롬프트 생성
        
        Args:
            passage: 지문
            learning_objective: 학습목표
            curriculum_info: 교육과정 정보 딕셔너리
            generation_count: 생성할 문항 수
            custom_instructions: 추가 지시사항
            
        Returns:
            완성된 프롬프트 문자열
        """
        prompt = cls.BASE_TEMPLATE.format(
            passage=passage,
            learning_objective=learning_objective,
            achievement_standard=curriculum_info.get("achievement_standard", ""),
            grade_level=curriculum_info.get("grade_level", ""),
            main_unit=curriculum_info.get("main_unit", ""),
            sub_unit=curriculum_info.get("sub_unit", ""),
            generation_count=generation_count
        )
        
        if custom_instructions:
            prompt += f"\n\n## 추가 지시사항\n{custom_instructions}"
        
        return prompt

