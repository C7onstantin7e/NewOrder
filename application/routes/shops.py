from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..extensions import mysql
from ..forms import ShopForm

shops_bp = Blueprint('shops', __name__, url_prefix='/shops')

# Добавляем новый маршрут для создания магазина
@shops_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_shop():
    # Проверка прав доступа
    if current_user.role not in ['admin', 'moderator']:
        flash('У вас нет прав для добавления магазинов', 'danger')
        return redirect(url_for('main.dashboard'))

    form = ShopForm()

    if form.validate_on_submit():
        try:
            with mysql.connection.cursor() as cur:
                # Проверка уникальности названия
                cur.execute("SELECT id FROM shops WHERE name = %s", (form.name.data,))
                if cur.fetchone():
                    flash('Магазин с таким названием уже существует', 'danger')
                    return render_template('shops/add.html', form=form)

                # Добавление нового магазина
                cur.execute(
                    "INSERT INTO shops (name, address) VALUES (%s, %s)",
                    (form.name.data, form.address.data)
                )
                mysql.connection.commit()
                flash('Магазин успешно добавлен!', 'success')
                return redirect(url_for('shops.list_shops'))

        except Exception as e:
            flash(f'Ошибка при добавлении магазина: {str(e)}', 'danger')

    return render_template('shops/add.html', form=form)


@shops_bp.route('/')
@login_required
def list_shops():
    # Проверка прав доступа
    if current_user.role not in ['admin', 'moderator', 'operator']:
        flash('У вас нет прав для просмотра этой страницы', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        with mysql.connection.cursor() as cur:
            cur.execute("SELECT id, name, address FROM shops ORDER BY name")
            shops = cur.fetchall()
            return render_template('shops/list.html', shops=shops)
    except Exception as e:
        flash(f'Ошибка при загрузке магазинов: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))


@shops_bp.route('/edit/<int:shop_id>', methods=['GET', 'POST'])
@login_required
def edit_shop(shop_id):
    # Проверка прав доступа
    if current_user.role not in ['admin', 'moderator']:
        flash('У вас нет прав для редактирования магазинов', 'danger')
        return redirect(url_for('main.dashboard'))

    form = ShopForm()
    try:
        with mysql.connection.cursor() as cur:
            # Получение данных магазина
            cur.execute("SELECT id, name, address FROM shops WHERE id = %s", (shop_id,))
            shop = cur.fetchone()

            if not shop:
                flash('Магазин не найден', 'danger')
                return redirect(url_for('shops.list_shops'))

            # Обработка формы
            if form.validate_on_submit():
                cur.execute("""
                    UPDATE shops 
                    SET name = %s, address = %s 
                    WHERE id = %s
                """, (form.name.data, form.address.data, shop_id))
                mysql.connection.commit()
                flash('Магазин успешно обновлен!', 'success')
                return redirect(url_for('shops.list_shops'))

            # Заполнение формы данными
            if  request.method == 'GET':
                form.name.data = shop['name']
                form.address.data = shop['address']

    except Exception as e:
        flash(f'Ошибка при обновлении магазина: {str(e)}', 'danger')

    return render_template('shops/edit.html', form=form, shop_id=shop_id)


@shops_bp.route('/delete/<int:shop_id>', methods=['POST'])
@login_required
def delete_shop(shop_id):
    # Проверка прав доступа
    if current_user.role != 'admin':
        flash('У вас нет прав для удаления магазинов', 'danger')
        return redirect(url_for('shops.list_shops'))

    try:
        with mysql.connection.cursor() as cur:
            # Проверка связанных заказов
            cur.execute("SELECT COUNT(*) FROM orders WHERE shop_id = %s", (shop_id,))
            order_count = cur.fetchone()['COUNT(*)']

            if order_count > 0:
                flash('Нельзя удалить магазин с существующими заказами', 'danger')
                return redirect(url_for('shops.list_shops'))

            # Удаление магазина
            cur.execute("DELETE FROM shops WHERE id = %s", (shop_id,))
            mysql.connection.commit()
            flash('Магазин успешно удален', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении магазина: {str(e)}', 'danger')

    return redirect(url_for('shops.list_shops'))