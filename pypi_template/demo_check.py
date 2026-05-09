import sys
from pathlib import Path

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app import app

client = TestClient(app)

for path in ["/", "/search?q=template", "/projects/pypi-ds", "/health"]:
    response = client.get(path)
    response.raise_for_status()
    print(path, response.status_code)
