import tkinter as tk
from tkinter import filedialog, messagebox

import csv
import fdb
import os
import shutil
import logging
from datetime import datetime

from check_health import validate_system
from anonymization_utils import anonymize_dicom_file
from path_utils import replace_drive_with_folder


def logging_setup(output_dir):
    # Настройка логирования
    os.makedirs(os.path.join(output_dir, 'logs'), exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(output_dir,
                              f'logs\\medical_data_processing_{datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def get_all_columns(database_path):
    # Подключение к базе данных
    con = fdb.connect(
        dsn=database_path,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )

    cur = con.cursor()

    # SQL-запрос для получения всех таблиц и их столбцов
    query = """
        SELECT rdb$relation_name AS table_name, rdb$field_name AS column_name
        FROM rdb$relation_fields
        WHERE rdb$system_flag = 0
        ORDER BY rdb$relation_name, rdb$field_position
    """
    cur.execute(query)

    columns = cur.fetchall()

    # Создание словаря для хранения столбцов по таблицам
    table_columns = {}
    for row in columns:
        table_name = row[0].strip()
        column_name = row[1].strip()
        if table_name not in table_columns:
            table_columns[table_name] = []
        table_columns[table_name].append(column_name)

    con.close()
    return table_columns


def log_columns_for_database(database_path, db_name):
    logging.info(f"Проверка столбцов в {db_name}...")
    table_columns = get_all_columns(database_path)
    for table, columns in table_columns.items():
        logging.info(f"Таблица '{table}': Столбцы: {', '.join(columns)}")
    logging.info(f"Завершена проверка столбцов в {db_name}.")


def fetch_study_results(database_path_medical, database_path_mkb10):
    con_medical = fdb.connect(
        dsn=database_path_medical,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    con_mkb10 = fdb.connect(
        dsn=database_path_mkb10,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    study_results = {}
    mkb10_values = {}
    image_names = {}

    cur_medical = con_medical.cursor()
    cur_medical.execute('SELECT STUDY_UID, STUDY_RESULT FROM STUDIES')
    for row in cur_medical.fetchall():
        study_uid = str(row[0]).strip()
        study_result = str(row[1]).strip()
        study_results[study_uid] = study_result

    # Считывание значений MKB из таблицы MKB10
    cur_mkb10 = con_mkb10.cursor()
    cur_mkb10.execute('SELECT MKB_VALUES FROM MKB10')
    for row in cur_mkb10.fetchall():
        mkb_value = row[0].split(' ')[0]
        mkb10_values[mkb_value] = row[0]

    # Запрос для получения изображений и связанных UID
    select_command = """
            SELECT I.IMAGE_PATH, S.STUDY_UID 
            FROM IMAGES I 
            JOIN SERIES S ON I.SERIES_UID = S.SERIES_UID
        """
    cur_medical.execute(select_command)
    total_images = 0
    images_with_mkb = 0

    for row in cur_medical.fetchall():
        total_images += 1
        image_path = str(row[0])
        study_uid = str(row[1]).strip()

        if study_uid in study_results:
            study_result = study_results[study_uid]
            if study_uid in image_names:
                image_names[study_uid].append(image_path)
            else:
                image_names[study_uid] = [image_path]

            # Проверка наличия кода МКБ и логирование
            diagnosis_code = study_result.split(' ')[0]
            if diagnosis_code and diagnosis_code in mkb10_values:
                images_with_mkb += 1
            else:
                # Если код МКБ отсутствует или пустой
                logging.info(f"No valid MKB code found for study UID: {study_uid}, Image Path: {image_path}")
        else:
            # Логирование случаев, когда исследование не найдено в базе Medical
            logging.warning(f"Study UID {study_uid} not found in Medical database.")

    # Вывод информации в консоль
    print(f"Всего изображений: {total_images}")
    print(f"Всего изображений с кодом МКБ: {images_with_mkb}")

    con_medical.close()
    con_mkb10.close()

    return study_results, mkb10_values, image_names


def write_study_results_to_csv(study_results, mkb10_values, image_names, output_filename, output_dir):
    fields = ['Image Name', 'Study UID', 'Study Result', 'MKB Description']
    with open(output_filename, 'w', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()

        for study_uid, study_result in study_results.items():
            diagnosis_code = study_result.split(' ')[0]
            mkb_description = mkb10_values.get(diagnosis_code, 'Description not found')
            image_name = image_names.get(study_uid, 'Not found')

            new_image_paths = []
            for image_path in image_name:
                if os.path.isabs(image_path):
                    # Если путь абсолютный, меняем диск на images
                    new_image_path = replace_drive_with_folder(image_path, 'images')
                    new_image_paths.append(new_image_path)
                else:
                    # Если относительный, то добавляем в начало images
                    new_image_paths.append(os.path.join('images', image_path))
            writer.writerow({
                'Image Name': new_image_paths,
                'Study UID': study_uid,
                'Study Result': study_result,
                'MKB Description': mkb_description,
            })


def copy_images_and_process_dicom(image_names, database_path_medical, output_dir):
    # base_dir = os.path.dirname(database_path_medical)

    for study_uid, images in image_names.items():
        for image_path in images:
            pure_path = image_path
            if os.path.isabs(image_path):
                output_image_path = os.path.join(output_dir, image_path)
                output_image_path = replace_drive_with_folder(output_image_path, os.path.join(output_dir, 'images'))
            else:
                # Если относительные, то надо добавить путь по папки в которой лежит База
                prefix_dir = os.path.join(output_dir, 'images')
                output_image_path = os.path.join(prefix_dir, image_path)

                image_path = os.path.join(os.path.dirname(database_path_medical), image_path)
            try:
                anonymize_dicom_file(image_path, output_image_path)
            except Exception as E:
                logging.warning(f'Не найден или недоступен файл {pure_path}')


def browse_file(entry):
    file_path = filedialog.askopenfilename()
    if file_path:
        entry.delete(0, tk.END)
        entry.insert(0, file_path)


def browse_directory(entry):
    dir_path = filedialog.askdirectory()
    if dir_path:
        entry.delete(0, tk.END)
        entry.insert(0, dir_path)


def start_processing():
    medical_db_path = entry_medical_db.get()
    mkb10_db_path = entry_mkb10_db.get()
    output_dir = entry_output_dir.get()

    if not os.path.exists(medical_db_path) or not os.path.exists(mkb10_db_path):
        messagebox.showerror("Ошибка", "Указанные пути к файлам не существуют.")
        return

    if not os.path.isdir(output_dir):
        messagebox.showerror("Ошибка", "Указанный путь для сохранения результатов не является директорией.")
        return

    # Запуск всех функций для обработки
    validate_system()  # Info about sys

    os.makedirs(output_dir, exist_ok=True)

    logging_setup(output_dir)
    log_columns_for_database(medical_db_path, "Medical Database")
    log_columns_for_database(mkb10_db_path, "MKB10 Database")

    study_results, mkb10_values, image_names = fetch_study_results(
        medical_db_path, mkb10_db_path,
    )

    output_csv_path = os.path.join(output_dir, 'results.csv')
    write_study_results_to_csv(
        study_results, mkb10_values, image_names, output_csv_path, output_dir
    )

    update_medical_database(medical_db_path, output_dir)
    copy_images_and_process_dicom(image_names, medical_db_path, output_dir)

    messagebox.showinfo("Успех", "Обработка данных завершена. Проверьте журнал для получения деталей.")


root = tk.Tk()
root.title("Обработка медицинских данных")

# Поля для ввода путей с предзаполненными значениями

tk.Label(root, text="Путь к базе данных Medical:").grid(row=0, column=0, padx=5, pady=5)
entry_medical_db = tk.Entry(root, width=50)
entry_medical_db.grid(row=0, column=1, padx=5, pady=5)
tk.Button(root, text="Обзор", command=lambda: browse_file(entry_medical_db)).grid(row=0, column=2, padx=5, pady=5)

tk.Label(root, text="Путь к базе данных MKB10:").grid(row=1, column=0, padx=5, pady=5)
entry_mkb10_db = tk.Entry(root, width=50)
entry_mkb10_db.grid(row=1, column=1, padx=5, pady=5)
tk.Button(root, text="Обзор", command=lambda: browse_file(entry_mkb10_db)).grid(row=1, column=2, padx=5, pady=5)

tk.Label(root, text="Директория для сохранения результатов:").grid(row=2, column=0, padx=5, pady=5)
entry_output_dir = tk.Entry(root, width=50)
entry_output_dir.grid(row=2, column=1, padx=5, pady=5)
tk.Button(root, text="Обзор", command=lambda: browse_directory(entry_output_dir)).grid(row=2, column=2, padx=5, pady=5)

# Кнопка для запуска обработки
tk.Button(root, text="Запуск", command=start_processing).grid(row=3, column=1, pady=20)

root.mainloop()
