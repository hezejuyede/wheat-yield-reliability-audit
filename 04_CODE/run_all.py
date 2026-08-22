#!/usr/bin/env python3
from pathlib import Path
import os, subprocess, sys, time
root=Path(__file__).resolve().parents[1]
env=os.environ.copy(); env['PROJECT_ROOT']=str(root); env['PYTHONDONTWRITEBYTECODE']='1'
start=time.time()
subprocess.run([sys.executable,str(root/'04_CODE'/'analysis.py')],check=True,env=env)
subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(root/'04_CODE'/'tests')],check=True,env=env)
print(f'ALL CHECKS PASSED in {time.time()-start:.2f} seconds')
