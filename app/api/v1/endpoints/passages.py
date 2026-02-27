from fastapi import APIRouter, HTTPException, Query, status, Depends, Body
from typing import Optional
from app.schemas.curriculum import (
    PassageResponse, 
    ListResponse,
    PassageUpdateRequest
)
from app.db.database import select_one, select_all, insert_one, get_db_connection
from app.db.passages import (
    get_original_passages_paginated,
    get_custom_passages_paginated,
    get_passage_info,
    create_custom_passage,
    get_project_scope_id,
    insert_without_passage,
    update_project_config_status,
    update_passage_use,
    search_passages_keyword,
    get_scope_ids_by_achievement,
    get_sibling_scope_ids
)
import json
import traceback
from app.utils.dependencies import get_current_user
from app.core.logger import logger
from app.schemas.passage import (
    PassageListResponse, 
    PassageUpdateRequest, 
    PassageUpdateResponse, 
    PassageUseRequest,
    PassageGenerateWithoutPassageRequest
)
router = APIRouter()

# 리스트 조회 시 content 미리보기 최대 길이
CONTENT_PREVIEW_LENGTH = 50


def truncate_passage_content(passage: dict, max_length: int = CONTENT_PREVIEW_LENGTH) -> dict:
    """
    지문의 content를 지정된 길이로 자릅니다.
    
    Args:
        passage: 지문 딕셔너리
        max_length: 최대 길이 (기본값: 50자)
        
    Returns:
        content가 잘린 지문 딕셔너리 (원본은 수정하지 않음)
    """
    truncated = passage.copy()
    content = truncated.get("content") or truncated.get("context", "")
    
    if len(content) > max_length:
        truncated["content"] = content[:max_length] + "..."
    
    return truncated


