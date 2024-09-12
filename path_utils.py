from pathlib import Path


def replace_drive_with_folder(input_path, new_folder):
    # ������� ������ ���� � �������� ������ �� ����� �����
    new_path = Path(new_folder) / Path(*Path(input_path).parts[1:])
    return str(new_path)
