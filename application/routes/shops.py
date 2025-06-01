from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from ..extensions import mysql
from ..forms import ShopForm

shops_bp = Blueprint('shops', __name__, url_prefix='/shops')

@shops_bp.route('/')
@login_required
def list_shops():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM shops")
    shops = cur.fetchall()
    cur.close()
    return render_template('shops/list.html', shops=shops)

@shops_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_shop():
    form = ShopForm()
    if form.validate_on_submit():
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO shops (name, address)
            VALUES (%s, %s)
        """, (form.name.data, form.address.data))
        mysql.connection.commit()
        cur.close()
        flash('Магазин добавлен!', 'success')
        return redirect(url_for('shops.list_shops'))
    return render_template('shops/add.html', form=form)