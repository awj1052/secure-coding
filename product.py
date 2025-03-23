import uuid
from flask import render_template, request, session, flash, redirect, url_for, Blueprint
from db import get_db
from admin import ADMIN

product = Blueprint('product', __name__)

# 상품 등록
@product.route('/product/new', methods=['GET', 'POST'])
def new():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        if price.isdigit() and int(price) > 0:
            # 가격이 양의 정수일 경우 처리
            price = int(price)
            # 상품 등록 코드
        else:
            flash('가격은 양의 정수여야 합니다.')
            return render_template('new_product.html')
        db = get_db()
        cursor = db.cursor()
        product_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO product (id, title, description, price, seller_id) VALUES (?, ?, ?, ?, ?)",
            (product_id, title, description, price, session['user_id'])
        )
        db.commit()
        flash('상품이 등록되었습니다.')
        return redirect(url_for('dashboard'))
    return render_template('new_product.html')

# 상품 상세보기
@product.route('/product/view/<product_id>')
def view(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM product WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    if not product:
        flash('상품을 찾을 수 없습니다.')
        return redirect(url_for('dashboard'))
    # 판매자 정보 조회
    cursor.execute("SELECT * FROM user WHERE id = ?", (product['seller_id'],))
    seller = cursor.fetchone()
    return render_template('view_product.html', product=product, seller=seller, ADMIN=ADMIN)

# 상품 수정하기
@product.route('/product/modify/<product_id>', methods=['GET', 'POST'])
def modify(product_id):
    method = request.form['_method']

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM product WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    if not product or \
        user_id != product['seller_id'] or user_id != ADMIN or \
        not method in ['PUT', 'DELETE']:
        flash("권한이 없습니다.")
        return redirect(request.referrer) 

    if method == 'PUT':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        if price.isdigit() and int(price) > 0:
            # 가격이 양의 정수일 경우 처리
            price = int(price)
            # 상품 등록 코드
        else:
            flash('가격은 양의 정수여야 합니다.')
            return redirect(request.referrer)

        cursor.execute(
            "UPDATE product SET title = ?, description = ?, price = ? WHERE id = ?",
            (title, description, price, product_id)
        )
        db.commit()
        flash('상품이 수정되었습니다.')
        return redirect(url_for('dashboard'))
    
    # DELETE
    cursor.execute("DELETE FROM product WHERE id = ?", (product_id,))
    db.commit()
    flash('상품이 삭제되었습니다.')
    return redirect(url_for('dashboard'))