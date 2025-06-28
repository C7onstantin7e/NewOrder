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


def import_shops_from_excel(file_path):
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

        print(f"Найдено строк в Excel: {len(df)}")

        # Обрабатываем каждую строку
        for index, row in df.iterrows():
            total_rows += 1

            # Извлекаем и очищаем данные
            name = clean_string(row.iloc[0])
            legal_address = clean_string(row.iloc[1])  # Юридический адрес
            physical_address = clean_string(row.iloc[2])  # Физический адрес

            # Пропускаем строки без названия
            if not name:
                print(f"⚠️ Строка {index + 2}: Пропущено - отсутствует название магазина")
                skipped_rows += 1
                continue

            # Выбираем адрес по приоритету: физический > юридический
            address = physical_address if physical_address else legal_address

            # Пропускаем строки без адреса
            if not address:
                print(f"⚠️ Строка {index + 2}: '{name}' - Пропущено, отсутствуют оба адреса")
                skipped_rows += 1
                continue

            # Вставляем данные в базу
            try:
                cursor.execute(
                    "INSERT INTO shops (name, address) VALUES (%s, %s)",
                    (name, address)
                )
                imported_rows += 1
                print(f"✅ Строка {index + 2}: Успешно импортирован '{name}' - {address}")

            except mysql.connector.IntegrityError as e:
                # Обработка дубликатов (если name уникально)
                if "Duplicate entry" in str(e):
                    print(f"⚠️ Строка {index + 2}: Дубликат - магазин '{name}' уже существует")
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
        print(f"Пропущено (без названия/адреса): {skipped_rows}")
        print(f"Дубликатов: {duplicate_rows}")
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
    excel_file = "shop.xlsx"
    import_shops_from_excel(excel_file)