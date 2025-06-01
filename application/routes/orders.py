from itertools import product

from flask import render_template, flash, redirect, url_for, request, Blueprint, current_app
from flask_login import login_required

from application.extensions import mysql
from ..forms import OrderForm

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_order():
    form = OrderForm()

    # Заполняем выбор магазинов
    with mysql.connection.cursor() as cur:
        cur.execute("SELECT id, name FROM shops")
        shops = cur.fetchall()
        form.shop_id.choices = [(shop['id'], shop['name']) for shop in shops]

        # Заполняем выбор товаров
        cur.execute("SELECT id, name FROM products")
        products = cur.fetchall()
        product_choices = [(prod['id'], prod['name']) for prod in products]

        # Устанавливаем choices для всех полей товаров
        for item in form.items:
            item.form.product_id.choices = product_choices

    # Отладочный вывод перед валидацией
    print(f"Form submitted? {request.method == 'POST'}")
    print(f"Form data: {form.data}")
    print(f"Form errors: {form.errors}")

    if form.validate_on_submit():
        print("Form validation passed! Creating order...")

        try:
            with mysql.connection.cursor() as cur:
                # Создаем заказ
                cur.execute("INSERT INTO orders (shop_id) VALUES (%s)",
                            (form.shop_id.data,))
                order_id = cur.lastrowid
                print(f"Created order ID: {order_id}")

                # Добавляем товары
                for item in form.items:
                    if item.form.product_id.data and item.form.quantity.data:
                        cur.execute(
                            """INSERT INTO order_items 
                               (order_id, product_id, quantity) 
                               VALUES (%s, %s, %s)""",
                            (order_id, item.form.product_id.data, item.form.quantity.data)
                        )
                        print(f"Added item: {item.form.product_id.data} x {item.form.quantity.data}")

                mysql.connection.commit()
                flash('Заказ успешно создан!', 'success')
                return redirect(url_for('orders.list_orders'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Ошибка создания заказа: {str(e)}', 'danger')
            print(f"Database error: {str(e)}")

    # Если форма не прошла валидацию
    print(f"Form validation failed. Errors: {form.errors}")
    return render_template('orders/add.html', form=form)

@orders_bp.route('/list')
@login_required
def list_orders():
    try:
        with mysql.connection.cursor() as cur:
            cur.execute("""
                SELECT 
                    o.id, 
                    DATE_FORMAT(o.created_at, '%Y-%m-%d %H:%i') as order_date,
                    s.name AS shop_name,
                    COALESCE((
                        SELECT SUM(p.price * oi.quantity)
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = o.id
                    ), 0) AS total_sum
                FROM 
                    orders o
                JOIN 
                    shops s ON o.shop_id = s.id
                ORDER BY 
                    o.created_at DESC
            """)
            orders = cur.fetchall()

            # Отладочный вывод
            print("Orders data:", orders)

            return render_template('orders/list.html', orders=orders)

    except Exception as e:
        current_app.logger.error(f"Error in list_orders: {str(e)}")
        flash('Ошибка при загрузке списка заказов', 'danger')
        return redirect(url_for('main.dashboard'))

@orders_bp.route('/details/<int:order_id>')
@login_required
def order_details(order_id):
    try:
        with mysql.connection.cursor() as cur:
            # Получаем информацию о заказе и магазине
            query = """
                SELECT 
                    o.id,
                    DATE_FORMAT(o.created_at, %s) as order_date,
                    s.name AS shop_name,
                    s.address AS shop_address,
                    COALESCE((
                        SELECT SUM(p.price * oi.quantity)
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = o.id
                    ), 0) AS total_sum
                FROM 
                    orders o
                JOIN 
                    shops s ON o.shop_id = s.id
                WHERE 
                    o.id = %s
            """
            date_format = '%Y-%m-%d %H:%i'
            print(f"Executing query: {query % (date_format, order_id)}")  # Отладочный вывод запроса
            cur.execute(query, (date_format, order_id))
            order = cur.fetchone()

            if not order:
                flash('Заказ не найден', 'danger')
                return redirect(url_for('orders.list_orders'))

            # Получаем товары в заказе
            cur.execute("""
                SELECT 
                    p.name AS product_name,
                    p.manufacturer,
                    p.price,
                    oi.quantity,
                    (p.price * oi.quantity) AS item_total
                FROM 
                    order_items oi
                JOIN 
                    products p ON oi.product_id = p.id
                WHERE 
                    oi.order_id = %s
            """, (order_id,))
            items = cur.fetchall()

            # Отладочный вывод
            print(f"Order details: {order}")
            print(f"Order items: {items}")

            return render_template('orders/details.html', order=order, items=items)

    except Exception as e:
        current_app.logger.error(f"Error in order_details: {str(e)}")
        flash('Ошибка при загрузке деталей заказа', 'danger')
        return redirect(url_for('orders.list_orders'))