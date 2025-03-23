from flask import Blueprint, session, request, render_template, redirect, url_for, current_app
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import uuid
import html
import hmac
import hashlib

from db import get_db
import spam
from socketio_instance import socketio

chat = Blueprint('chat', __name__)

@chat.route('/chat', methods=['POST'])
def chat_page():
    target = request.form.get('target')
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    # 로그인한 사용자 정보
    user_id = session['user_id']
    cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        return redirect(url_for('auth.login'))

    # 대상 사용자 정보
    cursor.execute("SELECT * FROM user WHERE username = ?", (target,))
    target_user = cursor.fetchone()
    if not target_user:
        return "존재하지 않는 사용자입니다.", 404

    # 채팅방 ID: 양방향 동일하게 보장
    room_id = create_hmac("|".join(sorted([user['username'], target_user['username']])), current_app.config['SECRET_KEY'])

    return render_template('chat.html', user=user, chat_partner=target_user, room_id=room_id)

# 소켓 통신 관련 이벤트 처리

@socketio.on('connect')
def handle_connect():
    if 'user_id' not in session:
        return False  # 인증 안되면 연결 거부

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Disconnected: {session.get('user_id')}")

@socketio.on('join_room')
def handle_join_room_event(data):
    room = data.get('room')
    join_room(room)
    print(f"Joined room: {room}")

@socketio.on('send_message_private')
def handle_send_message_private(data):
    if 'user_id' not in session:
        return

    user_id = session['user_id']
    room = data.get('room')
    message = data.get('message', '').strip()

    if not room or not message:
        return

    if spam.is_spam(user_id):
        emit("private_message", {
            'message_id': str(uuid.uuid4()),
            'username': '[SYSTEM]',
            'message': '메세지를 천천히 보내세요.'
        }, to=room)
        return

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        return

    if len(message) > 100:
        emit("private_message", {
            'message_id': str(uuid.uuid4()),
            'username': '[SYSTEM]',
            'message': '한 번에 많은 메세지를 보낼 수 없습니다.'
        }, to=room, broadcast=False)
        return

    safe_message = html.escape(message)
    emit("private_message", {
        'message_id': str(uuid.uuid4()),
        'username': user['username'],
        'message': safe_message
    }, to=room)

def create_hmac(data, secret_key):
    # 비밀 키와 데이터를 합쳐서 HMAC 생성
    return hmac.new(secret_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
