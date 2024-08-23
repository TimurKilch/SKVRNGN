import os
import platform

def validate_system():
    if platform.architecture()[0][:2] == '64':
        if not os.path.exists('C:\\Program Files\\Firebird\\Firebird_2_5'):
            print('Вы используете х64 архитектуру Python, но у вас не установлен Firebird 2.5 x64!')
            print('Установщик находится в папке /installers/Firebird-2.5.0.26074_1_x64.exe')
        else:
            print('Вы используете х64 архитектуру Python, найден Firebird 2.5 x64')
    
    elif platform.architecture()[0][:2] == '32':
        if not os.path.exists('C:\\Program Files (x86)\\Firebird\\Firebird_2_5'):
            print('Вы используете х32 архитектуру Python, но у вас не установлен Firebird 2.5 x32!')
            print('Установщик находится в папке /installers/Firebird-2.5.0.26074_1_Win32_pdb.exe')
        else:
            print('Вы используете х32 архитектуру Python, найден Firebird 2.5 x32')
