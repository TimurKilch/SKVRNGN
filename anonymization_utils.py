from pydicom import dcmread
import os
from typing import Optional
import shutil
import fdb
from path_utils import replace_drive_with_folder


def anonymize_dicom_file(dicom_file_path, output_file_path):
    dicom_data = dcmread(dicom_file_path)

    if 'PatientName' in dicom_data:
        dicom_data.PatientName = 'Anonymous'

    if 'PatientID' in dicom_data:
        dicom_data.PatientID = '00000000'

    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    dicom_data.save_as(output_file_path)


def anonymize_medical_database(
        database_path_medical: str,
        output_dir: Optional[str] = None,
        update_paths: bool = True) -> None:
    """
    Anonymize a medical database by removing sensitive information and updating image paths.

    If only `database_path_medical` is provided, the database at that path will be modified in-place.
    If `output_dir` is also provided, the original database will not be modified. Instead, a copy of
    the database will be saved to `output_dir` with the name 'Medical_update.gdb', and modifications
    will be applied to the copy.

    Parameters:
        database_path_medical (str): The path to the medical database file.
        output_dir (Optional[str]): The directory where the modified database will be saved.
                                    If None, the original database will be modified.
        update_paths (bool): Whether to update image paths in the database.

    Returns:
        None
    """
    # Determine the database path to work on
    if output_dir is not None:
        new_database_path = os.path.join(output_dir, 'Medical_update.gdb')
        shutil.copyfile(database_path_medical, new_database_path)
    else:
        new_database_path = database_path_medical

    # Connect to the database
    con_medical = fdb.connect(
        dsn=new_database_path,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur_medical = con_medical.cursor()

    # Deleting indices
    indices_to_remove = ['PAT_IDX1', 'PAT_IDX2', 'PAT_IDX3']
    for index in indices_to_remove:
        try:
            cur_medical.execute(f'DROP INDEX {index}')
            con_medical.commit()
        except fdb.DatabaseError as e:
            print(f"Error dropping index {index}: {e}")

    # Deleting unnecessary columns
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
        try:
            cur_medical.execute(f'ALTER TABLE patients DROP {column}')
            con_medical.commit()
        except fdb.DatabaseError as e:
            print(f"Error dropping column {column}: {e}")

    if update_paths:
        # Update image paths if they are absolute
        try:
            cur_medical.execute("SELECT IMAGE_PATH FROM IMAGES")
            images = cur_medical.fetchall()

            for image in images:
                original_image_path = str(image[0])
                if os.path.isabs(original_image_path):
                    # If path is absolute, replace drive with 'images' folder
                    new_image_path = replace_drive_with_folder(original_image_path, 'images')
                else:
                    # If path is relative, prepend 'images'
                    new_image_path = os.path.join('images', original_image_path)

                # Update the database with the new path
                cur_medical.execute(
                    "UPDATE IMAGES SET IMAGE_PATH = ? WHERE IMAGE_PATH = ?",
                    (new_image_path, original_image_path)
                )
                con_medical.commit()
        except fdb.DatabaseError as e:
            print(f"Error updating image paths: {e}")

    # Close the database connection
    con_medical.close()
