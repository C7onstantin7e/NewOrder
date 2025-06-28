from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ..extensions import mysql
from ..models import Product
from ..forms import ProductForm, MultiProductForm

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/')
@login_required
def list_products():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close()
    return render_template('products/list.html', products=products)

@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():

    if current_user.role != 'admin':
        flash('У вас нет прав для добавления продуктов', 'danger')
        return redirect(url_for('products.list_products'))

    form = ProductForm()
    if form.validate_on_submit():
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO products (name, manufacturer, price)
            VALUES (%s, %s, %s)
        """, (form.name.data, form.manufacturer.data, form.price.data))
        mysql.connection.commit()
        cur.close()
        flash('Товар добавлен!', 'success')
        return redirect(url_for('products.list_products'))
    return render_template('products/add.html', form=form)

@products_bp.route('/add_multi', methods=['GET', 'POST'])
@login_required
def add_multi_products():
    form = MultiProductForm()
    while len(form.products) < 5:
        form.products.append_entry()

    if form.validate_on_submit():
        try:
            cur = mysql.connection.cursor()
            for product in form.products.data:
                if product['name']:
                    cur.execute("""
                        INSERT INTO products (name, manufacturer, price)
                        VALUES (%s, %s, %s)
                    """, (product['name'], product['manufacturer'], product['price']))
            mysql.connection.commit()
            flash('Товары успешно добавлены!', 'success')
            return redirect(url_for('products.list_products'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
        finally:
            cur.close()
    return render_template('products/add_multi.html', form=form)

@products_bp.route('/ajax/add_row')
@login_required
def ajax_add_row():
    form = MultiProductForm()
    form.products.append_entry()
    return render_template('products/_product_row.html',
                         product_form=form.products[-1],
                         index=len(form.products))