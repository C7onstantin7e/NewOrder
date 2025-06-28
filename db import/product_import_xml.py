import pandas as pd
import mysql.connector
from mysql.connector import Error
import re


def clean_string(value):
    """Очистка строки от лишних пробелов и непечатаемых символов"""
    if pd.isna(value):
        return None
    cleaned = re.sub(r'\s+', ' ', str(value).strip())
    return cleaned if cleaned != '' else None


def normalize_unit(unit_str):
    """Нормализация единиц измерения"""
    if not unit_str:
        return 'шт'  # Значение по умолчанию

    unit_str = str(unit_str).lower().strip()
    if unit_str in ['кг', 'kg', 'килограммы', 'килограмм', 'kilo', 'kilogram']:
        return 'кг'
    return 'шт'  # Для всех остальных случаев


def determine_manufacturer(name):
    """Определяем производителя по названию товара"""
    if name.endswith(' х.д.'):
        return 'Хлебный двор', name[:-5].strip()
    return 'Свежая выпечка', name


def import_products_from_excel(file_path):
    try:
        # Читаем Excel файл
        df = pd.read_excel(file_path, sheet_name='Лист1', header=0, engine='openpyxl')

        # Подключаемся к базе данных
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='300132',
            database='flask_auth'
        )
        cursor = connection.cursor()

        # Счетчики для статистики
        total_rows = 0
        imported_rows = 0
        skipped_rows = 0
        duplicate_rows = 0
        xd_count = 0
        fresh_count = 0

        print(f"Найдено строк в Excel: {len(df)}")

        # Обрабатываем каждую строку
        for index, row in df.iterrows():
            total_rows += 1

            # Извлекаем и очищаем данные
            original_name = clean_string(row.iloc[0])  # Первая колонка - название
            unit = normalize_unit(row.iloc[1])  # Вторая колонка - единица измерения
            price = row.iloc[2]  # Третья колонка - цена

            # Пропускаем строки без названия
            if not original_name:
                print(f"⚠️ Строка {index + 2}: Пропущено - отсутствует название товара")
                skipped_rows += 1
                continue

            # Определяем производителя и очищаем название
            manufacturer, clean_name = determine_manufacturer(original_name)

            # Статистика по производителям
            if manufacturer == 'Хлебный двор':
                xd_count += 1
            else:
                fresh_count += 1

            # Проверяем цену
            try:
                # Преобразуем цену к целому числу
                price = int(float(price))
            except (ValueError, TypeError):
                print(f"⚠️ Строка {index + 2}: '{clean_name}' - Некорректная цена: {price}")
                skipped_rows += 1
                continue

            # Вставляем данные в базу
            try:
                cursor.execute(
                    "INSERT INTO products (name, manufacturer, price, unit) "
                    "VALUES (%s, %s, %s, %s)",
                    (clean_name, manufacturer, price, unit)
                )
                imported_rows += 1
                print(f"✅ Строка {index + 2}: Успешно импортирован "
                      f"'{clean_name}' - {manufacturer} ({price} ₽/{unit})")

            except mysql.connector.IntegrityError as e:
                # Обработка дубликатов (если name уникально)
                if "Duplicate entry" in str(e):
                    print(f"⚠️ Строка {index + 2}: Дубликат - товар '{clean_name}' уже существует")
                    duplicate_rows += 1
                else:
                    print(f"❌ Строка {index + 2}: Ошибка БД - {e}")
                connection.rollback()
            except Exception as e:
                print(f"❌ Строка {index + 2}: Ошибка - {e}")
                connection.rollback()

        # Фиксируем изменения
        connection.commit()

        # Статистика
        print("\n" + "=" * 50)
        print("Импорт завершен!")
        print(f"Всего обработано строк: {total_rows}")
        print(f"Успешно импортировано: {imported_rows}")
        print(f"Пропущено: {skipped_rows}")
        print(f"Дубликатов: {duplicate_rows}")
        print(f"Товаров Хлебный двор: {xd_count}")
        print(f"Товаров Свежая выпечка: {fresh_count}")
        print("=" * 50)

    except Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        if connection.is_connected():
            connection.rollback()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    # Укажите путь к вашему Excel-файлу
    excel_file = "product.xlsx"
    import_products_from_excel(excel_file)