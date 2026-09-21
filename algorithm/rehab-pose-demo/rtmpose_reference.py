"""Verify the exact local reference; no automatic model fallback."""
from pathlib import Path
import hashlib
import importlib.metadata
import json

ROOT = Path(__file__).resolve().parent

def verify(root=ROOT, model_dir=None, check_runtime=True):
    root = Path(root)
    model_dir = Path(model_dir or root / 'models/rtmpose')
    ref = json.loads((root / 'config/rtmpose_reference.json').read_text())
    errors = []
    for name, expected in ref['models'].items():
        path = model_dir / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append('model:' + name)
    for name, expected in ref['source'].items():
        path = root / name
        if not path.exists() or hashlib.sha256(path.read_text(encoding='utf-8-sig').replace('\r\n','\n').encode()).hexdigest() != expected:
            errors.append('source:' + name)
    if check_runtime:
        for name, expected in ref['runtime'].items():
            try: actual = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: actual = None
            if actual != expected: errors.append('runtime:' + name)
    return {'ready': not errors, 'reference_id': ref['reference_id'], 'errors': errors}

if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['ready'] else 1)
