from flask import Blueprint, session, request, render_template, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import uuid
import html
from db import get_db
import spam

chat = Blueprint('chat', __name__)
socketio = SocketIO()

@chat.route('/chat', methods=['POST'])
def chat_page():
    target = request.form['target']
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    cursor = db.cursor()

    user_id = session['user_id']
    cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        return redirect(url_for('auth.login'))

    cursor.execute("SELECT * FROM user WHERE username = ?", (target,))
    target_user = cursor.fetchone()
    if not target_user:
        return "존재하지 않는 사용자입니다.", 404

    # 1대1 채팅방 ID 생성 (두 유저 ID를 합쳐서 방 ID 생성)
    room_id = "|".join(sorted([user['username'], target]))

    return render_template('chat.html', user=user, chat_partner=target_user, room_id=room_id)


@socketio.on('join_room')
def handle_join_room_event(data):
    room = data.get('room')
    join_room(room)


@socketio.on('send_message_private')
def handle_send_message_private(data):
    if 'user_id' not in session:
        return

    user_id = session['user_id']
    room = data.get('room')

    if spam.is_spam(user_id): 
        message_data = {
            'message_id': str(uuid.uuid4()),
            'username': '[SYSTEM]',
            'message': '메세지를 천천히 보내세요.'
        }
        send(message_data, to=room)  # 해당 방에만 메시지 전송
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
        send(message_data, to=room)  # 해당 방에만 메시지 전송
        return

    safe_message = html.escape(message)  # HTML 태그 및 XSS 방어
    message_data = {
        'message_id': str(uuid.uuid4()),
        'username': user['username'],
        'message': safe_message
    }
    send(message_data, to=room)  # 해당 방에만 메시지 전송