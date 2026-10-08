"""Prevent laptop sleep during the authorized direct-cloud delivery handoff."""
import ctypes
from datetime import datetime,timezone
import os
from pathlib import Path
import time
from percorso import HERE,ROOT,write_new,now

write_new(HERE/'keep_awake_delivery_r1.json',dict(utc=now(),pid=os.getpid(),
    reason='keep local VCC completion coordinator available until upload finishes'))
if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise SystemExit(1)
try:
    while datetime.now(timezone.utc)<datetime(2026,10,9,0,30,tzinfo=timezone.utc):
        if (ROOT/'reports/invii/trial_2026-10-09/submit_t38_cloud_result.json').exists():break
        if (HERE/'stop_keep_awake_delivery_r1.json').exists():break
        time.sleep(10)
finally:
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    write_new(HERE/'keep_awake_delivery_stopped_r1.json',dict(utc=now(),pid=os.getpid()))
