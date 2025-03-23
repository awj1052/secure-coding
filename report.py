import uuid
from flask import render_template, request, session, flash, redirect, url_for, Blueprint
from db import get_db
import admin

report = Blueprint('report', __name__)

# 신고하기
@report.route('/report', methods=['GET', 'POST'])
def reporting():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        target_id = request.form['target_id']
        reason = request.form['reason']
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM user WHERE username = ?", (target_id,))
        target = cursor.fetchone()
        if not target:
            flash('유저를 찾을 수 없습니다.')
            return redirect(request.referrer)

        report_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO report (id, reporter_id, target_id, reason) VALUES (?, ?, ?, ?)",
            (report_id, session['user_id'], target_id, reason)
        )
        db.commit()
        flash('신고가 접수되었습니다.')
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@report.route('/report/list')
@admin.admin_required
def control():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM report")
    reports = cursor.fetchall()
    return render_template('report_list.html', reports=reports)

@report.route('/report/remove', methods=['POST'])
@admin.admin_required
def remove():
    target_id = request.form['target_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM user WHERE username = ?", (target_id,))
    db.commit()
    if cursor.rowcount > 0:
        flash(f'유저를 삭제했다!')
    else:
        flash(f'유저를 찾을 수 없다!')
    return redirect(request.referrer)
