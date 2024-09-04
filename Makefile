setup:
	python3.10 -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt
	
run_default:
	python main.py DB/MEDICAL.GDB DB/MKB10.GDB results

create_exe:
	pyinstaller --onefile --name svkvrngn main.py

run_exe:
	dist/svkvrngn.exe DB/MEDICAL.GDB DB/MKB10.GDB results