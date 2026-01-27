from fastapi import APIRouter, HTTPException, Query, status, Depends, Body
from typing import Optional
from app.schemas.curriculum import (
    PassageResponse, 
    ListResponse,
    PassageUpdateRequest
)
from app.db.storage import get_db_connection
from app.db.database import select_one, select_all, insert_one
from app.db.passages import (
    get_original_passages_paginated,
    get_custom_passages_paginated,
    get_passage_info,
    create_custom_passage,
    get_project_scope_id,
    update_project_config_status,
    update_passage_use
)
import json
from app.utils.dependencies import get_current_user
from app.schemas.passage import (
    PassageListResponse, 
    PassageUpdateRequest, 
    PassageUpdateResponse, 
    PassageUseRequest
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


def get_scope_ids_by_achievement(achievement_standard_id: int, connection) -> list:
    """
    achievement_standard_id로 scope_id 리스트를 조회합니다.
    project_scopes 테이블의 achievement_ids JSON 필드에서 찾습니다.
    """
    try:
        with connection.cursor() as cursor:
            # JSON_CONTAINS를 사용하여 achievement_ids 배열에 해당 ID가 포함되어 있는지 확인
            sql = """
                SELECT scope_id 
                FROM project_scopes
                WHERE JSON_CONTAINS(achievement_ids, %s)
            """
            # achievement_ids가 JSON 배열([1,5,12])이므로, 찾을 값은 스칼라(예: 1)로 전달해야 매칭됩니다.
            # JSON_CONTAINS([1,5], 1) => true
            cursor.execute(sql, (json.dumps(achievement_standard_id),))
            results = cursor.fetchall()
            return [row['scope_id'] for row in results] if results else []
    except Exception as e:
        print(f"scope_id 조회 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return []

@router.get(
    "/list-by-project",
    response_model=PassageListResponse,
    summary="프로젝트별 지문 리스트 조회 (원본/커스텀 분리)",
    description="프로젝트 ID로 해당 범위의 원본 지문과 커스텀 지문을 분리해서 조회합니다.",
    tags=["지문"]
)
async def get_passages_by_project(
    project_id: int = Query(..., description="프로젝트 ID (필수)", example=1),
    current_user_id: str = Depends(get_current_user)
):
    """
    프로젝트 ID로 지문을 조회합니다.
    """
    try:
        user_id = int(current_user_id)
        
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
        
        # 2. 원본/커스텀 지문 목록과 개수 가져오기 (SQL에서 이미 50자 절삭 처리됨)
        original_list, total_original = get_original_passages_paginated(scope_id)
        custom_list, total_custom = get_custom_passages_paginated(scope_id, user_id)
        
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
        import traceback
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
    description="지문 리스트를 조회합니다. achievement_standard_id와 text_type으로 필터링 가능합니다.",
    tags=["지문"]
)
async def get_passages(
    achievement_standard_id: int = Query(None, description="성취기준 ID", example=1),
    text_type: int = Query(None, description="텍스트 타입 (1: 원본 지문, 2: 커스텀 지문, None: 전체)", example=1),
    scope_id: Optional[int] = Query(None, description="스코프 ID", example=1),
    limit: int = Query(100, description="조회 개수 제한", ge=1, le=1000),
    offset: int = Query(0, description="조회 시작 위치", ge=0),
    current_user_id: str = Depends(get_current_user)
):
    """
    지문 리스트를 반환합니다.
    
    - **achievement_standard_id**: 성취기준 ID (선택사항, 지정 시 해당 성취기준의 지문만 조회)
    - **text_type**: 텍스트 타입 (1: 원본 지문, 2: 커스텀 지문, None: 전체)
    - **scope_id**: 스코프 ID (선택사항, achievement_standard_id보다 우선)
    - **limit**: 조회 개수 제한 (기본값: 100, 최대: 1000)
    - **offset**: 조회 시작 위치 (기본값: 0)
    - **id**: 지문 고유 ID
    - **title**: 지문 제목
    - **content**: 지문 내용 미리보기 (50자로 제한, 전체 내용은 상세/전문 조회 사용)
    - **description**: 지문 설명
    
    **참고**: 리스트 조회에서는 content가 50자로 제한됩니다.
    전체 내용이 필요한 경우 `/passages/{passage_id}` 또는 `/passages/full_content`를 사용하세요.
    """
    connection = get_db_connection()
    if not connection:
        raise HTTPException(
            status_code=500,
            detail="데이터베이스 연결에 실패했습니다."
        )
    
    try:
        user_id = int(current_user_id)
        with connection.cursor() as cursor:
            # scope_id 결정
            scope_ids = []
            if scope_id is not None:
                # scope_id가 직접 제공된 경우
                scope_ids = [scope_id]
            elif achievement_standard_id is not None:
                # achievement_standard_id로 scope_id 리스트 조회
                scope_ids = get_scope_ids_by_achievement(achievement_standard_id, connection)
            
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
                           NULL as description, scope_id, NULL as achievement_standard_id,
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
                           NULL as description, scope_id, NULL as achievement_standard_id,
                           IFNULL(is_use, 1) as is_use,
                           1 as is_custom
                    FROM passage_custom
                    WHERE {where_clause} AND user_id = %s AND IFNULL(is_use, 1) = 1
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
                        SELECT custom_passage_id FROM passage_custom WHERE {where_clause} AND user_id = %s AND IFNULL(is_use, 1) = 1
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
                           NULL as description, scope_id, NULL as achievement_standard_id,
                           1 as is_use,
                           1 as source_type,
                           0 as is_custom
                    FROM passages
                    WHERE {where_clause}
                    
                    UNION ALL
                    
                    SELECT custom_passage_id as id, 
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id, NULL as achievement_standard_id,
                           IFNULL(is_use, 1) as is_use,
                           2 as source_type,
                           1 as is_custom
                    FROM passage_custom
                    WHERE {where_clause} AND user_id = %s AND IFNULL(is_use, 1) = 1
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                list_params = params.copy()
                list_params.extend([user_id, limit, offset])
                cursor.execute(sql, list_params)
                passages = cursor.fetchall()
                
                # achievement_standard_id 추가 및 형식 변환
                items = []
                for passage in passages:
                    item = dict(passage)
                    # achievement_standard_id가 None이면 scope_id로 찾기
                    if item.get('achievement_standard_id') is None and item.get('scope_id'):
                        with connection.cursor() as inner_cursor:
                            inner_sql = """
                                SELECT achievement_ids
                                FROM project_scopes
                                WHERE scope_id = %s
                                LIMIT 1
                            """
                            inner_cursor.execute(inner_sql, (item['scope_id'],))
                            scope_result = inner_cursor.fetchone()
                            if scope_result and scope_result.get('achievement_ids'):
                                try:
                                    achievement_ids_raw = scope_result['achievement_ids']
                                    # JSON 문자열인 경우 파싱
                                    if isinstance(achievement_ids_raw, str):
                                        achievement_ids = json.loads(achievement_ids_raw)
                                    # 이미 리스트인 경우
                                    elif isinstance(achievement_ids_raw, list):
                                        achievement_ids = achievement_ids_raw
                                    else:
                                        achievement_ids = []
                                    
                                    # achievement_ids가 리스트이고 비어있지 않으면 첫 번째 값 사용
                                    if isinstance(achievement_ids, list) and len(achievement_ids) > 0:
                                        first_id = achievement_ids[0]
                                        # 정수로 변환 가능한지 확인
                                        if isinstance(first_id, int):
                                            item['achievement_standard_id'] = first_id
                                        elif isinstance(first_id, str) and first_id.isdigit():
                                            item['achievement_standard_id'] = int(first_id)
                                except:
                                    pass
                    if item.get('achievement_standard_id') is None:
                        item['achievement_standard_id'] = achievement_standard_id or 0
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
            
            # achievement_standard_id 추가 및 형식 변환
            items = []
            for passage in passages:
                item = dict(passage)
                # is_custom 설정 (SQL에서 이미 설정되어 있지만, 명시적으로 정리)
                if text_type == 1:
                    # 원본 지문만: is_custom = 0
                    item['is_custom'] = 0
                elif text_type == 2:
                    # 커스텀 지문만: is_custom = 1
                    item['is_custom'] = 1
                # achievement_standard_id가 None이면 scope_id로 찾기
                if item.get('achievement_standard_id') is None and item.get('scope_id'):
                    with connection.cursor() as inner_cursor:
                        inner_sql = """
                            SELECT achievement_ids
                            FROM project_scopes
                            WHERE scope_id = %s
                            LIMIT 1
                        """
                        inner_cursor.execute(inner_sql, (item['scope_id'],))
                        scope_result = inner_cursor.fetchone()
                        if scope_result and scope_result.get('achievement_ids'):
                            try:
                                achievement_ids_raw = scope_result['achievement_ids']
                                # JSON 문자열인 경우 파싱
                                if isinstance(achievement_ids_raw, str):
                                    achievement_ids = json.loads(achievement_ids_raw)
                                # 이미 리스트인 경우
                                elif isinstance(achievement_ids_raw, list):
                                    achievement_ids = achievement_ids_raw
                                else:
                                    achievement_ids = []
                                
                                # achievement_ids가 리스트이고 비어있지 않으면 첫 번째 값 사용
                                if isinstance(achievement_ids, list) and len(achievement_ids) > 0:
                                    first_id = achievement_ids[0]
                                    # 정수로 변환 가능한지 확인
                                    if isinstance(first_id, int):
                                        item['achievement_standard_id'] = first_id
                                    elif isinstance(first_id, str) and first_id.isdigit():
                                        item['achievement_standard_id'] = int(first_id)
                            except (json.JSONDecodeError, ValueError, TypeError):
                                pass
                # achievement_standard_id가 정수인지 확인하고 설정
                if item.get('achievement_standard_id') is None:
                    item['achievement_standard_id'] = achievement_standard_id if achievement_standard_id else 0
                elif not isinstance(item.get('achievement_standard_id'), int):
                    try:
                        item['achievement_standard_id'] = int(item['achievement_standard_id']) if item['achievement_standard_id'] else 0
                    except (ValueError, TypeError):
                        item['achievement_standard_id'] = 0
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
        import traceback
        error_detail = f"지문 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if connection:
            connection.close()


@router.get(
    "/{passage_id}",
    response_model=PassageResponse,
    summary="지문 상세 조회",
    description="특정 지문의 상세 정보를 조회합니다.",
    tags=["지문"]
)
async def get_passage(
    passage_id: int,
    source_type: Optional[int] = Query(None, description="지문 소스 타입 (1: 원본 지문, 2: 커스텀 지문, None: 자동 검색)", example=1),
    current_user_id: str = Depends(get_current_user)
):
    """
    지문 ID로 특정 지문의 상세 정보를 반환합니다.
    
    - **passage_id**: 지문 ID
    - **source_type**: 지문 소스 타입 (1: passages 테이블, 2: passage_custom 테이블, None: 둘 다 검색)
    """
    connection = get_db_connection()
    if not connection:
        raise HTTPException(
            status_code=500,
            detail="데이터베이스 연결에 실패했습니다."
        )
    
    try:
        user_id = int(current_user_id)
        with connection.cursor() as cursor:
            passage = None
            
            # source_type에 따라 조회
            if source_type == 1:  # 원본 지문만
                sql = """
                    SELECT passage_id as id, title, context as content, 
                           NULL as description, scope_id,
                           1 as is_use
                    FROM passages
                    WHERE passage_id = %s
                """
                cursor.execute(sql, (passage_id,))
                passage = cursor.fetchone()
            elif source_type == 2:  # 커스텀 지문만
                sql = """
                    SELECT custom_passage_id as id, 
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id,
                           IFNULL(is_use, 1) as is_use
                    FROM passage_custom
                    WHERE custom_passage_id = %s AND user_id = %s AND IFNULL(is_use, 1) = 1
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
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id,
                           IFNULL(is_use, 1) as is_use
                    FROM passage_custom
                    WHERE custom_passage_id = %s AND user_id = %s AND IFNULL(is_use, 1) = 1
                """
                cursor.execute(sql, (passage_id, user_id))
                passage = cursor.fetchone()
            
            if not passage:
                raise HTTPException(
                    status_code=404,
                    detail=f"지문 ID {passage_id}를 찾을 수 없습니다."
                )
            
            # scope_id로 achievement_standard_id 찾기
            scope_id = passage.get('scope_id')
            achievement_standard_id = 0
            if scope_id:
                with connection.cursor() as inner_cursor:
                    inner_sql = """
                        SELECT achievement_ids
                        FROM project_scopes
                        WHERE scope_id = %s
                        LIMIT 1
                    """
                    inner_cursor.execute(inner_sql, (scope_id,))
                    scope_result = inner_cursor.fetchone()
                    if scope_result and scope_result.get('achievement_ids'):
                        try:
                            achievement_ids_raw = scope_result['achievement_ids']
                            # JSON 문자열인 경우 파싱
                            if isinstance(achievement_ids_raw, str):
                                achievement_ids = json.loads(achievement_ids_raw)
                            # 이미 리스트인 경우
                            elif isinstance(achievement_ids_raw, list):
                                achievement_ids = achievement_ids_raw
                            else:
                                achievement_ids = []
                            
                            # achievement_ids가 리스트이고 비어있지 않으면 첫 번째 값 사용
                            if isinstance(achievement_ids, list) and len(achievement_ids) > 0:
                                first_id = achievement_ids[0]
                                # 정수로 변환 가능한지 확인
                                if isinstance(first_id, int):
                                    achievement_standard_id = first_id
                                elif isinstance(first_id, str) and first_id.isdigit():
                                    achievement_standard_id = int(first_id)
                        except (json.JSONDecodeError, ValueError, TypeError) as e:
                            print(f"achievement_ids 파싱 오류: {e}, 값: {scope_result.get('achievement_ids')}")
                            achievement_standard_id = 0
            
            # 응답 형식 변환
            item = dict(passage)
            # achievement_standard_id가 정수인지 확인
            if not isinstance(achievement_standard_id, int):
                try:
                    achievement_standard_id = int(achievement_standard_id) if achievement_standard_id else 0
                except (ValueError, TypeError):
                    achievement_standard_id = 0
            
            item['achievement_standard_id'] = achievement_standard_id
            if item.get('description') is None:
                item['description'] = ""
            if item.get('is_use') is None:
                item['is_use'] = 1
            
            return PassageResponse(**item)
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"지문 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if connection:
            connection.close()


@router.get(
    "/search_keyword/{keyword}",
    response_model=ListResponse,
    summary="키워드를 통한 지문 검색",
    description="특정 키워드를 포함하는 지문을 검색합니다.",
    tags=["지문"]
)
async def search_passages_by_keyword(
    keyword: str,
    source_type: Optional[int] = Query(None, description="지문 소스 타입 (1: 원본 지문, 2: 커스텀 지문, None: 전체)", example=1),
    current_user_id: str = Depends(get_current_user)
):
    """
    키워드를 포함하는 지문을 반환합니다.
    
    - **keyword**: 검색할 키워드
    - **source_type**: 지문 소스 타입 (1: passages 테이블만, 2: passage_custom 테이블만, None: 둘 다)
    
    지문의 제목(title), 내용(context)에서 키워드를 검색합니다.
    
    **참고**: 리스트 조회에서는 content가 50자로 제한됩니다.
    전체 내용이 필요한 경우 `/passages/{passage_id}` 또는 `/passages/full_content`를 사용하세요.
    """
    connection = get_db_connection()
    if not connection:
        raise HTTPException(
            status_code=500,
            detail="데이터베이스 연결에 실패했습니다."
        )
    
    try:
        user_id = int(current_user_id)
        with connection.cursor() as cursor:
            search_pattern = f"%{keyword}%"
            
            # source_type에 따라 다른 쿼리 실행
            if source_type == 1:  # 원본 지문만
                sql = """
                    SELECT passage_id as id, title, context as content, 
                           NULL as description, scope_id, NULL as achievement_standard_id
                    FROM passages
                    WHERE title LIKE %s OR context LIKE %s
                    ORDER BY id DESC
                """
                cursor.execute(sql, (search_pattern, search_pattern))
            elif source_type == 2:  # 커스텀 지문만
                sql = """
                    SELECT custom_passage_id as id, 
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id, NULL as achievement_standard_id
                    FROM passage_custom
                    WHERE user_id = %s AND IFNULL(is_use, 1) = 1 AND (custom_title LIKE %s OR title LIKE %s OR context LIKE %s)
                    ORDER BY id DESC
                """
                cursor.execute(sql, (user_id, search_pattern, search_pattern, search_pattern))
            else:  # None: 전체 (원본 + 커스텀)
                sql = """
                    SELECT passage_id as id, title, context as content, 
                           NULL as description, scope_id, NULL as achievement_standard_id
                    FROM passages
                    WHERE title LIKE %s OR context LIKE %s
                    
                    UNION ALL
                    
                    SELECT custom_passage_id as id, 
                           COALESCE(custom_title, title) as title, 
                           context as content,
                           NULL as description, scope_id, NULL as achievement_standard_id
                    FROM passage_custom
                    WHERE user_id = %s AND IFNULL(is_use, 1) = 1 AND (custom_title LIKE %s OR title LIKE %s OR context LIKE %s)
                    ORDER BY id DESC
                """
                cursor.execute(sql, (search_pattern, search_pattern, user_id, search_pattern, search_pattern, search_pattern))
            
            passages = cursor.fetchall()
            
            if not passages:
                raise HTTPException(
                    status_code=404,
                    detail=f"키워드 '{keyword}'를 포함하는 지문을 찾을 수 없습니다."
                )
            
            # 형식 변환
            items = []
            for passage in passages:
                item = dict(passage)
                if item.get('description') is None:
                    item['description'] = ""
                if item.get('achievement_standard_id') is None:
                    item['achievement_standard_id'] = 0
                items.append(item)
            
            # 리스트 조회에서는 content를 50자로 제한
            truncated_passages = [truncate_passage_content(p) for p in items]
            
            return ListResponse(items=truncated_passages, total=len(truncated_passages))
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"지문 검색 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if connection:
            connection.close()


# @router.get(
#     "/full_content",
#     response_model=PassageResponse,
#     summary="지문 전문",
#     description="특정 지문의 전문을 조회합니다.",
#     tags=["지문"]
# )
# async def get_passage_content(
#     passage_id: int = Query(..., description="지문 ID", example=1)
# ):
#     """
#     지문 ID를 기반으로 지문의 전문을 조회합니다.
    
#     - **passage_id**: 지문 ID
#     """
#     connection = get_db_connection()
#     if not connection:
#         raise HTTPException(
#             status_code=500,
#             detail="데이터베이스 연결에 실패했습니다."
#         )
    
#     try:
#         with connection.cursor() as cursor:
#             # 원본 지문에서 먼저 조회
#             sql = """
#                 SELECT passage_id as id, title, context as content, 
#                        NULL as description, scope_id,
#                        1 as is_use
#                 FROM passages
#                 WHERE passage_id = %s
#             """
#             cursor.execute(sql, (passage_id,))
#             passage = cursor.fetchone()
            
#             # 원본 지문에 없으면 커스텀 지문에서 조회
#             if not passage:
#                 sql = """
#                     SELECT custom_passage_id as id, 
#                            COALESCE(custom_title, title) as title, 
#                            context as content,
#                            NULL as description, scope_id,
#                            IFNULL(is_use, 1) as is_use
#                     FROM passage_custom
#                     WHERE custom_passage_id = %s
#                 """
#                 cursor.execute(sql, (passage_id,))
#                 passage = cursor.fetchone()
            
#             if not passage:
#                 raise HTTPException(
#                     status_code=404,
#                     detail=f"지문 ID {passage_id}의 전문을 찾을 수 없습니다."
#                 )
            
#             # scope_id로 achievement_standard_id 찾기
#             scope_id = passage.get('scope_id')
#             achievement_standard_id = 0
#             if scope_id:
#                 with connection.cursor() as inner_cursor:
#                     inner_sql = """
#                         SELECT achievement_ids
#                         FROM project_scopes
#                         WHERE scope_id = %s
#                         LIMIT 1
#                     """
#                     inner_cursor.execute(inner_sql, (scope_id,))
#                     scope_result = inner_cursor.fetchone()
#                     if scope_result and scope_result.get('achievement_ids'):
#                         try:
#                             achievement_ids_raw = scope_result['achievement_ids']
#                             # JSON 문자열인 경우 파싱
#                             if isinstance(achievement_ids_raw, str):
#                                 achievement_ids = json.loads(achievement_ids_raw)
#                             # 이미 리스트인 경우
#                             elif isinstance(achievement_ids_raw, list):
#                                 achievement_ids = achievement_ids_raw
#                             else:
#                                 achievement_ids = []
                            
#                             # achievement_ids가 리스트이고 비어있지 않으면 첫 번째 값 사용
#                             if isinstance(achievement_ids, list) and len(achievement_ids) > 0:
#                                 first_id = achievement_ids[0]
#                                 # 정수로 변환 가능한지 확인
#                                 if isinstance(first_id, int):
#                                     achievement_standard_id = first_id
#                                 elif isinstance(first_id, str) and first_id.isdigit():
#                                     achievement_standard_id = int(first_id)
#                         except (json.JSONDecodeError, ValueError, TypeError) as e:
#                             print(f"achievement_ids 파싱 오류: {e}, 값: {scope_result.get('achievement_ids')}")
#                             achievement_standard_id = 0
            
#             # 응답 형식 변환
#             item = dict(passage)
#             # achievement_standard_id가 정수인지 확인
#             if not isinstance(achievement_standard_id, int):
#                 try:
#                     achievement_standard_id = int(achievement_standard_id) if achievement_standard_id else 0
#                 except (ValueError, TypeError):
#                     achievement_standard_id = 0
            
#             item['achievement_standard_id'] = achievement_standard_id
#             if item.get('description') is None:
#                 item['description'] = ""
#             if item.get('is_use') is None:
#                 item['is_use'] = 1
            
#             return PassageResponse(**item)
            
#     except HTTPException:
#         raise
#     except Exception as e:
#         import traceback
#         error_detail = f"지문 조회 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
#         raise HTTPException(
#             status_code=500,
#             detail=error_detail
#         )
#     finally:
#         if connection:
#             connection.close()


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
    current_user_id: str = Depends(get_current_user)
):
    """
    새로운 지문을 생성하여 passage_custom 테이블에 저장합니다.
    
    **필수 필드:**
    - **title**: 지문 제목
    - **content**: 지문 내용
    - **project_id**: 프로젝트 ID (scope_id와 achievement_standard_id를 자동으로 찾기 위해 사용)
    
    **선택 필드:**
    - **auth**: 작성자
    - **custom_title**: 커스텀 제목
    
    생성된 지문의 ID를 포함한 전체 정보를 반환합니다.
    """
    connection = get_db_connection()
    if not connection:
        raise HTTPException(
            status_code=500,
            detail="데이터베이스 연결에 실패했습니다."
        )
    
    try:
        user_id = int(current_user_id)
        
        with connection.cursor() as cursor:
            # 1) project_id로 프로젝트 소유권 확인 및 scope_id, achievement_standard_id 조회
            project_sql = """
                SELECT 
                    p.scope_id,
                    ps.achievement_ids
                FROM projects p
                LEFT JOIN project_scopes ps ON p.scope_id = ps.scope_id
                WHERE p.project_id = %s AND p.user_id = %s AND p.is_deleted = FALSE
            """
            cursor.execute(project_sql, (project_id, user_id))
            project_result = cursor.fetchone()
            
            if not project_result:
                    raise HTTPException(
                    status_code=404,
                    detail="프로젝트를 찾을 수 없습니다. (권한 없음 또는 삭제됨)"
                )
            
            # scope_id 가져오기
            final_scope_id = project_result.get('scope_id')
            if not final_scope_id:
                    raise HTTPException(
                        status_code=404,
                    detail=f"프로젝트 ID {project_id}에 해당하는 scope_id를 찾을 수 없습니다."
                )
            
            # achievement_ids에서 첫 번째 achievement_standard_id 가져오기
            achievement_standard_id = None
            achievement_ids_raw = project_result.get('achievement_ids')
            if achievement_ids_raw:
                try:
                    # JSON 문자열인 경우 파싱
                    if isinstance(achievement_ids_raw, str):
                        achievement_ids = json.loads(achievement_ids_raw)
                    # 이미 리스트인 경우
                    elif isinstance(achievement_ids_raw, list):
                        achievement_ids = achievement_ids_raw
                    else:
                        achievement_ids = []
                    
                    # achievement_ids가 리스트이고 비어있지 않으면 첫 번째 값 사용
                    if isinstance(achievement_ids, list) and len(achievement_ids) > 0:
                        first_id = achievement_ids[0]
                        # 정수로 변환 가능한지 확인
                        if isinstance(first_id, int):
                            achievement_standard_id = first_id
                        elif isinstance(first_id, str) and first_id.isdigit():
                            achievement_standard_id = int(first_id)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            
            # passage_custom 테이블에 INSERT (source_passage_id는 NULL로 설정)
            sql = """
                INSERT INTO passage_custom (user_id, scope_id, custom_title, title, auth, context, passage_id, is_use)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            """
            cursor.execute(sql, (
                user_id,
                final_scope_id,
                custom_title or title,  # custom_title
                title,  # title
                auth,   # auth (None 가능)
                content,  # context
                None,  # passage_id는 NULL (완전 새로운 지문)
            ))
            # INSERT 직후에 생성된 ID를 먼저 확보
            custom_passage_id = cursor.lastrowid
            connection.commit()
            
            if not custom_passage_id:
                raise HTTPException(
                    status_code=500,
                    detail="지문 생성은 성공했지만 생성된 ID를 가져올 수 없습니다."
                )

            # 생성 직후: 지문 상세 조회와 동일한 응답 형태로 반환
            # source_type=2로 명시하여 커스텀 지문임을 지정
            return await get_passage(custom_passage_id, source_type=2, current_user_id=current_user_id)
            
    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        import traceback
        error_detail = f"지문 생성 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if connection:
            connection.close()


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
    current_user_id: str = Depends(get_current_user)
):
    """
    기존 지문을 기반으로 새로운 지문을 생성하여 passage_custom 테이블에 저장합니다.
    """
    try:
        passage_id = request.passage_id
        user_id = int(current_user_id)
        
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
            where={"user_id": user_id, "is_use": True},
            columns="custom_title"
        )
        print(f"custom_title_list: {custom_title_list}")
        
        # DB에 동일한 제목의 커스텀 지문이 이미 존재하는 경우 제목 변경
        if custom_title in [item.get("custom_title") for item in custom_title_list]:
            print(f"custom_title: {custom_title}")
            print(f"custom_title_list: {custom_title_list}")
            import random, time
            random_suffix = f"_{int(time.time())}_{random.randint(1000, 9999)}"
            custom_title += random_suffix
            title_auto_modified = True

        # 4. 새 커스텀 지문 생성
        # 커스텀 지문의 경우 상속받은 원본 ID(passage_id)를 유지, 원본인 경우 해당 ID를 사용
        original_id = base_info.get("passage_id") if is_custom_source else passage_id

        new_custom_id = create_custom_passage({
            "user_id": user_id,
            "scope_id": scope_id,
            "custom_title": custom_title,
            "title": base_info.get("title"),  # 시스템 원본 제목 유지
            "auth": base_info.get("auth"),    # 원본 저자 정보 유지
            "context": request.content,
            "passage_id": original_id,
            "is_use": 1
        })

        update_project_config_status(request.project_id, 1, new_custom_id)
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
        import traceback
        error_detail = f"지문 수정 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )



