import argparse
import csv
import fdb
import os
import shutil

def fetch_study_results(database_path_medical, database_path_mkb10):  # noqa: WPS210
    """
    Fetch study results from the medical and MKB10 databases.

    Args:
        database_path_medical (str): Path to the medical database.
        database_path_mkb10 (str): Path to the MKB10 database.

    Returns:
        tuple: Three dictionaries: study_results, mkb10_values, and image_names.
    """
    con_medical = fdb.connect(  # noqa: S106
        dsn=database_path_medical,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    con_mkb10 = fdb.connect(  # noqa: S106
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

    cur_mkb10 = con_mkb10.cursor()
    cur_mkb10.execute('SELECT MKB_VALUES FROM MKB10')
    for row in cur_mkb10.fetchall():
        mkb_value = row[0].split(' ')[0]
        mkb10_values[mkb_value] = row[0]
    select_command = """
            SELECT I.IMAGE_NAME, S.STUDY_UID 
            FROM IMAGES I 
            JOIN SERIES S ON I.SERIES_UID = S.SERIES_UID
        """
    cur_medical.execute(select_command)
    for row in cur_medical.fetchall():
        image_name = str(row[0])
        study_uid = str(row[1]).strip()
        if study_uid in study_results:
            image_names[study_uid] = image_name
    con_medical.close()
    con_mkb10.close()

    return study_results, mkb10_values, image_names


def write_study_results_to_csv(study_results, mkb10_values, image_names, output_filename):  # noqa: WPS210
    """
    Write the study results along with MKB descriptions and image names to a CSV file.

    Args:
        study_results (dict): Study results with study UID as key.
        mkb10_values (dict): MKB10 values with diagnosis code as key.
        image_names (dict): Image names with study UID as key.
        output_filename (str): Name of the resulting CSV file.
    """
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


def update_medical_database(database_path_medical, output_filename):
    """
    Remove specified columns from the 'patients' table in the medical database and save the updated database.

    Args:
        database_path_medical (str): Path to the medical database.
        output_filename (str): Name of the resulting updated database file.
    """
    # Создание копии базы данных с новым именем
    new_database_path = os.path.join(os.path.dirname(output_filename), 'Medical_update.gdb')
    shutil.copyfile(database_path_medical, new_database_path)

    # Подключение к новой базе данных
    con_medical = fdb.connect(
        dsn=new_database_path,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur_medical = con_medical.cursor()

    # Удаление индексов, которые мешают удалению столбцов
    indices_to_remove = ['PAT_IDX1', 'PAT_IDX2', 'PAT_IDX3']
    for index in indices_to_remove:
        cur_medical.execute(f'DROP INDEX {index}')
        con_medical.commit()

    # Удаление указанных столбцов из таблицы 'patients'
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

    # Закрытие подключения
    con_medical.close()

def main():
    """
    Parse arguments and process the databases.

    This function handles the command-line arguments and initiates
    the processing of the specified databases.
    """
    parser = argparse.ArgumentParser(
        description='Process medical databases and export study results to a CSV file.',
    )
    parser.add_argument('database_path_medical', type=str, help='Path to the medical database')
    parser.add_argument('database_path_mkb10', type=str, help='Path to the MKB10 database')
    parser.add_argument('output_filename', type=str, help='Name of the resulting CSV file')

    args = parser.parse_args()

    # Fetch and process study results
    study_results, mkb10_values, image_names = fetch_study_results(
        args.database_path_medical, args.database_path_mkb10,
    )
    write_study_results_to_csv(
        study_results, mkb10_values, image_names, args.output_filename,
    )

    # Update the medical database by removing the 'patients' table
    update_medical_database(args.database_path_medical, args.output_filename)


if __name__ == '__main__':
    main()