@router.get(
    "/list-by-project",
    response_model=PassageListResponse,
    summary="프로젝트별 지문 리스트 조회 (원본/커스텀 분리)",
    description="프로젝트 ID로 해당 범위의 원본 지문과 커스텀 지문을 분리해서 조회합니다.",
    tags=["지문"]
)
async def get_passages_by_project(
    project_id: int = Query(..., description="프로젝트 ID (필수)", example=1),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    프로젝트 ID로 지문을 조회합니다.
    """
    user_id, role = user_data
    try:
        
        # 1. project_id로 scope_id 찾기
        scope_id = select_one(
            table="projects",
            where={"project_id": project_id, "user_id": user_id, "is_deleted": False},
            columns="scope_id"
        ).get("scope_id")

        if not scope_id:
            raise HTTPException(
                status_code=404,
                detail="프로젝트를 찾을 수 없거나 범위가 설정되지 않았습니다."
            )
        
        # 2. 같은 소단원의 모든 scope_id 조회 (지문별 learning_activity가 다른 경우 대응)
        sibling_scope_ids = get_sibling_scope_ids(scope_id)
        
        # 3. 원본/커스텀 지문 목록과 개수 가져오기 (SQL에서 이미 50자 절삭 처리됨)
        original_list, total_original = get_original_passages_paginated(sibling_scope_ids)
        custom_list, total_custom = get_custom_passages_paginated(sibling_scope_ids, user_id)
        
        return PassageListResponse(
            success=True,
            message="지문 리스트 조회 성공",
            original=original_list,
            custom=custom_list,
            total_original=total_original,
            total_custom=total_custom
        )
            
    except HTTPException:
        return PassageListResponse(
            success=False,
            message="프로젝트를 찾을 수 없거나 범위가 설정되지 않았습니다.",
            original=[],
            custom=[],
            total_original=0,
            total_custom=0
        )
    except Exception as e:
        logger.exception("지문 리스트 조회 중 오류")
        return PassageListResponse(
            success=False,
            message=f"지문 리스트 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}",
            original=[],
            custom=[],
            total_original=0,
            total_custom=0
        )

@router.get(
    "/list",
    response_model=ListResponse,
    summary="지문 리스트 조회 (미사용)",
    description="지문 리스트를 조회합니다. achievement_code와 text_type으로 필터링 가능합니다.",
    tags=["지문"]
)
async def get_passages(
    achievement_code: Optional[str] = Query(None, description="성취기준 코드", example="9국01-01"),
    text_type: int = Query(None, description="텍스트 타입 (1: 원본 지문, 2: 커스텀 지문, None: 전체)", example=1),
    scope_id: Optional[int] = Query(None, description="스코프 ID", example=1),
    limit: int = Query(100, description="조회 개수 제한", ge=1, le=1000),
    offset: int = Query(0, description="조회 시작 위치", ge=0),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    지문 리스트를 반환합니다.
    
    - **achievement_code**: 성취기준 코드 (선택사항, 지정 시 해당 성취기준의 지문만 조회)
    - **text_type**: 텍스트 타입 (1: 원본 지문, 2: 커스텀 지문, None: 전체)
    - **scope_id**: 스코프 ID (선택사항, achievement_code보다 우선)
    - **limit**: 조회 개수 제한 (기본값: 100, 최대: 1000)
    - **offset**: 조회 시작 위치 (기본값: 0)
    - **id**: 지문 고유 ID
    - **title**: 지문 제목
    - **content**: 지문 내용 미리보기 (50자로 제한, 전체 내용은 상세/전문 조회 사용)
    - **description**: 지문 설명
    
    **참고**: 리스트 조회에서는 content가 50자로 제한됩니다.
    전체 내용이 필요한 경우 `/passages/{passage_id}` 또는 `/passages/full_content`를 사용하세요.
    """
    from app.db.database import select_with_query
    
    user_id, role = user_data
    try:
        with get_db_connection() as connection:
          with connection.cursor() as cursor:
            # scope_id 결정
            scope_ids = []
            if scope_id is not None:
                # scope_id가 직접 제공된 경우
                scope_ids = [scope_id]
            elif achievement_code is not None:
                scope_ids = get_scope_ids_by_achievement(achievement_code, connection=connection)
            
            # WHERE 조건 구성
            where_conditions = []
            params = []
            
            if scope_ids:
                where_conditions.append(f"scope_id IN ({','.join(['%s'] * len(scope_ids))})")
                params.extend(scope_ids)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # text_type에 따라 다른 테이블 조회 또는 UNION
            if text_type == 1:  # 원본 지문만
                sql = f"""
                    SELECT passage_id as id, title, context as content, 
                           NULL as description, scope_id, NULL as achievement_code,
                           1 as is_use,
                           0 as is_custom
                    FROM passages
                    WHERE {where_clause}
                    ORDER BY passage_id DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cursor.execute(sql, params)
            elif text_type == 2:  # 커스텀 지문만
                sql = f"""
                    SELECT custom_passage_id as id, 
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id, NULL as achievement_code,
                           IFNULL(is_used, 1) as is_use,
                           1 as is_custom
                    FROM passage_custom
                    WHERE {where_clause} AND user_id = %s AND IFNULL(is_used, 1) = 1
                    ORDER BY custom_passage_id DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([user_id, limit, offset])
                cursor.execute(sql, params)
            else:  # 전체 (원본 + 커스텀)
                # 전체 개수 조회
                count_sql = f"""
                    SELECT COUNT(*) as total FROM (
                        SELECT passage_id FROM passages WHERE {where_clause}
                        UNION ALL
                        SELECT custom_passage_id FROM passage_custom WHERE {where_clause} AND user_id = %s AND IFNULL(is_used, 1) = 1
                    ) as combined
                """
                count_params = params.copy()
                count_params.append(user_id)
                cursor.execute(count_sql, count_params)
                total_result = cursor.fetchone()
                total = total_result['total'] if total_result else 0
                
                # 리스트 조회
                sql = f"""
                    SELECT passage_id as id, title, context as content, 
                           NULL as description, scope_id, NULL as achievement_code,
                           1 as is_use,
                           1 as source_type,
                           0 as is_custom
                    FROM passages
                    WHERE {where_clause}
                    
                    UNION ALL
                    
                    SELECT custom_passage_id as id, 
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id, NULL as achievement_code,
                           IFNULL(is_used, 1) as is_use,
                           2 as source_type,
                           1 as is_custom
                    FROM passage_custom
                    WHERE {where_clause} AND user_id = %s AND IFNULL(is_used, 1) = 1
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                list_params = params.copy()
                list_params.extend([user_id, limit, offset])
                cursor.execute(sql, list_params)
                passages = cursor.fetchall()
                
                items = []
                for passage in passages:
                    item = dict(passage)
                    if item.get('achievement_code') is None and item.get('scope_id'):
                        with connection.cursor() as inner_cursor:
                            inner_sql = """
                                SELECT JSON_UNQUOTE(JSON_EXTRACT(achievement_ids, '$[0]')) AS first_code
                                FROM project_scopes
                                WHERE scope_id = %s
                                LIMIT 1
                            """
                            inner_cursor.execute(inner_sql, (item['scope_id'],))
                            scope_result = inner_cursor.fetchone()
                            if scope_result and scope_result.get('first_code'):
                                item['achievement_code'] = scope_result['first_code']
                    if item.get('achievement_code') is None:
                        item['achievement_code'] = achievement_code or ""
                    if item.get('description') is None:
                        item['description'] = ""
                    if item.get('is_use') is None:
                        item['is_use'] = 1
                    elif not isinstance(item.get('is_use'), int):
                        try:
                            item['is_use'] = int(item['is_use']) if item['is_use'] is not None else 1
                        except (ValueError, TypeError):
                            item['is_use'] = 1
                    # is_custom 설정 (source_type 기반)
                    if item.get('source_type') == 1:
                        # 원본 지문: is_custom = 0
                        item['is_custom'] = 0
                    elif item.get('source_type') == 2:
                        # 커스텀 지문: is_custom = 1
                        item['is_custom'] = 1
                    # source_type 제거 (응답에 포함하지 않음)
                    item.pop('source_type', None)
                    items.append(item)
                
                # 리스트 조회에서는 content를 50자로 제한
                truncated_passages = [truncate_passage_content(p) for p in items]
                
                return ListResponse(items=truncated_passages, total=total)
            
            # text_type이 1 또는 2인 경우
            passages = cursor.fetchall()
            
            if not passages:
                return ListResponse(items=[], total=0)
            
            items = []
            for passage in passages:
                item = dict(passage)
                if text_type == 1:
                    item['is_custom'] = 0
                elif text_type == 2:
                    item['is_custom'] = 1
                if item.get('achievement_code') is None and item.get('scope_id'):
                    with connection.cursor() as inner_cursor:
                        inner_sql = """
                            SELECT JSON_UNQUOTE(JSON_EXTRACT(achievement_ids, '$[0]')) AS first_code
                            FROM project_scopes
                            WHERE scope_id = %s
                            LIMIT 1
                        """
                        inner_cursor.execute(inner_sql, (item['scope_id'],))
                        scope_result = inner_cursor.fetchone()
                        if scope_result and scope_result.get('first_code'):
                            item['achievement_code'] = scope_result['first_code']
                if item.get('achievement_code') is None:
                    item['achievement_code'] = achievement_code if achievement_code else ""
                if item.get('description') is None:
                    item['description'] = ""
                if item.get('is_use') is None:
                    item['is_use'] = 1
                elif not isinstance(item.get('is_use'), int):
                    try:
                        item['is_use'] = int(item['is_use']) if item['is_use'] is not None else 1
                    except (ValueError, TypeError):
                        item['is_use'] = 1
                items.append(item)
            
            # 리스트 조회에서는 content를 50자로 제한
            truncated_passages = [truncate_passage_content(p) for p in items]
            
            return ListResponse(items=truncated_passages, total=len(truncated_passages))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("지문 조회 중 오류")
        error_detail = f"지문 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.get(
    "/{passage_id}",
    response_model=PassageResponse,
    summary="지문 상세 조회",
    description="특정 지문의 상세 정보를 조회합니다.",
    tags=["지문"]
)
async def get_passage(
    passage_id: int,
    source_type: Optional[int] = Query(None, description="지문 소스 타입 (0: 원본 지문, 1: 커스텀 지문, None: 자동 검색)", example=1),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    지문 ID로 특정 지문의 상세 정보를 반환합니다.
    
    - **passage_id**: 지문 ID
    - **source_type**: 지문 소스 타입 (0: passages 테이블, 1: passage_custom 테이블, None: 둘 다 검색)
    """
    user_id, role = user_data
    try:
        with get_db_connection() as connection:
          with connection.cursor() as cursor:
            passage = None
            
            # source_type에 따라 조회
            if source_type == 0:  # 원본 지문만
                sql = """
                    SELECT passage_id as id, title, context as content, 
                           NULL as description, scope_id,
                           1 as is_use
                    FROM passages
                    WHERE passage_id = %s
                """
                cursor.execute(sql, (passage_id,))
                passage = cursor.fetchone()
            elif source_type == 1:  # 커스텀 지문만
                sql = """
                    SELECT custom_passage_id as id, 
                           title as title, 
                           custom_title as custom_title,
                           context as content,
                           NULL as description, scope_id,
                           IFNULL(is_used, 1) as is_use
                    FROM passage_custom
                    WHERE custom_passage_id = %s AND user_id = %s AND IFNULL(is_used, 1) = 1
                """
                cursor.execute(sql, (passage_id, user_id))
                passage = cursor.fetchone()
            else:  # None: 자동 검색 (원본 먼저, 없으면 커스텀)
                # 원본 지문에서 먼저 조회
                sql = """
                    SELECT passage_id as id, title, context as content, 
                        NULL as description, scope_id,
                        1 as is_use
                    FROM passages
                    WHERE passage_id = %s
                """
                cursor.execute(sql, (passage_id,))
                passage = cursor.fetchone()
            
            # 원본 지문에 없으면 커스텀 지문에서 조회
            if not passage:
                sql = """
                    SELECT custom_passage_id as id, 
                           title as title, 
                           custom_title as custom_title,
                           context as content,
                           NULL as description, scope_id,
                           IFNULL(is_used, 1) as is_use
                    FROM passage_custom
                    WHERE custom_passage_id = %s AND user_id = %s AND IFNULL(is_used, 1) = 1
                """
                cursor.execute(sql, (passage_id, user_id))
                passage = cursor.fetchone()
            
            if not passage:
                raise HTTPException(
                    status_code=404,
                    detail=f"지문 ID {passage_id}를 찾을 수 없습니다."
                )
            
            scope_id = passage.get('scope_id')
            found_code = None
            if scope_id:
                with connection.cursor() as inner_cursor:
                    inner_sql = """
                        SELECT JSON_UNQUOTE(JSON_EXTRACT(achievement_ids, '$[0]')) AS first_code
                        FROM project_scopes
                        WHERE scope_id = %s
                        LIMIT 1
                    """
                    inner_cursor.execute(inner_sql, (scope_id,))
                    scope_result = inner_cursor.fetchone()
                    if scope_result and scope_result.get('first_code'):
                        found_code = scope_result['first_code']
            
            item = dict(passage)
            item['achievement_code'] = found_code or ""
            if item.get('description') is None:
                item['description'] = ""
            if item.get('is_use') is None:
                item['is_use'] = 1
            
            item["message"] = "지문 전문 조회 성공"
            
            return PassageResponse(**item)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("지문 조회 중 오류")
        error_detail = f"지문 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.get(
    "/search_keyword/{keyword}",
    response_model=PassageListResponse,
    summary="키워드를 통한 지문 검색",
    description="특정 키워드를 포함하는 지문을 검색합니다.",
    tags=["지문"]
)
async def search_passages_by_keyword(
    keyword: str,
    source_type: Optional[int] = Query(None, description="지문 소스 타입 (0: 원본 지문, 1: 커스텀 지문, None: 전체)", example=None),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    키워드를 포함하는 지문을 반환합니다.
    
    - **keyword**: 검색할 키워드
    - **source_type**: 지문 소스 타입 (0: passages 테이블만, 1: passage_custom 테이블만, None: 둘 다)
    
    지문의 제목(title), 내용(context)에서 키워드를 검색합니다.
    
    **참고**: 리스트 조회에서는 content가 50자로 제한됩니다.
    전체 내용이 필요한 경우 `/passages/{passage_id}` 또는 `/passages/full_content`를 사용하세요.
    """
    user_id, role = user_data
    try:
        
        # DB 로직을 app/db/passages.py의 함수로 대체
        passages = search_passages_keyword(keyword, user_id, source_type)
        
        # 원본과 커스텀 분리
        original_items = []
        custom_items = []
        
        for passage in passages:
            item = dict(passage)
            
            # DB 조회 단계에서 이미 50자로 절삭되었으므로 그대로 사용
            if item.get('is_custom') == 1:
                custom_items.append(item)
            else:
                original_items.append(item)
        
        return PassageListResponse(
            success=True,
            message=f"키워드 '{keyword}' 검색 결과",
            original=original_items,
            custom=custom_items,
            total_original=len(original_items),
            total_custom=len(custom_items)
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("지문 검색 중 오류")
        error_detail = f"지문 검색 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.post(
    "/create",
    response_model=PassageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 지문 생성",
    description="새로운 지문을 passage_custom 테이블에 생성합니다.",
    tags=["지문"]
)
async def create_passage(
    title: str = Body(..., description="지문 제목", example="자연수의 곱셈 문제"),
    content: str = Body(..., description="지문 내용", example="3 × 5 = ?"),
    project_id: int = Body(..., description="프로젝트 ID", example=1),
    auth: Optional[str] = Body(None, description="작성자", example="작성자"),
    custom_title: Optional[str] = Body(None, description="커스텀 제목", example="내가 만든 지문"),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    새로운 지문을 생성하여 passage_custom 테이블에 저장합니다.
    
    **필수 필드:**
    - **title**: 지문 제목
    - **content**: 지문 내용
    - **project_id**: 프로젝트 ID (scope_id를 자동으로 찾기 위해 사용)
    
    **선택 필드:**
    - **auth**: 작성자
    - **custom_title**: 커스텀 제목
    
    생성된 지문의 ID를 포함한 전체 정보를 반환합니다.
    """
    from app.db.database import select_with_query
    
    user_id, role = user_data
    try:
        
        with get_db_connection() as connection:
            # 1) project_id로 프로젝트 소유권 확인 및 scope_id 조회
            project_sql = """
                SELECT 
                    p.scope_id,
                    ps.achievement_ids
                FROM projects p
                LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
                WHERE p.project_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
            """
            project_result = select_with_query(project_sql, (project_id, user_id), connection=connection)
            
            if not project_result:
                raise HTTPException(
                    status_code=404,
                    detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)"
                )
            
            project_data = project_result[0]
            
            # scope_id 가져오기
            final_scope_id = project_data.get('scope_id')
            if not final_scope_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"프로젝트 ID {project_id}에 해당하는 scope_id를 찾을 수 없습니다."
                )
            
            # 2) 커스텀 지문 생성 (db 함수 사용)
            custom_passage_id = create_custom_passage({
                "user_id": user_id,
                "scope_id": final_scope_id,
                "custom_title": custom_title or title,
                "title": title,
                "auth": auth,
                "context": content,
                "passage_id": None,  # 완전 새로운 지문
                "is_used": 1
            }, connection=connection)
            
            if not custom_passage_id:
                raise HTTPException(
                    status_code=500,
                    detail="지문 생성은 성공했지만 생성된 ID를 가져올 수 없습니다."
                )

        # 생성 직후: 지문 상세 조회와 동일한 응답 형태로 반환
        # source_type=2로 명시하여 커스텀 지문임을 지정
        return await get_passage(custom_passage_id, source_type=2, user_data=user_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("지문 생성 중 오류")
        error_detail = f"지문 생성 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.post(
    "/update",
    response_model=PassageUpdateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="기존 지문을 기반으로 새 지문 생성",
    description="기존 지문(source_passage_id)을 기반으로 새로운 지문을 passage_custom 테이블에 생성합니다.",
    tags=["지문"]
)
async def update_passage(
    request: PassageUpdateRequest,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    기존 지문을 기반으로 새로운 지문을 생성하여 passage_custom 테이블에 저장합니다.
    """
    user_id, role = user_data
    try:
        passage_id = request.passage_id
        
        # 1. 프로젝트 범위(scope_id) 및 소유권 확인
        scope_id = get_project_scope_id(request.project_id, user_id)
        if not scope_id:
            raise HTTPException(
                status_code=404,
                detail="프로젝트를 찾을 수 없거나 범위가 설정되지 않았습니다."
            )

        # 2. 베이스가 되는 지문 정보 조회 (존재 여부 확인)
        is_custom_source = request.is_custom == 1
        base_info = get_passage_info(passage_id, is_custom_source, user_id)
        
        if not base_info:
            type_str = "커스텀" if is_custom_source else "원본"
            raise HTTPException(
                status_code=404,
                detail=f"{type_str} 지문 ID {passage_id}를 찾을 수 없습니다."
            )

        # 3. 제목 중복 방지 로직 (수정 없이 복사될 경우 제목에 난수 추가)
        custom_title = request.custom_title
        title_auto_modified = False

        custom_title_list = select_all(
            table="passage_custom",
            where={"user_id": user_id, "is_used": True},
            columns="custom_title"
        )
        logger.debug("custom_title_list: %s", custom_title_list)
        
        # DB에 동일한 제목의 커스텀 지문이 이미 존재하는 경우 제목 변경
        if custom_title in [item.get("custom_title") for item in custom_title_list]:
            logger.debug("custom_title: %s, custom_title_list: %s", custom_title, custom_title_list)
            import random, time
            random_suffix = f"_{int(time.time())}_{random.randint(1000, 9999)}"
            custom_title += random_suffix
            title_auto_modified = True

        # 4. 새 커스텀 지문 생성 및 프로젝트 설정 업데이트 (단일 트랜잭션)
        # 커스텀 지문의 경우 상속받은 원본 ID(passage_id)를 유지, 원본인 경우 해당 ID를 사용
        original_id = base_info.get("passage_id") if is_custom_source else passage_id

        # 단일 트랜잭션으로 두 작업 수행 (데이터 일관성 보장)
        with get_db_connection() as connection:
            new_custom_id = create_custom_passage({
                "user_id": user_id,
                "scope_id": scope_id,
                "custom_title": custom_title,
                "title": base_info.get("title"),  # 시스템 원본 제목 유지
                "auth": base_info.get("auth"),    # 원본 저자 정보 유지
                "context": request.content,
                "passage_id": original_id,
                "is_used": 1
            }, connection=connection)

            update_project_config_status(request.project_id, 1, new_custom_id, connection=connection)
        # 메시지 설정
        if title_auto_modified:
            message = f"기존 제목과 중복되어 '{custom_title}'로 자동 변경되어 저장되었습니다."
        else:
            message = "지문이 성공적으로 저장되었습니다."
            
        return PassageUpdateResponse(
            success=True,
            message=message,
            passage_id=new_custom_id,
            is_custom=1
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("지문 수정 중 오류")
        error_detail = f"지문 수정 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )



@router.post(
    "/delete/{passage_id}",
    status_code=status.HTTP_200_OK,
    summary="지문 삭제(소프트 삭제)",
    description="실제 DELETE가 아니라 passage_custom.is_used=0으로 비활성 처리합니다.",
    tags=["지문"]
)
async def delete_passage(
    passage_id: int,
    is_custom: Optional[int] = Query(None, description="지문 소스 타입 (0: 원본 지문, 1: 커스텀 지문, None: 자동 판단)", example=2),
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    지문 ID를 기반으로 지문을 소프트 삭제 처리합니다.
    
    - **passage_id**: 지문 ID
    - **is_custom**: 지문 소스 타입 (0: passages 테이블, 1: passage_custom 테이블, None: 자동 판단)
    
    주의: 원본 지문(passages)은 삭제할 수 없습니다. source_type=1이면 400 에러를 반환합니다.
    """
    from app.db.database import update, select_with_query
    
    user_id, role = user_data
    try:
        
        # source_type이 0이면 원본 지문 삭제 시도 → 거부
        if is_custom == 0:
            raise HTTPException(
                status_code=400,
                detail="원본 지문(passages)은 삭제할 수 없습니다. 커스텀 지문(passage_custom)만 삭제 가능합니다."
            )
        
        with get_db_connection() as connection:
            # source_type이 2이거나 None인 경우: 커스텀 지문 삭제 시도 (soft delete)
            updated = update(
                table="passage_custom",
                data={"is_used": 0},
                where={"custom_passage_id": passage_id, "user_id": user_id},
                connection=connection
            )

            if updated <= 0:
                # source_type이 None이고 커스텀 지문에 없으면 원본 지문인지 확인
                if is_custom is None:
                    check_result = select_with_query(
                        "SELECT passage_id FROM passages WHERE passage_id = %s",
                        (passage_id,),
                        connection=connection
                    )
                    if check_result:
                        raise HTTPException(
                            status_code=400,
                            detail="원본 지문(passages)은 삭제할 수 없습니다. 커스텀 지문(passage_custom)만 삭제 가능합니다."
                        )
                raise HTTPException(
                    status_code=404,
                    detail=f"커스텀 지문 ID {passage_id}를 찾을 수 없습니다."
                )

        return {"success": True, "message": "커스텀 지문이 비활성(is_used=0) 처리되었습니다.", "passage_id": passage_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("지문 소프트 삭제 중 오류")
        error_detail = f"지문 소프트 삭제 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )




@router.post(
    "/original_used",
    summary="원본 지문 그대로 사용",
    description="원본 지문 그대로 사용",
    tags=["지문"]
)
async def original_used_response(
    request: PassageUseRequest,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    원본 지문 그대로 사용 여부를 조회합니다.
    """
    user_id, role = user_data
    try:
        if request.is_custom == 0:
            config_id = update_passage_use(request.project_id, 0, request.passage_id)
        elif request.is_custom == 1:
            config_id = update_passage_use(request.project_id, 1, request.passage_id)
        else:
            return {
                "success": False,
                "message": "요청 처리 중 오류가 발생했습니다.",
                "detail": "커스텀 지문 또는 원본 지문을 선택해주세요."
            }
        return {
            "success": True,
            "message": "요청이 정상적으로 처리되었습니다.",
            "config_id": config_id
            }

    except Exception as e:
        logger.exception("요청 처리 중 오류")
        return {
            "success": False,
            "message": "요청 처리 중 오류가 발생했습니다.",
            "detail": str(e)
            }





@router.post(
    "/modified_used",
    summary="지문 수정해서 사용",
    description="지문 수정해서 사용",
    tags=["지문"]
)
async def modified_used_response(
    request: PassageUseRequest,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    원본 지문 그대로 사용 여부를 조회합니다.
    """
    user_id, role = user_data
    logger.debug("request: %s", request)
    try:
        if request.is_custom == 0:
            update_passage_use(request.project_id, 4)
        else:
            update_passage_use(request.project_id, 4)
        return {
            "success": True,
            "message": "요청이 정상적으로 처리되었습니다.",
            }
    except Exception as e:
        logger.exception("요청 처리 중 오류")
        return {
            "success": False,
            "message": "요청 처리 중 오류가 발생했습니다.",
            "detail": str(e)
            }


@router.post(
    "/generate_without_passage",
    summary="지문없이 생성",
    description="지문없이 생성",
    tags=["지문"]
)
async def generate_without_passage(
    request: PassageGenerateWithoutPassageRequest,
    user_data: tuple[int, str] = Depends(get_current_user)
):
    """
    지문없이 생성
    """
    user_id, role = user_data
    try:

        project_id = request.project_id
        project = select_one(
            table="projects",
            where={"project_id": project_id, "user_id": user_id},
            columns="project_id"
        )
        if not project:
            raise HTTPException(
                status_code=404,
                detail="프로젝트를 찾을 수 없습니다. 관리자에게 문의해주세요."
            )

        config_id = insert_without_passage(project_id)
        if not config_id:
            raise HTTPException(
                status_code=404,
                detail="프로젝트 설정값이 확인되지 않습니다. 관리자에게 문의해주세요."
            )


        return {"success": True, "message": "요청이 정상적으로 처리되었습니다.", "config_id": config_id}
    except Exception as e:
        logger.exception("요청 처리 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        )

