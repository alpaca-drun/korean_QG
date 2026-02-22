"""
AWS SES를 이용한 이메일 전송 클라이언트
"""
import time
import boto3
from typing import Optional
from botocore.exceptions import ClientError
from botocore.config import Config
from app.core.config import settings
from app.core.logger import logger


class EmailClient:
    """AWS SES 이메일 클라이언트"""
    
    # 재시도 설정
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 초
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: Optional[str] = None,
        sender_email: Optional[str] = None
    ):
        """
        EmailClient 초기화
        
        Args:
            aws_access_key_id: AWS Access Key (None이면 설정에서 가져옴)
            aws_secret_access_key: AWS Secret Key (None이면 설정에서 가져옴)
            aws_region: AWS Region (None이면 설정에서 가져옴)
            sender_email: 발신자 이메일 (None이면 설정에서 가져옴)
        """
        self.aws_access_key_id = aws_access_key_id or settings.aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key or settings.aws_secret_access_key
        self.aws_region = aws_region or settings.aws_ses_region
        self.sender_email = sender_email or settings.aws_ses_sender_email
        
        # boto3 설정 (타임아웃 및 재시도)
        boto_config = Config(
            connect_timeout=10,  # 연결 타임아웃 10초
            read_timeout=30,     # 읽기 타임아웃 30초
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
        
        # SES 클라이언트 초기화
        self.ses = boto3.client(
            'ses',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
            config=boto_config
        )
    
    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        bcc_addresses: Optional[list] = None
    ) -> bool:
        """
        이메일 전송
        
        Args:
            to_address: 수신자 이메일
            subject: 제목
            body: 본문 (텍스트)
            html_body: HTML 본문 (선택사항)
            bcc_addresses: BCC 수신자 리스트 (선택사항, None이면 설정에서 가져옴)
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            # 메시지 구성
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {}
            }
            
            # 텍스트 본문 추가
            if body:
                message['Body']['Text'] = {'Data': body, 'Charset': 'UTF-8'}
            
            # HTML 본문 추가
            if html_body:
                message['Body']['Html'] = {'Data': html_body, 'Charset': 'UTF-8'}
            
            # Destination 구성
            destination = {'ToAddresses': [to_address]}
            
            # BCC 추가 (파라미터로 받거나 설정에서 가져옴)
            if bcc_addresses is None:
                bcc_addresses = settings.aws_ses_bcc_email_list
            
            if bcc_addresses:
                destination['BccAddresses'] = bcc_addresses
                logger.info("BCC 수신자: %s", ", ".join(bcc_addresses))
            
            # 이메일 전송 (재시도 로직 포함)
            last_error = None
            for attempt in range(self.MAX_RETRIES):
                try:
                    logger.debug("이메일 전송 시도 %d/%d: %s", attempt + 1, self.MAX_RETRIES, to_address)
                    
                    response = self.ses.send_email(
                        Source=f"디지털사업팀 <{self.sender_email}>",
                        Destination=destination,
                        Message=message
                    )
                    
                    logger.info("이메일 전송 성공: %s (MessageId: %s)", to_address, response['MessageId'])
                    return True
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    last_error = e
                    
                    # 재시도 가능한 에러인지 확인
                    if error_code in ['Throttling', 'ServiceUnavailable', 'RequestThrottled']:
                        logger.warning("이메일 전송 일시적 실패 (시도 %d/%d): %s - %s", 
                                     attempt + 1, self.MAX_RETRIES, error_code, error_message)
                        if attempt < self.MAX_RETRIES - 1:
                            time.sleep(self.RETRY_DELAY * (attempt + 1))
                            continue
                    else:
                        # 재시도 불가능한 에러 (잘못된 이메일 주소 등)
                        logger.error("이메일 전송 실패 (재시도 불가): %s - %s", error_code, error_message)
                        return False
            
            # 최대 재시도 후에도 실패
            if last_error:
                logger.error("이메일 전송 최종 실패: %s", last_error)
            return False
            
        except Exception as e:
            logger.exception("이메일 전송 중 예외 발생: %s", e)
            return False
    
    def send_success_email(
        self,
        to_address: str,
        project_name: str,
        success_count: int,
        total_count: int,
        total_questions: int,
        result_url: Optional[str] = None
    ) -> bool:
        """
        문항 생성 성공 이메일 전송
        """
        subject = f"[문항 생성 완료] {project_name}"
        
        # URL 관련 문구 추가
        url_text = f"\n결과 확인: {result_url}" if result_url else ""
        
        # 텍스트 본문 (Plain Text)
        body = f"""
안녕하세요,

