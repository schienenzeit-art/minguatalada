import subprocess
import sys

try:
    subprocess.check_call([sys.executable, "-m", "py_compile", "services/pdf_service.py"])
    print('OK')
except subprocess.CalledProcessError as e:
    print('COMPILE_ERROR', e)
