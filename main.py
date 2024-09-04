import argparse
import csv
import fdb
import os
import shutil
import logging
from pydicom import dcmread
from check_health import validate_system
from datetime import datetime
from pathlib import Path

# Настройка логирования
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename=f'logs\\medical_data_processing_{datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}.log',
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


def write_study_results_to_csv(study_results, mkb10_values, image_names, output_filename):
    fields = ['Image Name', 'Study UID', 'Study Result', 'MKB Description']
    with open(output_filename, 'w', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()

        for study_uid, study_result in study_results.items():
            diagnosis_code = study_result.split(' ')[0]
            mkb_description = mkb10_values.get(diagnosis_code, 'Description not found')
            image_name = image_names.get(study_uid, 'Not found')
            writer.writerow({
                'Image Name': image_name,
                'Study UID': study_uid,
                'Study Result': study_result,
                'MKB Description': mkb_description,
            })


def update_medical_database(database_path_medical, output_dir):
    new_database_path = os.path.join(output_dir, 'Medical_update.gdb')
    shutil.copyfile(database_path_medical, new_database_path)

    con_medical = fdb.connect(
        dsn=new_database_path,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur_medical = con_medical.cursor()

    # Удаление индексов
    indices_to_remove = ['PAT_IDX1', 'PAT_IDX2', 'PAT_IDX3']
    for index in indices_to_remove:
        cur_medical.execute(f'DROP INDEX {index}')
        con_medical.commit()

    # Удаление ненужных столбцов
    columns_to_remove = [
        'PATIENT_NAME',
        'PATIENT_NAME_R',
        'PATIENT_CASE_HISTORY_NUMBER',
        'PATIENT_ADDRESS_REGION',
        'PATIENT_ADDRESS_AREA',
        'PATIENT_ADDRESS_CITY',
        'PATIENT_ADDRESS_SHF',
        'PATIENT_NAME_STD'
    ]
    for column in columns_to_remove:
        cur_medical.execute(f'ALTER TABLE patients DROP {column}')
        con_medical.commit()

    # Обновление путей изображений, если они абсолютные
    cur_medical.execute("SELECT IMAGE_PATH FROM IMAGES")
    images = cur_medical.fetchall()

    for image in images:
        original_image_path = str(image[0])
        if os.path.isabs(original_image_path):
            # Если путь абсолютный, меняем диск на output_dir/images
            new_image_path = replace_drive_with_folder(original_image_path, os.path.join(output_dir, 'images'))
            # Обновляем базу данных новым путем
            cur_medical.execute(f"UPDATE IMAGES SET IMAGE_PATH = ? WHERE IMAGE_PATH = ?", (new_image_path, original_image_path))
            con_medical.commit()

    con_medical.close()


def process_dicom_file(dicom_file_path, output_file_path):
    dicom_data = dcmread(dicom_file_path)

    if 'PatientName' in dicom_data:
        dicom_data.PatientName = 'Anonymous'

    if 'PatientID' in dicom_data:
        dicom_data.PatientID = '00000000'

    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    dicom_data.save_as(output_file_path)


def replace_drive_with_folder(input_path, new_folder):
    # Создаем объект пути и заменяем корень на новую папку
    new_path = Path(new_folder) / Path(*Path(input_path).parts[1:])
    return str(new_path)


def copy_images_and_process_dicom(image_names, database_path_medical, output_dir):
    if os.path.isabs(database_path_medical):
        base_dir = ""
    else:
        base_dir = os.path.dirname(database_path_medical)

    for study_uid, images in image_names.items():
        for image in images:
            original_image_path = os.path.join(base_dir, image)
            output_image_path = os.path.join(output_dir, image)

            # Т.к у нас здесь абсолютные пути, меняем том на путь до output_dir/images/
            # Т.е. том(диск) на output_dir/images
            output_image_path = replace_drive_with_folder(output_image_path, output_dir)

            process_dicom_file(original_image_path, output_image_path)


def main():
    parser = argparse.ArgumentParser(
        description='Process medical databases and export study results to a CSV file.',
    )
    parser.add_argument('database_path_medical', type=str, help='Path to the medical database')
    parser.add_argument('database_path_mkb10', type=str, help='Path to the MKB10 database')
    parser.add_argument('output_dir', type=str, help='Directory to save the results (CSV, GDB, and images)')

    validate_system()  # Info about sys

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Логирование столбцов для обеих баз данных
    log_columns_for_database(args.database_path_medical, "Medical Database")
    log_columns_for_database(args.database_path_mkb10, "MKB10 Database")

    # Основная обработка данных
    study_results, mkb10_values, image_names = fetch_study_results(
        args.database_path_medical, args.database_path_mkb10,
    )

    output_csv_path = os.path.join(args.output_dir, 'results.csv')
    write_study_results_to_csv(
        study_results, mkb10_values, image_names, output_csv_path,
    )

    update_medical_database(args.database_path_medical, args.output_dir)
    copy_images_and_process_dicom(image_names, args.database_path_medical, args.output_dir)

    print("Processing completed. Check the log file for details on missing MKB codes.")


if __name__ == '__main__':
    main()
