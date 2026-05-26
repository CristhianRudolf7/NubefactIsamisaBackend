import os
import sys
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from main import app
from app.routers import auth
from app.models.user import User, UserRole

client = TestClient(app)
mock_user = User(dni="12345678", nombre="Test User", rol=UserRole.ADMIN, puede_acceder_ventas=True, is_active=True)
app.dependency_overrides[auth.require_ventas_access] = lambda: mock_user
app.dependency_overrides[auth.require_authenticated] = lambda: mock_user
app.dependency_overrides[auth.require_admin] = lambda: mock_user

print("Testing /api/ventas (without trailing slash):")
r1 = client.get("/api/ventas")
print(f"Status Code: {r1.status_code}")
print(f"Body: {r1.text[:200]}\n")

print("Testing /api/ventas/ (with trailing slash):")
r2 = client.get("/api/ventas/")
print(f"Status Code: {r2.status_code}")
print(f"Body: {r2.text[:200]}\n")

print("Testing a health check endpoint:")
r3 = client.get("/health")
print(f"Status Code: {r3.status_code}")
print(f"Body: {r3.text}\n")
