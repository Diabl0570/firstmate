import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

fixture, code, interface, stage, rc, settings, state, task_id = sys.argv[1:]

def sanitize(text):
    return text.replace(fixture, '<fixture>').replace(code, '<code-root>')

files = [Path(settings), Path(state) / (task_id + '.busy-state'), Path(state) / (task_id + '.busy-gen')]
records = []
for path in files:
    if not path.exists():
        records.append({'path': sanitize(str(path)), 'exists': False})
        continue
    record = {'path': sanitize(str(path)), 'exists': True, 'mode': oct(stat.S_IMODE(path.stat().st_mode))}
    try:
        data = path.read_bytes()
        record.update(sha256=hashlib.sha256(data).hexdigest(), byte_length=len(data))
        text = sanitize(data.decode())
        try:
            value = json.loads(text)
            if isinstance(value, dict) and isinstance(value.get('savedFixture'), str):
                value['savedFixture'] = {'length': len(value['savedFixture']), 'content': 'generic repeated fixture character'}
            record['state'] = value
        except ValueError:
            record['state'] = text
    except PermissionError:
        record['readable'] = False
    records.append(record)
parent = Path(settings).parent
record = {'interface': interface, 'stage': stage, 'product_exit': int(rc), 'output': sanitize(sys.stdin.read()), 'persisted_files': records, 'settings_directory_entries': sorted(p.name for p in parent.iterdir()) if parent.is_dir() else []}
with Path(os.environ['PHASE_EVIDENCE']).open('a') as stream:
    stream.write(json.dumps(record, sort_keys=True) + '\n')
