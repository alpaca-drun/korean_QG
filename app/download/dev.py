from docx import Document
from copy import deepcopy
import os
from dotenv import load_dotenv
import sys

# 실행 위치에 상관없이 import 되도록 경로 보정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# app/download/database.py 사용
from app.db.storage import get_db_connection


def execute_query_via_app_db(query: str, params: tuple | None = None, fetch: bool = True):
    """
    app/db/storage.py의 get_db_connection()을 사용해서 쿼리를 실행합니다.
    (FastAPI 서버와 동일한 settings/db 환경변수를 사용)
    """
    connection = get_db_connection()
    if not connection:
        raise ValueError("DB 연결 실패: settings.db_host/db_user/db_password/db_database 설정을 확인하세요.")
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()

# .env 파일에서 환경변수 로드
load_dotenv()
def get_cell_text(table, row, col):
    try:
        cell = table.cell(row, col)
        text = cell.text.strip()
        if not text and col > 0:
            text = table.cell(row, col - 1).text.strip()
        return text
    except IndexError:
        return ""
def find_table_in_cell(cell, tag, doc=None):
    """
    셀 안에 있는 표를 재귀적으로 찾는 함수
    
    Args:
        cell: 셀 객체
        tag: 찾을 태그 문자열
        doc: Document 객체 (표 객체 생성 시 필요)
    
    Returns:
        찾은 Table 객체 또는 None
    """
    from docx.table import Table
    
    # 셀 안의 모든 표 요소 찾기 (XPath 사용)
    try:
        # lxml의 xpath 사용
        tbl_elements = cell._element.xpath('.//w:tbl', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
    except:
        # xpath가 없는 경우 직접 찾기
        tbl_elements = []
        for elem in cell._element.iter():
            if elem.tag.endswith('}tbl'):
                tbl_elements.append(elem)
    
    for tbl_elm in tbl_elements:
        try:
            # 표 객체 생성 (doc이 필요함)
            if doc is not None:
                nested_table = Table(tbl_elm, doc)
            else:
                # doc이 없으면 직접 접근 시도
                nested_table = Table(tbl_elm, cell._parent._parent)
            
            # 표 안의 모든 셀 검색
            for row in nested_table.rows:
                for nested_cell in row.cells:
                    cell_text = nested_cell.text
                    if tag in cell_text:
                        print(f"✅ 중첩 표를 찾았습니다! (셀 안의 표)")
                        print(f"   찾은 셀 내용: {cell_text[:100]}")
                        return nested_table
            
            # 중첩 표 안에 또 다른 표가 있을 수 있으므로 재귀적으로 검색
            for row in nested_table.rows:
                for nested_cell in row.cells:
                    result = find_table_in_cell(nested_cell, tag, doc)
                    if result:
                        return result
        except Exception as e:
            # 표 객체 생성 실패 시 다음 표로
            continue
    
    return None

def find_career_table(doc, tag="{nu}"):
    """
    표에서 특정 태그를 포함한 표를 찾는 함수 (중첩 표 포함)
    
    Args:
        doc: Document 객체
        tag: 찾을 태그 문자열 (기본값: "{nu}")
    
    Returns:
        찾은 Table 객체 또는 None
    """
    # 최상위 레벨의 표 검색
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                # 셀의 텍스트 직접 가져오기
                cell_text = cell.text
                if tag in cell_text:
                    print(f"✅ 표를 찾았습니다! (표 인덱스: {table_idx}, 행: {row_idx}, 열: {col_idx})")
                    print(f"   찾은 셀 내용: {cell_text[:100]}")
                    return table
                
                # 셀 안에 중첩된 표가 있는지 확인
                nested_table = find_table_in_cell(cell, tag, doc)
                if nested_table:
                    return nested_table
    
    print(f"❌ '{tag}' 태그를 포함한 표를 찾을 수 없습니다.")
    # 디버깅: 모든 표의 첫 번째 셀 내용 출력
    print("\n📋 디버깅 정보 - 모든 표의 첫 번째 셀 내용:")
    for table_idx, table in enumerate(doc.tables):
        if len(table.rows) > 0 and len(table.rows[0].cells) > 0:
            first_cell_text = table.rows[0].cells[0].text[:50]
            print(f"   표 {table_idx}: {first_cell_text}...")
    return None
def extract_category_from_info_id(info_id):
    """
    CREATE_INFO_ID에서 카테고리 값을 추출하는 함수
    예: "말하기듣기_30-05-05" -> "말하기듣기"
    
    Args:
        info_id: 정보 ID 문자열
    
    Returns:
        카테고리 문자열 (없으면 빈 문자열)
    """
    if not info_id:
        print("📝 [카테고리 추출] info_id가 없습니다.")
        return ""
    
    # 언더스코어로 분리하여 첫 번째 부분 추출
    parts = str(info_id).split('_')
    if len(parts) > 0:
        category = parts[0]
        print(f"📝 [카테고리 추출] '{info_id}' → '{category}'")
        return category
    print(f"📝 [카테고리 추출] '{info_id}'에서 카테고리를 추출할 수 없습니다.")
    return ""

def replace_document_text(doc, replacements):
    """
    문서 전체에서 플레이스홀더를 교체하는 함수 (표 외부의 텍스트 포함)
    
    Args:
        doc: Document 객체
        replacements: 플레이스홀더와 값의 딕셔너리 (예: {'{category}': '말하기듣기'})
    """
    print(f"📄 [문서 플레이스홀더 교체] 시작 (교체할 항목: {len(replacements)}개)")
    replaced_count = 0
    
    # 문서의 모든 단락에서 교체
    for paragraph in doc.paragraphs:
        if paragraph.text:
            new_text = paragraph.text
            for placeholder, value in replacements.items():
                if placeholder in new_text:
                    new_text = new_text.replace(placeholder, value)
                    replaced_count += 1
            
            if new_text != paragraph.text:
                # 단락 내용 교체
                paragraph.clear()
                if new_text:
                    paragraph.add_run(new_text)
    
    # 표 안의 셀에서도 교체 (표 내부는 replace_table_text에서 처리되지만, 
    # 표 외부의 플레이스홀더를 위해 여기서도 처리)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if paragraph.text:
                        new_text = paragraph.text
                        for placeholder, value in replacements.items():
                            if placeholder in new_text:
                                new_text = new_text.replace(placeholder, value)
                                replaced_count += 1
                        
                        if new_text != paragraph.text:
                            paragraph.clear()
                            if new_text:
                                paragraph.add_run(new_text)
    
    print(f"📄 [문서 플레이스홀더 교체] 완료 (총 {replaced_count}개 교체)")

def fill_table_from_list(doc_path, output_path, data_list, category=""):
    """
    sample.docx의 표를 복사하여 리스트 데이터로 채우는 함수
    
    Args:
        doc_path: 원본 docx 파일 경로
        output_path: 출력 파일 경로
        data_list: 표를 채울 데이터 리스트 (각 항목은 dict 형태)
                  예: [{'nu': 1, 'question': '질문1', 'select1': '선택1', ...}, ...]
        category: 카테고리 문자열 (예: "말하기듣기", "쓰기", "매체")
    """
    print(f"\n{'='*60}")
    print(f"📋 [문서 처리 시작]")
    print(f"   입력 파일: {doc_path}")
    print(f"   출력 파일: {output_path}")
    print(f"   데이터 개수: {len(data_list)}개")
    print(f"   카테고리: {category if category else '(없음)'}")
    print(f"{'='*60}\n")
    
    # 원본 문서 열기
    print(f"📂 [1/5] 문서 열기 중...")
    doc = Document(doc_path)
    print(f"   ✅ 문서 열기 완료 (표 개수: {len(doc.tables)}개)")
    
    # 카테고리 플레이스홀더 교체 (문서 전체)
    if category:
        print(f"\n📝 [2/5] 카테고리 플레이스홀더 교체 중...")
        replace_document_text(doc, {'{category}': category})
    else:
        print(f"\n📝 [2/5] 카테고리 플레이스홀더 교체 건너뜀 (카테고리 없음)")
    
    # 첫 번째 표 찾기 (원본 표)
    print(f"\n🔍 [3/5] 표 찾기 중...")
    if len(doc.tables) == 0:
        print("   ❌ 표를 찾을 수 없습니다!")
        return
    
    # {nu} 플레이스홀더가 포함된 표 찾기
    original_table = find_career_table(doc, "{nu}")
    if original_table is None:
        print("   ❌ {nu} 태그가 포함된 표를 찾을 수 없습니다.")
        return
    
    print(f"   ✅ 원본 표 찾기 완료")

    # 원본 표의 element를 저장 (플레이스홀더가 있는 원본 상태를 먼저 저장)
    print(f"\n📊 [4/5] 표 데이터 채우기 중...")
    original_table_elm = deepcopy(original_table._element)
    previous_table_elm = original_table._element
    
    num = 1
    # 첫 번째 데이터로 원본 표 채우기
    if data_list:
        print(f"   📝 표 {num}/{len(data_list)} 채우는 중...", end="", flush=True)
        replace_table_text(original_table, data_list[0], num)
        print(f" ✅")
        
        # 나머지 데이터에 대해 표 복사 및 채우기
        for data in data_list[1:]:
            num += 1 
            print(f"   📝 표 {num}/{len(data_list)} 채우는 중...", end="", flush=True)
            
            # 원본 표 element 복사 (플레이스홀더가 있는 원본 상태로 복사)
            new_table_elm = deepcopy(original_table_elm)
            
            # 이전 표 다음에 줄바꿈(단락) 추가
            from docx.oxml import OxmlElement
            
            # 단락 요소 생성 (빈 줄)
            p = OxmlElement('w:p')
            previous_table_elm.addnext(p)
            
            # 단락 다음에 새 표 삽입
            p.addnext(new_table_elm)
            
            # 새로 추가된 표를 Document 객체로 찾기
            new_table_obj = None
            for t in doc.tables:
                if t._element == new_table_elm:
                    new_table_obj = t
                    break
            
            if new_table_obj:
                replace_table_text(new_table_obj, data, num)
                previous_table_elm = new_table_elm
            print(f" ✅")
    
    # 결과 저장
    print(f"\n💾 [5/5] 파일 저장 중...")
    doc.save(output_path)
    print(f"   ✅ 저장 완료!")
    print(f"\n{'='*60}")
    print(f"🎉 완료! {len(data_list)}개의 표가 생성되어 {output_path}에 저장되었습니다.")
    print(f"{'='*60}\n")

def get_project_id_from_env_or_arg(project_id: str | int | None = None) -> int:
    """
    프로젝트 ID를 환경변수/인자에서 안전하게 가져옵니다.

    우선순위:
    - 인자 project_id
    - PROJECT_ID
    - CREATE_PROJECT_ID
    - CREATE_INFO_ID (기존 호환: 숫자면 project_id로 간주)
    """
    if project_id is None:
        project_id = (
            os.getenv("PROJECT_ID")
            or os.getenv("CREATE_PROJECT_ID")
            or os.getenv("CREATE_INFO_ID")
        )
    if not project_id:
        raise ValueError("PROJECT_ID 환경변수가 설정되지 않았습니다. (또는 CREATE_PROJECT_ID/CREATE_INFO_ID 숫자값)")
    try:
        return int(str(project_id).strip())
    except ValueError:
        raise ValueError(f"PROJECT_ID가 정수가 아닙니다: {project_id}")


def get_project_passage_text(project_id: int, user_id: int | None = None) -> str:
    """
    project_source_config를 기반으로 프로젝트의 지문(원본/커스텀)을 가져옵니다.
    - custom_passage_id가 있으면 passage_custom.context
    - passage_id가 있으면 passages.context
    """
    query = """
        SELECT
            psc.custom_passage_id,
            psc.passage_id,
            pc.context AS custom_context,
            ps.context AS passage_context
        FROM project_source_config psc
        LEFT JOIN passage_custom pc ON pc.custom_passage_id = psc.custom_passage_id
        LEFT JOIN passages ps ON ps.passage_id = psc.passage_id
        WHERE psc.project_id = %s
        ORDER BY psc.created_at DESC
        LIMIT 1
    """
    # 프로젝트 소유권 검증(선택)
    if user_id is not None:
        ownership = execute_query_via_app_db(
            "SELECT project_id FROM projects WHERE project_id = %s AND user_id = %s AND is_deleted = 0 LIMIT 1",
            params=(project_id, user_id),
            fetch=True,
        )
        if not ownership:
            return ""

    results = execute_query_via_app_db(query, params=(project_id,), fetch=True)
    if not results:
        return ""
    row = results[0] or {}
    return (row.get("custom_context") or row.get("passage_context") or "").strip()


def get_question_data_from_db(project_id: int | None = None, user_id: int | None = None):
    """
    DB에서 질문(객관식/단답형/OX) 데이터를 가져오는 함수
    
    Args:
        project_id: 프로젝트 ID
    
    Returns:
        질문 데이터 리스트 (각 항목은 dict 형태)
    """
    # project_id_int = get_project_id_from_env_or_arg(project_id)
    project_id_int = project_id
    passage_text = get_project_passage_text(project_id_int, user_id=user_id)
    print(f"passage_text: {passage_text}")
    
    # ✅ 현재 DB 스키마 기반: multiple_choice_questions / short_answer_questions / true_false_questions
    # seq는 생성시간 기준으로 부여
    query = """
        (
            SELECT
                mcq.question_id AS qid,
                mcq.created_at AS created_at,
                mcq.question AS question,
                mcq.option1 AS select1,
                mcq.option2 AS select2,
                mcq.option3 AS select3,
                mcq.option4 AS select4,
                mcq.option5 AS select5,
                mcq.answer AS answer,
                mcq.answer_explain AS answer_explain,
                mcq.box_content AS box_content,
                1 AS qtype
            FROM multiple_choice_questions mcq
            JOIN projects p ON p.project_id = mcq.project_id
            WHERE mcq.project_id = %s
        )
        UNION ALL
        (
            SELECT
                saq.short_question_id AS qid,
                saq.created_at AS created_at,
                saq.question AS question,
                NULL AS select1,
                NULL AS select2,
                NULL AS select3,
                NULL AS select4,
                NULL AS select5,
                saq.answer AS answer,
                saq.answer_explain AS answer_explain,
                saq.box_content AS box_content,
                2 AS qtype
            FROM short_answer_questions saq
            JOIN projects p2 ON p2.project_id = saq.project_id
            WHERE saq.project_id = %s
        )
        UNION ALL
        (
            SELECT
                tfq.ox_question_id AS qid,
                tfq.created_at AS created_at,
                tfq.question AS question,
                'O' AS select1,
                'X' AS select2,
                NULL AS select3,
                NULL AS select4,
                NULL AS select5,
                tfq.answer AS answer,
                tfq.answer_explain AS answer_explain,
                NULL AS box_content,
                3 AS qtype
            FROM true_false_questions tfq
            JOIN projects p3 ON p3.project_id = tfq.project_id
            WHERE tfq.project_id = %s
        )
        ORDER BY qid ASC
    """
    
    # DB 연결 설정 확인 (try 블록 밖에서 정의하여 except에서도 사용 가능)
    # env_prefix = os.getenv('DB_ENV_PREFIX', 'QG_db')
    # database = os.getenv('DB_DATABASE', 'midtest')
    
    try:
        
        # print(f"🔌 [DB 연결] project_id={project_id_int}로 데이터 조회 중...")
        # print(f"   환경변수 접두사: {env_prefix}")
        # print(f"   데이터베이스: {database}")
        
        # # 환경변수 확인
        # host = os.getenv(f'{env_prefix}_host')
        # user = os.getenv(f'{env_prefix}_user')
        # password = os.getenv(f'{env_prefix}_password')
        
        # if not host:
        #     print(f"   ⚠️ 경고: {env_prefix}_host 환경변수가 설정되지 않았습니다.")
        # if not user:
        #     print(f"   ⚠️ 경고: {env_prefix}_user 환경변수가 설정되지 않았습니다.")
        # if not password:
        #     print(f"   ⚠️ 경고: {env_prefix}_password 환경변수가 설정되지 않았습니다.")
        
        # print(f"   DB 연결 시도 중...")
        # 프로젝트 소유권/삭제 여부 필터링(선택)
        if user_id is None:
            base_filters = " AND 1=1"
            params = (project_id_int, project_id_int, project_id_int)
        else:
            base_filters = " AND p.user_id = %s AND p.is_deleted = 0"
            # p2/p3도 동일하게 적용되도록 문자열 치환
            params = (project_id_int, user_id, project_id_int, user_id, project_id_int, user_id)

        filtered_query = (
            query
            .replace("WHERE mcq.project_id = %s", f"WHERE mcq.project_id = %s{base_filters} AND IFNULL(mcq.is_used, 1) = 1")
            .replace(
                "WHERE saq.project_id = %s",
                (f"WHERE saq.project_id = %s AND p2.user_id = %s AND p2.is_deleted = 0 AND IFNULL(saq.is_used, 1) = 1")
                if user_id is not None
                else "WHERE saq.project_id = %s AND IFNULL(saq.is_used, 1) = 1"
            )
            .replace(
                "WHERE tfq.project_id = %s",
                (f"WHERE tfq.project_id = %s AND p3.user_id = %s AND p3.is_deleted = 0 AND IFNULL(tfq.is_used, 1) = 1")
                if user_id is not None
                else "WHERE tfq.project_id = %s AND IFNULL(tfq.is_used, 1) = 1"
            )
        )

        results = execute_query_via_app_db(filtered_query, params=params, fetch=True)
        
        if not results:
            print(f"   ⚠️ project_id={project_id_int}에 해당하는 문항 데이터가 없습니다.")
            return []
        
        print(f"   ✅ DB 쿼리 완료 (조회된 행: {len(results)}개)")
        
        # 결과를 딕셔너리 리스트로 변환
        print(f"📦 [데이터 변환] 딕셔너리로 변환 중...")
        data_list = []
        for idx, row in enumerate(results, 1):
            # 번호는 전체 문항 순서로 부여
            data_list.append({
                'nu': idx,
                'question': row.get('question', ''),
                'select1': row.get('select1', '') or '',
                'select2': row.get('select2', '') or '',
                'select3': row.get('select3', '') or '',
                'select4': row.get('select4', '') or '',
                'select5': row.get('select5', '') or '',
                'answer': row.get('answer', ''),
                'answer_explain': row.get('answer_explain', ''),
                # 템플릿에 {passage}가 있으면 프로젝트 지문을 사용
                'passage': passage_text
            })
            if idx % 10 == 0 or idx == len(results):
                print(f"   진행 중... {idx}/{len(results)}", end="\r", flush=True)
        
        print(f"\n   ✅ 변환 완료! 총 {len(data_list)}개의 질문 데이터를 가져왔습니다.")
        return data_list
        
    except ValueError as e:
        print(f"\n❌ [DB 연결 오류] 설정 오류 발생:")
        print(f"   {e}")
        print(f"\n💡 해결 방법:")
        print(f"   1. .env 파일 또는 환경변수에 다음을 설정하세요:")
        print(f"      - DB_HOST=데이터베이스_호스트")
        print(f"      - DB_PORT=데이터베이스_포트 (기본값: 3306)")
        print(f"      - DB_USER=데이터베이스_사용자")
        print(f"      - DB_PASSWORD=데이터베이스_비밀번호")
        print(f"      - DB_DATABASE=데이터베이스_이름")
        print(f"   3. 데이터베이스 이름을 변경하려면 DB_DATABASE 환경변수를 설정하세요 (기본값: midtest)")
        raise
    except Exception as e:
        print(f"\n❌ [DB 연결 오류] 예상치 못한 오류 발생:")
        print(f"   오류 타입: {type(e).__name__}")
        print(f"   오류 메시지: {e}")
        print(f"\n💡 해결 방법:")
        print(f"   1. 데이터베이스 서버가 실행 중인지 확인하세요")
        print(f"   2. 네트워크 연결을 확인하세요")
        print(f"   3. 방화벽 설정을 확인하세요")
        print(f"   4. 환경변수 설정을 확인하세요")
        import traceback
        print(f"\n📋 상세 오류 정보:")
        traceback.print_exc()
        raise

def copy_run_formatting(source_run, target_run):
    """
    source_run의 서식을 target_run에 복사하는 함수
    
    Args:
        source_run: 서식을 복사할 원본 Run 객체
        target_run: 서식을 적용할 대상 Run 객체
    """
    try:
        # 폰트 이름
        if source_run.font.name:
            target_run.font.name = source_run.font.name
        # 폰트 크기
        if source_run.font.size:
            target_run.font.size = source_run.font.size
        # 굵기
        if source_run.font.bold is not None:
            target_run.font.bold = source_run.font.bold
        # 기울임
        if source_run.font.italic is not None:
            target_run.font.italic = source_run.font.italic
        # 밑줄
        if source_run.font.underline is not None:
            target_run.font.underline = source_run.font.underline
        # 색상
        try:
            if source_run.font.color.rgb:
                target_run.font.color.rgb = source_run.font.color.rgb
        except:
            pass
        # 하이라이트 색상
        if source_run.font.highlight_color is not None:
            target_run.font.highlight_color = source_run.font.highlight_color
    except Exception as e:
        # 서식 복사 실패 시 기본 서식으로 진행
        pass

def replace_table_text(table, data, num):
    """
    표의 플레이스홀더를 실제 데이터로 교체하는 함수 (서식 유지)
    
    Args:
        table: docx Table 객체
        data: 채울 데이터 (dict)
    """
    # 플레이스홀더 교체 딕셔너리
    replacements = {
        '{nu}': str(data.get('nu', '')),
        '{num}': str(num),
        '{question}': str(data.get('question', '')),
        '{select1}': str(data.get('select1', '')),
        '{select2}': str(data.get('select2', '')),
        '{select3}': str(data.get('select3', '')),
        '{select4}': str(data.get('select4', '')),
        '{select5}': str(data.get('select5', '')),
        '{answer}': str(data.get('answer', '')),
        '{answer_explain}': str(data.get('answer_explain', '')),
        '{passage}': str(data.get('passage', ''))
    }
    
    # 표 내의 모든 셀을 순회하며 플레이스홀더 교체
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            # 각 단락을 순회
            for paragraph in cell.paragraphs:
                # 단락의 전체 텍스트 확인
                para_text = paragraph.text
                if not para_text:
                    continue
                
                # 플레이스홀더가 있는지 확인
                has_placeholder = False
                for placeholder in replacements.keys():
                    if placeholder in para_text:
                        has_placeholder = True
                        break
                
                if not has_placeholder:
                    continue
                
                # 플레이스홀더를 실제 값으로 교체
                replaced_text = para_text
                for placeholder, value in replacements.items():
                    if placeholder in replaced_text:
                        replaced_text = replaced_text.replace(placeholder, value)
                
                # 텍스트가 변경되었는지 확인
                if replaced_text == para_text:
                    continue
                
                # 기존 run들의 서식 정보 저장 (첫 번째 run의 서식 사용)
                reference_run = None
                if paragraph.runs:
                    reference_run = paragraph.runs[0]
                
                # 기존 run들을 모두 제거
                for run in list(paragraph.runs):
                    run._element.getparent().remove(run._element)
                
                # 교체된 텍스트를 새 run으로 추가 (서식 유지)
                if replaced_text:
                    new_run = paragraph.add_run(replaced_text)
                    if reference_run:
                        copy_run_formatting(reference_run, new_run)

# 사용 예시
if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("🚀 문서 생성 스크립트 시작")
    print("="*60 + "\n")
    
    # 프로젝트 ID 결정
    project_id = os.getenv("PROJECT_ID") or os.getenv("CREATE_PROJECT_ID") or os.getenv("CREATE_INFO_ID")
    print(f"📌 [환경변수 확인] PROJECT_ID/CREATE_PROJECT_ID/CREATE_INFO_ID = {project_id if project_id else '(설정되지 않음)'}")
    if not project_id:
        print("❌ PROJECT_ID 환경변수가 설정되지 않았습니다. (또는 CREATE_PROJECT_ID/CREATE_INFO_ID 숫자값)")
        sys.exit(1)

    project_id_int = get_project_id_from_env_or_arg(project_id)
    category = os.getenv("CATEGORY", "")
    
    # DB에서 데이터 가져오기
    try:
        print(f"\n💾 [DB 데이터 조회] 시작...")
        data_list = get_question_data_from_db(project_id_int)
        
        if not data_list:
            print("\n❌ 가져올 데이터가 없습니다.")
            sys.exit(1)
        
        # 입력 파일과 출력 파일 경로 (환경변수에서 가져오거나 기본값 사용)
        input_file = os.getenv('INPUT_DOCX', 'sample3.docx')
        output_file = os.getenv('OUTPUT_DOCX', f'output-project-{project_id_int}.docx')
        
        print(f"\n📁 [파일 경로]")
        print(f"   입력: {input_file}")
        print(f"   출력: {output_file}")
        
        # 함수 실행 (카테고리 전달)
        fill_table_from_list(input_file, output_file, data_list, category=category)
        
    except ValueError as e:
        print(f"❌ 오류: {e}")
        print("\n사용법:")
        print("  1. 환경변수 설정: export INFO_ID=123")
        print("  2. 또는 명령줄 인자: python dev.py 123")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 기존 샘플 데이터 (사용 안 함)
    _sample_data = [
        {
            'nu': 1,
            'question': '첫 번째 질문입니다',
            'select1': '선택지 1-1',
            'select2': '선택지 1-2',
            'select3': '선택지 1-3',
            'select4': '선택지 1-4',
            'select5': '선택지 1-5'
        },
        {
            'nu': 2,
            'question': '두 번째 질문입니다',
            'select1': '선택지 2-1',
            'select2': '선택지 2-2',
            'select3': '선택지 2-3',
            'select4': '선택지 2-4',
            'select5': '선택지 2-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        },
        {
            'nu': 3,
            'question': '세 번째 질문입니다',
            'select1': '선택지 3-1',
            'select2': '선택지 3-2',
            'select3': '선택지 3-3',
            'select4': '선택지 3-4',
            'select5': '선택지 3-5'
        }
    ]