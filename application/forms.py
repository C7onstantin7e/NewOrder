from flask_wtf import FlaskForm
from werkzeug.routing import ValidationError
from wtforms import StringField, PasswordField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from flask import request
from wtforms import StringField, IntegerField, FieldList, FormField, SubmitField
from application import mysql


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Роль', choices=[
        ('operator', 'Оператор'),
        ('moderator', 'Модератор'),
        ('admin', 'Администратор')
    ], validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')



class ProductItemForm(FlaskForm):
    name = StringField('Название товара', validators=[DataRequired()])
    manufacturer = StringField('Производитель', validators=[DataRequired()])
    price = IntegerField('Цена (в тенге)', validators=[DataRequired()])
    unit = SelectField('Единица измерения',
                       choices=[('piece', 'Штуки'), ('kg', 'Килограммы')],
                       default='piece')
    submit = SubmitField('Сохранить')

class MultiProductForm(FlaskForm):
    products = FieldList(
        FormField(ProductItemForm),
        min_entries=1,
        max_entries=25
    )
    submit = SubmitField('Сохранить все')

class ShopForm(FlaskForm):
    name = StringField('Название магазина', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    submit = SubmitField('Сохранить')

    def validate_name(self, field):
        # Проверка уникальности названия магазина
        shop_id = request.view_args.get('shop_id', 0)

        with mysql.connection.cursor() as cur:
            cur.execute("""
                SELECT id 
                FROM shops 
                WHERE name = %s AND id != %s
            """, (field.data, shop_id))
            existing = cur.fetchone()

            if existing:
                raise ValidationError('Магазин с таким названием уже существует')

## Подкласс если можно так сказать
class OrderItemForm(FlaskForm):
    product_id = SelectField('Товар', coerce=int, choices=[])
    quantity = IntegerField('Количество', validators=[DataRequired(), NumberRange(min=1)])

## Order.py
class OrderForm(FlaskForm):
    shop_id = SelectField('Магазин', coerce=int, choices=[])
    items = FieldList(FormField(OrderItemForm), min_entries=1)
    submit = SubmitField('Создать заказ')

class ProductForm(FlaskForm):
    name = StringField('Название товара', validators=[DataRequired()])
    manufacturer = StringField('Производитель', validators=[DataRequired()])
    price = IntegerField('Цена', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Сохранить')