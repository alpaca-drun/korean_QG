"""
AWS SES를 이용한 이메일 전송 클라이언트
"""
import boto3
from typing import Optional
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logger import logger


class EmailClient:
    """AWS SES 이메일 클라이언트"""
    
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
        
        # SES 클라이언트 초기화
        self.ses = boto3.client(
            'ses',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
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
            
            # 이메일 전송
            response = self.ses.send_email(
                Source=self.sender_email,
                Destination=destination,
                Message=message
            )
            
            logger.info("이메일 전송 성공: %s (MessageId: %s)", to_address, response['MessageId'])
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error("이메일 전송 실패: %s - %s", error_code, error_message)
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
        total_questions: int
    ) -> bool:
        """
        문항 생성 성공 이메일 전송
        
        Args:
            to_address: 수신자 이메일
            project_name: 프로젝트 이름
            success_count: 성공한 배치 수
            total_count: 전체 배치 수
            total_questions: 생성된 전체 문항 수
            
        Returns:
            bool: 전송 성공 여부
        """
        subject = f"[문항 생성 완료] {project_name}"
        
        # 텍스트 본문
        body = f"""
안녕하세요,

"{project_name}" 프로젝트의 문항 생성이 완료되었습니다.

📊 생성 결과:
- 성공한 배치: {success_count}/{total_count}
- 생성된 총 문항 수: {total_questions}개

대시보드에서 생성된 문항을 확인하실 수 있습니다.

감사합니다.
        """.strip()
        
        # HTML 본문 (선택사항)
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
        .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; border-radius: 5px; }}
        .stats {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ 문항 생성 완료</h1>
        </div>
        <div class="content">
            <p>안녕하세요,</p>
            <p><strong>"{project_name}"</strong> 프로젝트의 문항 생성이 완료되었습니다.</p>
            
            <div class="stats">
                <h3>📊 생성 결과</h3>
                <ul>
                    <li>성공한 배치: <strong>{success_count}/{total_count}</strong></li>
                    <li>생성된 총 문항 수: <strong>{total_questions}개</strong></li>
                </ul>
            </div>
            
            <p>대시보드에서 생성된 문항을 확인하실 수 있습니다.</p>
            <p>감사합니다.</p>
        </div>
        <div class="footer">
            <p>이 메일은 자동으로 발송되었습니다.</p>
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
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
        .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; border-radius: 5px; }}
        .error {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #f44336; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>❌ 문항 생성 실패</h1>
        </div>
        <div class="content">
            <p>안녕하세요,</p>
            <p><strong>"{project_name}"</strong> 프로젝트의 문항 생성 중 오류가 발생했습니다.</p>
            
            <div class="error">
                <h3>❌ 오류 내용</h3>
                <p>{error_message}</p>
            </div>
            
            <p>관리자에게 문의하거나 다시 시도해주세요.</p>
            <p>감사합니다.</p>
        </div>
        <div class="footer">
            <p>이 메일은 자동으로 발송되었습니다.</p>
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