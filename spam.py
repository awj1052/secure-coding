import time
from collections import defaultdict

# 유저별 메시지 전송 기록 (최근 N초 동안 요청 횟수 저장)
request_counter = defaultdict(list)

# 스팸 방지 설정
MAX_MESSAGES = 5       # 제한 메시지 개수
TIME_WINDOW = 10        # 제한 시간 (초)

def is_spam(user_id):
    current_time = time.time()

    # 최근 TIME_WINDOW 초 동안의 요청만 유지
    request_counter[user_id] = [t for t in request_counter[user_id] if current_time - t < TIME_WINDOW]

    # 제한 횟수 초과 시 차단
    if len(request_counter[user_id]) >= MAX_MESSAGES:
        return True

    # 메시지 기록 추가
    request_counter[user_id].append(current_time)
    return False
