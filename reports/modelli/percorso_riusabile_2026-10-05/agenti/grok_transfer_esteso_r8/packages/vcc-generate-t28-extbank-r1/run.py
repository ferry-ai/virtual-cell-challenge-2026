import os, runpy, sys
from pathlib import Path
os.chdir("/kaggle/working")
sys.path.insert(0, "/kaggle/working")
runpy.run_path("/kaggle/working/driver.py", run_name="__main__")