@router.post(
    "/delete/{passage_id}",
    status_code=status.HTTP_200_OK,
    summary="지문 삭제(소프트 삭제)",
    description="실제 DELETE가 아니라 passage_custom.is_use=0으로 비활성 처리합니다.",
    tags=["지문"]
)
async def delete_passage(
    passage_id: int,
    is_custom: Optional[int] = Query(None, description="지문 소스 타입 (1: 원본 지문, 2: 커스텀 지문, None: 자동 판단)", example=2),
    current_user_id: str = Depends(get_current_user)
):
    """
    지문 ID를 기반으로 지문을 소프트 삭제 처리합니다.
    
    - **passage_id**: 지문 ID
    - **is_custom**: 지문 소스 타입 (0: passages 테이블, 1: passage_custom 테이블, None: 자동 판단)
    
    주의: 원본 지문(passages)은 삭제할 수 없습니다. source_type=1이면 400 에러를 반환합니다.
    """
    connection = get_db_connection()
    if not connection:
        raise HTTPException(
            status_code=500,
            detail="데이터베이스 연결에 실패했습니다."
        )
    
    try:
        user_id = int(current_user_id)
        with connection.cursor() as cursor:
            # source_type이 1이면 원본 지문 삭제 시도 → 거부
            if is_custom == 0:
                raise HTTPException(
                    status_code=400,
                    detail="원본 지문(passages)은 삭제할 수 없습니다. 커스텀 지문(passage_custom)만 삭제 가능합니다."
                )
            
            # source_type이 2이거나 None인 경우: 커스텀 지문 삭제 시도
            sql = """
                UPDATE passage_custom
                SET is_use = 0
                WHERE custom_passage_id = %s AND user_id = %s
            """
            cursor.execute(sql, (passage_id, user_id))
            updated = cursor.rowcount > 0

            if not updated:
                # source_type이 None이고 커스텀 지문에 없으면 원본 지문인지 확인
                if is_custom is None:
                    check_sql = "SELECT passage_id FROM passages WHERE passage_id = %s"
                    cursor.execute(check_sql, (passage_id,))
                    if cursor.fetchone():
                        raise HTTPException(
                            status_code=400,
                            detail="원본 지문(passages)은 삭제할 수 없습니다. 커스텀 지문(passage_custom)만 삭제 가능합니다."
                        )
                raise HTTPException(
                    status_code=404,
                    detail=f"커스텀 지문 ID {passage_id}를 찾을 수 없습니다."
                )

            connection.commit()
            return {"success": True, "message": "커스텀 지문이 비활성(is_use=0) 처리되었습니다.", "passage_id": passage_id}

    except HTTPException:
        raise
    except Exception as e:
        if connection:
            connection.rollback()
        import traceback
        error_detail = f"지문 소프트 삭제 중 오류가 발생했습니다: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    finally:
        if connection:
            connection.close()




@router.post(
    "/original_used",
    summary="원본 지문 그대로 사용",
    description="원본 지문 그대로 사용",
    tags=["지문"]
)
async def original_used_response(
    request: PassageUseRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    원본 지문 그대로 사용 여부를 조회합니다.
    """
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
        import traceback
        print(traceback.format_exc())
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
    current_user_id: str = Depends(get_current_user)
):
    """
    원본 지문 그대로 사용 여부를 조회합니다.
    """
    print(f"request: {request}")
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
        import traceback
        print(traceback.format_exc())
        return {
            "success": False,
            "message": "요청 처리 중 오류가 발생했습니다.",
            "detail": str(e)
            }