요청하신 "{project_name}" 프로젝트의 문항 생성이 완료되었습니다.

- 생성된 총 문항 수: {total_questions}개
{url_text}

감사합니다.
        """.strip()
        
        # HTML 버튼 (CTA) - 인라인 스타일 적용
        cta_section = f"""
            <div style="margin: 40px 0; text-align: center;">
                <a href="{result_url}" style="background-color: #2563EB; color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 18px; display: inline-block;">
                    생성된 문항 확인하기
                </a>
            </div>
        """ if result_url else ""
        
        # HTML 본문
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; color: #333333; background-color: #f4f4f7;">
    <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border: 1px solid #e1e1e7; border-radius: 8px; overflow: hidden;">
        <!-- 상단 강조 라인 -->
        <div style="height: 4px; background-color: #2563EB;"></div>
        
        <div style="padding: 40px 30px;">
            <h2 style="margin-top: 0; color: #111827; font-size: 22px;">문항 생성이 완료되었습니다.</h2>
            
            <p style="font-size: 16px; color: #4b5563;">
                안녕하세요, <br>
                요청하신 <strong>{project_name}</strong> 프로젝트의 문항 생성이 성공적으로 완료되었습니다.
            </p>
            
            <div style="margin: 30px 0; padding: 20px; background-color: #f9fafb; border-radius: 6px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="color: #6b7280; font-size: 14px;">프로젝트명</td>
                        <td style="color: #111827; font-size: 14px; font-weight: bold; text-align: right;">{project_name}</td>
                    </tr>
                    <tr>
                        <td style="padding-top: 10px; color: #6b7280; font-size: 14px;">생성 문항 수</td>
                        <td style="padding-top: 10px; color: #2563EB; font-size: 14px; font-weight: bold; text-align: right;">{total_questions}개</td>
                    </tr>
                </table>
            </div>

            <p style="font-size: 15px; color: #4b5563;">아래 버튼을 클릭하여 생성된 문항을 바로 확인하실 수 있습니다.</p>
            
            {cta_section}
            
        </div>
        
        <div style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e1e1e7;">
            <p style="margin: 0; font-size: 12px; color: #9ca3af;">본 메일은 발신 전용입니다.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return self.send_email(to_address, subject, body, html_body)
        
    def send_failure_email(
        self,
        to_address: str,
        project_name: str,
        error_message: str
    ) -> bool:
        """
        문항 생성 실패 이메일 전송
        
        Args:
            to_address: 수신자 이메일
            project_name: 프로젝트 이름
            error_message: 오류 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        subject = f"[문항 생성 실패] {project_name}"
        
        body = f"""
안녕하세요,

"{project_name}" 프로젝트의 문항 생성 중 오류가 발생했습니다.

❌ 오류 내용:
{error_message}

관리자에게 문의하거나 다시 시도해주세요.

감사합니다.
        """.strip()
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; color: #333333; background-color: #f4f4f7;">
    <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border: 1px solid #e1e1e7; border-radius: 8px; overflow: hidden;">
        <!-- 상단 강조 라인 (실패: 빨간색) -->
        <div style="height: 4px; background-color: #EF4444;"></div>
        
        <div style="padding: 40px 30px;">
            <h2 style="margin-top: 0; color: #111827; font-size: 22px;">문항 생성에 실패했습니다.</h2>
            
            <p style="font-size: 16px; color: #4b5563;">
                안녕하세요, <br>
                요청하신 <strong>{project_name}</strong> 프로젝트의 문항 생성 중 오류가 발생했습니다.
            </p>
            
            <div style="margin: 30px 0; padding: 20px; background-color: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px;">
                <h3 style="margin-top: 0; font-size: 16px; color: #991B1B; margin-bottom: 10px;">❌ 오류 내용</h3>
                <p style="margin: 0; color: #B91C1C; font-size: 14px; word-break: break-all;">
                    {error_message}
                </p>
            </div>

            <p style="font-size: 15px; color: #4b5563;">
                잠시 후 다시 시도하시거나, 문제가 지속될 경우 관리자에게 문의해주세요.
            </p>
            
        </div>
        
        <div style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e1e1e7;">
            <p style="margin: 0; font-size: 12px; color: #9ca3af;">본 메일은 발신 전용입니다.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
        
        return self.send_email(to_address, subject, body, html_body)


# 싱글톤 인스턴스
_email_client: Optional[EmailClient] = None


def get_email_client() -> EmailClient:
    """
    EmailClient 싱글톤 인스턴스 반환
    
    Returns:
        EmailClient: 이메일 클라이언트 인스턴스
    """
    global _email_client
    if _email_client is None:
        _email_client = EmailClient()
    return _email_client