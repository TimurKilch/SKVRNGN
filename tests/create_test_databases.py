"""
Код для создания 2-х тестовых баз данных: со всеми абсолютными путями и 50% абсолютных путей. Для тестов

"""
import fdb
import os
import shutil
import random


def create_test_database_with_absolute_paths(original_db_path, new_db_path, path_prefix):
    # Скопировать оригинальную базу данных в новую
    shutil.copyfile(original_db_path, new_db_path)

    # Подключение к новой базе данных
    con = fdb.connect(
        dsn=new_db_path,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur = con.cursor()

    # Запрос для получения всех путей изображений
    cur.execute("SELECT IMAGE_PATH FROM IMAGES")
    image_paths = cur.fetchall()

    # Обновление каждого IMAGE_PATH на абсолютный путь
    for (image_path,) in image_paths:
        if not os.path.isabs(image_path):
            new_image_path = os.path.join(path_prefix, image_path)
            cur.execute("UPDATE IMAGES SET IMAGE_PATH = ? WHERE IMAGE_PATH = ?", (new_image_path, image_path))
            con.commit()

    con.close()
    print(f"База данных '{new_db_path}' успешно создана с абсолютными путями для изображений.")


def create_test_database_with_mixed_paths(original_db_path, new_db_path, path_prefix):
    # Скопировать оригинальную базу данных в новую
    shutil.copyfile(original_db_path, new_db_path)

    # Подключение к новой базе данных
    con = fdb.connect(
        dsn=new_db_path,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur = con.cursor()

    # Запрос для получения всех путей изображений
    cur.execute("SELECT IMAGE_PATH FROM IMAGES")
    image_paths = cur.fetchall()

    # Случайное обновление 50% путей на абсолютные
    for (image_path,) in image_paths:
        if not os.path.isabs(image_path):
            if random.choice([True, False]):  # Случайный выбор, чтобы сделать 50% путей абсолютными
                new_image_path = os.path.join(path_prefix, image_path)
                cur.execute("UPDATE IMAGES SET IMAGE_PATH = ? WHERE IMAGE_PATH = ?", (new_image_path, image_path))
                con.commit()

    con.close()
    print(f"База данных '{new_db_path}' успешно создана с 50% абсолютных и 50% относительных путей для изображений.")


if __name__ == '__main__':
    # Путь к оригинальной базе данных
    original_db_path = '../DB/MEDICAL.GDB'
    # Путь к новой базе данных с абсолютными путями
    new_db_path_abs = '../DB/MEDICAL_ABS.GDB'
    # Путь к новой базе данных с 50% абсолютных и 50% относительных путей
    new_db_path_mixed = '../DB/MEDICAL_MIXED.GDB'
    # Префикс для добавления к относительным путям ИЗМЕНИТЬ ПОД СЕБЯ
    path_prefix = r'/DB'

    # Создание базы данных с абсолютными путями
    create_test_database_with_absolute_paths(original_db_path, new_db_path_abs, path_prefix)

    # Создание базы данных с 50% абсолютных и 50% относительных путей
    create_test_database_with_mixed_paths(original_db_path, new_db_path_mixed, path_prefix)
