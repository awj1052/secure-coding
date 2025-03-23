from functools import wraps
from flask import abort, session
import os

ADMIN = None # user_id
if os.path.exists('admin.txt'):
    with open('admin.txt', "r") as f:
        ADMIN = f.read().strip()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session['user_id'] == ADMIN:
            abort(403)  # 권한 없음
        return f(*args, **kwargs)
    return decorated_function
