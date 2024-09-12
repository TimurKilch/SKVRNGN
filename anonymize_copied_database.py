#!/usr/bin/env python

import argparse
import os
import sys
from anonymization_utils import anonymize_dicom_file, anonymize_medical_database
from tqdm import tqdm


def find_dicom_files(directory):
    """
    Recursively find all .dcm files in the given directory and its subdirectories.

    Parameters:
        directory (str): The root directory to start the search.

    Returns:
        list: A list of full paths to .dcm files.
    """
    dicom_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.dcm'):
                dicom_files.append(os.path.join(root, file))
    return dicom_files


def main():
    parser = argparse.ArgumentParser(
        description='Anonymize DICOM files and a medical database.'
    )
    parser.add_argument(
        'dicom_directory',
        help='Path to the directory containing DICOM files to anonymize.'
    )
    parser.add_argument(
        'database_path',
        help='Path to the medical database file to anonymize.'
    )
    args = parser.parse_args()

    dicom_directory = args.dicom_directory
    database_path = args.database_path

    # Anonymize DICOM files
    dicom_files = find_dicom_files(dicom_directory)
    if not dicom_files:
        print(f"No DICOM files found in directory: {dicom_directory}")
    else:
        for dicom_file_path in tqdm(dicom_files, desc="Anonymizing DICOM files", unit="file"):
            output_file_path = dicom_file_path  # Overwrite the original file
            try:
                anonymize_dicom_file(dicom_file_path, output_file_path)
            except Exception as e:
                print(f"Error anonymizing DICOM file {dicom_file_path}: {e}", file=sys.stderr)

    # Anonymize medical database
    try:
        anonymize_medical_database(database_path_medical=database_path, update_paths=False)
        print(f"Anonymized medical database: {database_path}")
    except Exception as e:
        print(f"Error anonymizing medical database {database_path}: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
