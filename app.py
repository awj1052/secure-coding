import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, Blueprint, abort
from flask_socketio import SocketIO, send
import os
import bcrypt
import html

from db import *
from admin import *
import auth, product, report, chat
import filtering, spam

app = Flask(__name__)
app.config['SECRET_KEY'] = ''
if os.path.exists('secret.txt'):
    with open('secret.txt', "r") as f:
        app.config['SECRET_KEY'] = f.read().strip()

DATABASE = 'market.db'
socketio = SocketIO(app)

app.register_blueprint(auth.auth)
app.register_blueprint(product.product)
app.register_blueprint(report.report)
app.register_blueprint(chat.chat)

@app.teardown_appcontext
def close_connection(exception):
    close_db(exception)

@app.before_request
def check_spam():
    ip = get_client_ip()
    if spam.is_spam(ip):
        abort(429, description="Too Many Requests - You are being rate-limited.")

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]  # 첫 번째 IP가 실제 클라이언트 IP
    return request.headers.get('X-Real-IP') or request.remote_addr

# 기본 라우트
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# 대시보드: 사용자 정보와 전체 상품 리스트 표시
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    cursor = db.cursor()
    # 현재 사용자 조회
    cursor.execute("SELECT * FROM user WHERE id = ?", (session['user_id'],))
    current_user = cursor.fetchone()
    if current_user is None:
        return redirect(url_for('auth.login'))
    # 모든 상품 조회
    cursor.execute("SELECT * FROM product")
    all_products = cursor.fetchall()
    return render_template('dashboard.html', products=all_products, user=current_user)

# 프로필 페이지: bio 업데이트 가능
@app.route('/profile', methods=['GET', 'POST'])
@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username=None):
    # 로그인 체크
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()    

    # 프로필을 볼 사용자를 결정
    user = None
    if username is None:
        cursor.execute("SELECT * FROM user WHERE id = ?", (session['user_id'],)) # 로그인한 사용자의 프로필을 기본값으로 설정
        user = cursor.fetchone()
    else:
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        user = cursor.fetchone()
    
    if user is None:
        flash('사용자를 찾을 수 없습니다.')
        return redirect(url_for('profile'))  # 잘못된 사용자 ID로 접근할 경우 로그인된 사용자 프로필로 돌아가기
    
    # 프로필 수정 처리
    if request.method == 'POST':
        if username is not None:
            flash("다른 사용자의 소개글은 수정할 수 없습니다.")
            return redirect(url_for('profile', username=username)) 
        bio = request.form.get('bio', '')
        cursor.execute("UPDATE user SET bio = ? WHERE id = ?", (bio, session['user_id']))
        db.commit()
        flash('프로필이 업데이트되었습니다.')
        return redirect(url_for('profile'))  # 로그인한 사용자의 프로필로 리다이렉트

    return render_template('profile.html', user=user)

@app.route('/changePassword', methods=['GET', 'POST'])
def change_pw():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    # 비밀번호 변경 처리
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # 현재 비밀번호 확인
        if not bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
            flash('현재 비밀번호가 올바르지 않습니다.')
            return redirect(url_for('change_pw'))
        if not validate.password(new_password):
            flash('올바르지 않은 비밀번호입니다.')
            return redirect(url_for('change_pw'))
        # 새로운 비밀번호 확인
        if new_password != confirm_password:
            flash('새로운 비밀번호가 일치하지 않습니다.')
            return redirect(url_for('change_pw'))

        # 새로운 비밀번호 해싱 후 저장
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("UPDATE user SET password = ? WHERE id = ?", (hashed_password, user_id))
        db.commit()

        session.pop('user_id', None)
        flash('비밀번호가 변경되어 로그아웃 됩니다.')
        return redirect(url_for('index'))

    return render_template('change_pw.html', user=user)

# 실시간 채팅: 클라이언트가 메시지를 보내면 전체 브로드캐스트
@socketio.on('send_message')
def handle_send_message_event(data):
    if 'user_id' not in session:
        return
    
    user_id = session['user_id']
    if spam.is_spam(user_id): 
        message_data = {
            'message_id': str(uuid.uuid4()),
            'username': '[SYSTEM]',
            'message': '메세지를 천천히 보내세요.'
        }
        send(message_data, broadcast=False)
        return

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        return 

    message = data.get('message', '').strip()
    if not message or len(message) > 100:
        message_data = {
            'message_id': str(uuid.uuid4()),
            'username': '[SYSTEM]',
            'message': '한 번에 많은 메세지를 보낼 수 없습니다.'
        }
        send(message_data, broadcast=False)
        return  # 빈 메시지 또는 너무 긴 메시지는 차단

    safe_message = html.escape(message)  # HTML 태그 및 XSS 방어
    message_data = {
        'message_id': str(uuid.uuid4()),
        'username': user['username'],
        'message': safe_message
    }
    send(message_data, broadcast=True)

if __name__ == '__main__':
    init_db(app)  # 앱 컨텍스트 내에서 테이블 생성
    socketio.run(app, debug=True)
