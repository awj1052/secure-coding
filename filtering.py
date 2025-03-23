import re

blocked_patterns = [
    r'<script.*?>.*?</script>',
    r'javascript:',
    r'eval\(',
    r'alert\(',
    r'<.*?>',
    r'[\x00-\x1F\x7F]',
]

def is_message_safe(message):
    if len(message) > 100: return False
    for pattern in blocked_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return False 
    return True