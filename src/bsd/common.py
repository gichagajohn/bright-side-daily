"""Bounded I/O, configuration and safe error reporting."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def config():
    return json.loads((ROOT / 'config/publishing.json').read_text())

def digest(text):
    return hashlib.sha256(' '.join(str(text).lower().split()).encode()).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()

def safe_error(exc):
    # Known local validation/transport errors are actionable; arbitrary library
    # exceptions can include credential-bearing URLs and are reduced to their type.
    message = str(exc) if type(exc) in (RuntimeError, ValueError) else 'operation failed'
    for name, value in os.environ.items():
        if value and len(value) >= 6 and any(word in name for word in ('TOKEN', 'KEY', 'PASSWORD', 'SECRET')):
            message = message.replace(value, '[REDACTED]')
    message = re.sub(r'https?://\S+', '[URL REDACTED]', message)
    return type(exc).__name__ + ': ' + message[:240]

def run(args, timeout=240):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('Media command failed: ' + Path(str(args[0])).name)
    return p.stdout

def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]))

def duration(path):
    return float(probe(path)['format']['duration'])

def write_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    temp.replace(path)

def enabled(name):
    return os.getenv(name, '').lower() == 'true'
