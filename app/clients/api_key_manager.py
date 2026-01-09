import random
from typing import List, Optional, Dict
from threading import Lock
from datetime import datetime, timedelta


class APIKeyManager:
    """API 키 풀 관리자 - 로테이션 및 Rate Limit 처리"""
    
    def __init__(self, api_keys: List[str], strategy: str = "round_robin"):
        """
        Args:
            api_keys: API 키 리스트
            strategy: 로테이션 전략 (round_robin, random, failover)
        """
        if not api_keys:
            raise ValueError("API 키 리스트가 비어있습니다.")
        
        self.api_keys = api_keys
        self.strategy = strategy
        self.current_index = 0
        self.lock = Lock()
        
        # Rate limit 추적 (키별로 마지막 사용 시간과 에러 카운트)
        self.key_status: Dict[str, Dict] = {
            key: {
                "last_used": None,
                "error_count": 0,
                "last_error": None,
                "is_blocked": False,
                "blocked_until": None
            }
            for key in api_keys
        }
    
    def get_next_key(self) -> Optional[str]:
        """다음 사용할 API 키 반환"""
        if not self.api_keys:
            return None
        
        available_keys = self._get_available_keys()
        if not available_keys:
            # 모든 키가 차단된 경우, 차단 해제 시도
            self._reset_blocked_keys()
            available_keys = self._get_available_keys()
        
        if not available_keys:
            return None
        
        if self.strategy == "round_robin":
            return self._get_round_robin_key(available_keys)
        elif self.strategy == "random":
            return random.choice(available_keys)
        elif self.strategy == "failover":
            return available_keys[0]
        else:
            return available_keys[0]
    
    def get_keys_for_batch(self, batch_size: int) -> List[str]:
        """
        배치 처리를 위한 여러 API 키 반환
        
        Args:
            batch_size: 필요한 키 개수
            
        Returns:
            API 키 리스트
        """
        available_keys = self._get_available_keys()
        if not available_keys:
            self._reset_blocked_keys()
            available_keys = self._get_available_keys()
        
        if not available_keys:
            return []
        
        # 배치 크기만큼 키를 순환하여 반환
        keys = []
        for i in range(batch_size):
            key = available_keys[i % len(available_keys)]
            keys.append(key)
        
        return keys
    
    def _get_available_keys(self) -> List[str]:
        """사용 가능한 API 키 리스트 반환 (차단되지 않은 키)"""
        now = datetime.now()
        available = []
        
        for key in self.api_keys:
            status = self.key_status[key]
            if not status["is_blocked"]:
                available.append(key)
            elif status["blocked_until"] and now > status["blocked_until"]:
                # 차단 시간이 지났으면 해제
                status["is_blocked"] = False
                status["blocked_until"] = None
                status["error_count"] = 0
                available.append(key)
        
        return available
    
    def _get_round_robin_key(self, available_keys: List[str]) -> str:
        """라운드로빈 방식으로 키 선택"""
        with self.lock:
            if self.current_index >= len(available_keys):
                self.current_index = 0
            
            key = available_keys[self.current_index]
            self.current_index += 1
            return key
    
    def mark_success(self, api_key: str):
        """API 키 사용 성공 표시"""
        if api_key in self.key_status:
            self.key_status[api_key]["last_used"] = datetime.now()
            self.key_status[api_key]["error_count"] = 0
    
    def mark_error(self, api_key: str, error_type: str = "rate_limit"):
        """API 키 사용 실패 표시"""
        if api_key not in self.key_status:
            return
        
        status = self.key_status[api_key]
        status["error_count"] += 1
        status["last_error"] = datetime.now()
        
        # 에러 타입에 따른 차단 시간 설정
        if error_type == "rate_limit":
            # Rate limit: 5분 차단
            status["is_blocked"] = True
            status["blocked_until"] = datetime.now() + timedelta(minutes=5)
        elif error_type == "timeout":
            # 타임아웃: 2분 차단 (일시적인 문제일 수 있음)
            status["is_blocked"] = True
            status["blocked_until"] = datetime.now() + timedelta(minutes=2)
        elif error_type == "invalid_key":
            # 잘못된 키: 10분 차단
            status["is_blocked"] = True
            status["blocked_until"] = datetime.now() + timedelta(minutes=10)
        elif status["error_count"] >= 3:
            # 연속 3회 에러 시 1분 차단
            status["is_blocked"] = True
            status["blocked_until"] = datetime.now() + timedelta(minutes=1)
    
    def _reset_blocked_keys(self):
        """차단된 키 초기화 (긴급 상황용)"""
        now = datetime.now()
        for key, status in self.key_status.items():
            if status["blocked_until"] and now > status["blocked_until"]:
                status["is_blocked"] = False
                status["blocked_until"] = None
                status["error_count"] = 0
    
    def get_status(self) -> Dict[str, Dict]:
        """모든 API 키의 상태 반환"""
        return self.key_status.copy()

