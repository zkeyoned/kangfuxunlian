"""使用临时数据库验证真实注册，不接触本机患者数据。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_temp = tempfile.TemporaryDirectory()
os.environ["REHAB_DATA_DIR"] = _temp.name
sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
from main import app
from fastapi.testclient import TestClient


class RegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db(seed=True)
        cls.client = TestClient(app)

    def register(self, username, **overrides):
        return self.client.post("/api/v1/auth/register", json={
            "username": username, "password": "test-only-1234", "display_name": "测试患者", "role": "patient", **overrides})

    def test_register_login_persistence_and_isolation(self):
        r = self.register(" Fresh@Example.test ")
        self.assertEqual(r.status_code, 201, r.text)
        r = self.client.post("/api/v1/auth/login", json={"username": "FRESH@EXAMPLE.TEST", "password": "test-only-1234"})
        self.assertEqual(r.status_code, 200)
        user = r.json()["user"]
        headers = {"Authorization": "Bearer " + r.json()["token"]}
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).json()["id"], user["id"])
        self.assertEqual(self.client.get("/api/v1/me/plan/today", headers=headers).json()["items"], [])
        with db.connect() as con:
            saved = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
            self.assertTrue(db.verify_password("test-only-1234", saved["password_hash"]))
            self.assertNotEqual(saved["password_hash"], "test-only-1234")
            self.assertIsNone(con.execute("SELECT therapist_id FROM patients WHERE user_id=?", (user["id"],)).fetchone()[0])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM audit_logs WHERE user_id=? AND action='register'", (user["id"],)).fetchone()[0], 1)
            other = con.execute("SELECT institution_id FROM users WHERE username='dr.lin'").fetchone()[0]
            self.assertNotEqual(saved["institution_id"], other)
        self.assertEqual(self.client.get("/api/v1/patients", headers=headers).status_code, 403)
        self.client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 401)

    def test_duplicate_is_atomic(self):
        self.assertEqual(self.register("dup@example.test").status_code, 201)
        with db.connect() as con:
            before = con.execute("SELECT COUNT(*) FROM institutions").fetchone()[0]
        self.assertEqual(self.register("DUP@example.test").status_code, 409)
        with db.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM institutions").fetchone()[0], before)

    def test_validation_and_no_self_elevation(self):
        for role in ("therapist", "admin"):
            self.assertEqual(self.register("role@example.test", role=role).status_code, 400)
        self.assertEqual(self.register("invalid").status_code, 400)
        self.assertEqual(self.register("short@example.test", password="123").status_code, 422)
        self.assertEqual(self.register("space@example.test", display_name=" ").status_code, 400)
        self.assertEqual(self.client.post("/api/v1/auth/login", json={"username":"missing@example.test", "password":"incorrect"}).json()["error"], "用户名或密码错误")


if __name__ == "__main__":
    unittest.main()
