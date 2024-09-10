import fdb


def display_image_paths(database_path_medical):
    # Подключаемся к базе данных
    con_medical = fdb.connect(
        dsn=database_path_medical,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur_medical = con_medical.cursor()

    # Запрашиваем несколько значений IMAGE_PATH из таблицы IMAGES
    cur_medical.execute(f"SELECT IMAGE_PATH FROM IMAGES")
    image_paths = cur_medical.fetchall()

    # Выводим полученные пути на экран
    print("Примеры IMAGE_PATH из базы данных:")
    for idx, path in enumerate(image_paths):
        print(f"{idx + 1}. {path[0]}")

    # Закрываем подключение к базе данных
    con_medical.close()


if __name__ == "__main__":
    # Пример использования функции
    database_path_medical = "../results/Medical_update.gdb"
    display_image_paths(database_path_medical)
