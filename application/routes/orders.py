from itertools import product

from flask import render_template, flash, redirect, url_for, request, Blueprint, current_app
from flask_login import login_required, current_user

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

    if current_user.role not in ['admin', 'moderator', 'operator']:
        flash('У вас нет прав для просмотра деталей заказов', 'danger')
        return redirect(url_for('main.dashboard'))

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

@orders_bp.route('/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):

    if current_user.role not in ['admin', 'moderator', 'operator']:
        flash('У вас нет прав для редактирования заказов', 'danger')
        return redirect(url_for('main.dashboard'))

    form = OrderForm()

    try:
        with mysql.connection.cursor() as cur:
            # Получаем информацию о заказе
            cur.execute("""
                SELECT 
                    o.id,
                    o.shop_id
                FROM 
                    orders o
                WHERE 
                    o.id = %s
            """, (order_id,))
            order = cur.fetchone()

            if not order:
                flash('Заказ не найден', 'danger')
                return redirect(url_for('orders.list_orders'))

            # Заполняем выбор магазинов
            cur.execute("SELECT id, name FROM shops")
            shops = cur.fetchall()
            shop_choices = [(shop['id'], shop['name']) for shop in shops]
            form.shop_id.choices = shop_choices

            # Заполняем выбор товаров
            cur.execute("SELECT id, name FROM products")
            products = cur.fetchall()
            product_choices = [(prod['id'], prod['name']) for prod in products]
            for item in form.items:
                item.form.product_id.choices = product_choices

            # Получаем текущие товары в заказе
            cur.execute("""
                SELECT 
                    oi.product_id,
                    oi.quantity
                FROM 
                    order_items oi
                WHERE 
                    oi.order_id = %s
            """, (order_id,))
            items = cur.fetchall()

            # Обработка POST-запроса
            if request.method == 'POST':
                # Устанавливаем choices перед валидацией
                form.shop_id.choices = shop_choices
                for item in form.items:
                    item.form.product_id.choices = product_choices

                print(f"POST Form data: {form.data}")
                print(f"POST Form errors: {form.errors}")
                print(f"Shop choices: {shop_choices}")
                print(f"Product choices: {product_choices}")

                if form.validate_on_submit():
                    try:
                        # Обновляем магазин заказа
                        cur.execute("UPDATE orders SET shop_id = %s WHERE id = %s",
                                    (form.shop_id.data, order_id))

                        # Удаляем все текущие товары из заказа
                        cur.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))

                        # Добавляем товары из формы
                        for item in form.items:
                            if item.form.product_id.data and item.form.quantity.data:
                                cur.execute(
                                    """INSERT INTO order_items 
                                       (order_id, product_id, quantity) 
                                       VALUES (%s, %s, %s)""",
                                    (order_id, item.form.product_id.data, item.form.quantity.data)
                                )
                                print(f"Updated item: {item.form.product_id.data} x {item.form.quantity.data}")

                        mysql.connection.commit()
                        flash('Заказ успешно обновлён!', 'success')
                        return redirect(url_for('orders.order_details', order_id=order_id))

                    except Exception as e:
                        mysql.connection.rollback()
                        flash(f'Ошибка обновления заказа: {str(e)}', 'danger')
                        print(f"Database error: {str(e)}")
                else:
                    flash('Ошибка валидации формы. Проверьте введённые данные.', 'danger')

            # Предзаполняем форму текущими данными для GET-запроса или после неудачной валидации
            form.shop_id.data = str(order['shop_id'])  # Преобразуем в строку для SelectField
            # Очищаем текущие элементы формы
            while len(form.items) > 0:
                form.items.pop_entry()
            # Заполняем форму данными из order_items
            for item in items:
                form.items.append_entry({
                    'product_id': str(item['product_id']),  # Преобразуем в строку
                    'quantity': item['quantity']
                })
            # Устанавливаем choices для всех полей товаров
            for item in form.items:
                item.form.product_id.choices = product_choices

            # Отладочный вывод
            print(f"Order: {order}")
            print(f"Items: {items}")
            print(f"Form data: {form.data}")

            return render_template('orders/edit.html', form=form, order_id=order_id)

    except Exception as e:
        current_app.logger.error(f"Error in edit_order: {str(e)}")
        flash('Ошибка при загрузке страницы редактирования', 'danger')
        return redirect(url_for('orders.list_orders'))