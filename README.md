- Python 3.10.11
- Ubuntu 20.04
Setup:
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
or
```
make setup
```

### Run app:
```bash
python main.py path_to_MEDICAL.GDB path_to_MKB10.GDB path_to_results_dir
```

## Анонимизация скопированной базы данны
- Поиск всех .dcm файлов в указанной директории и удаление в них полей PatientName и PatientID
- Очистка из базы данных полей:
  + 'PATIENT_NAME'
  + 'PATIENT_NAME_R'
  + 'PATIENT_CASE_HISTORY_NUMBER'
  + 'PATIENT_ADDRESS_REGION'
  + 'PATIENT_ADDRESS_AREA'
  + 'PATIENT_ADDRESS_CITY'
  + 'PATIENT_ADDRESS_SHF'
  + 'PATIENT_NAME_STD'

Запуск:
```bash
python anonymize_copied_database.py /path/to/dicom_directory /path/to/database_file.gdb
```