import bcrypt
import uuid
from flask import render_template, request, session, flash, redirect, url_for, Blueprint
from db import get_db

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        if not check_username(username):
            flash('올바르지 않은 사용자명입니다.')
            return redirect(url_for('auth.register'))
        password = request.form['password']
        if not check_password(password):
            flash('올바르지 않은 비밀번호입니다.')
            return redirect(url_for('auth.register'))
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.')
            return redirect(url_for('auth.register'))
        
        # 중복 사용자 체크
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        if cursor.fetchone() is not None:
            flash('이미 존재하는 사용자명입니다.')
            return redirect(url_for('auth.register'))

        # 비밀번호를 bcrypt로 해시하기
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # 사용자 ID 생성 (UUID 사용)
        user_id = str(uuid.uuid4())

        # 사용자 정보 DB에 저장 (해시된 비밀번호 사용)
        cursor.execute("INSERT INTO user (id, username, password) VALUES (?, ?, ?)",
                       (user_id, username, hashed_password))
        db.commit()

        flash('회원가입이 완료되었습니다. 로그인 해주세요.')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

# 로그인
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user:
            # DB에 저장된 해시된 비밀번호 가져오기
            stored_hash = user['password']
            
            # bcrypt로 입력한 비밀번호와 저장된 해시된 비밀번호 비교
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # 비밀번호가 일치하면 세션 설정
                session['user_id'] = user['id']
                flash('로그인 성공!')
                return redirect(url_for('dashboard'))
            else:
                flash('아이디 또는 비밀번호가 올바르지 않습니다.')
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')

        return redirect(url_for('auth.login'))

    return render_template('login.html')

# 로그아웃
@auth.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('index'))

import re

def check_username(username):
    pattern = r'^[a-zA-Z0-9-_]{3,20}$'
    return re.match(pattern, username)

def check_password(password):
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,20}$'
    return re.match(pattern, password)