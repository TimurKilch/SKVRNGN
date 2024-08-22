import os
import shutil
import fdb

def print_table_columns(database_path_medical):
    """
    Print all column names of the 'patients' table in the medical database.

    Args:
        database_path_medical (str): Path to the medical database.
    """
    # Connect to the database
    con_medical = fdb.connect(
        dsn=database_path_medical,
        user='sysdba',
        password='masterkey',
        charset='UTF8',
    )
    cur_medical = con_medical.cursor()

    # Fetch all columns for the 'patients' table
    cur_medical.execute("""
        SELECT rdb$field_name
        FROM rdb$relation_fields
        WHERE rdb$relation_name='PATIENTS'
    """)
    columns = cur_medical.fetchall()

    # Print all column names
    print("Columns in 'patients' table:")
    for column in columns:
        print(column[0].strip())

    # Close the connection
    con_medical.close()

# Usage example
database_path_medical = './Medical_update.gdb'
print_table_columns(database_path_medical)

