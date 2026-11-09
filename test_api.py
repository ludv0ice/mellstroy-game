import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = settings.database_path
        settings.database_path = str(Path(self.temp.name) / "test.db")
        self.client = TestClient(app)
        self.client.__enter__()
        self.base = "/api/v1"
        self.tarif = {"tarif_name": "Основной", "internet": 50, "count_minutes": 500, "count_sms": 100, "salary": "600.25"}
        response = self.client.post(self.base + "/tarifs", json=self.tarif)
        self.assertEqual(response.status_code, 201)
        self.tarif_id = response.json()["id_tarif"]
        self.person = {"number_phone": "+79001234567", "id_tarif": self.tarif_id, "lastname": "Иванов", "firstname": "Иван", "patronymic_name": "Иванович", "date_birthday": "1995-10-20", "pasport_serial": "0012", "pasport_number": "003456", "date_issue": "2016-01-01"}
        self.assertEqual(self.client.post(self.base + "/clients", json=self.person).status_code, 201)

    def tearDown(self):
        self.client.__exit__(None, None, None)
        settings.database_path = self.previous
        self.temp.cleanup()

    def get(self, path, **params):
        response = self.client.get(self.base + path, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_phone_and_birthday(self):
        other = {**self.person, "number_phone": "88001234567", "firstname": "Пётр", "date_birthday": "1990-01-01"}
        self.assertEqual(self.client.post(self.base + "/clients", json=other).status_code, 201)
        self.assertEqual(len(self.get("/clients/search/phone", phone="+7")), 1)
        self.assertEqual(len(self.get("/clients/search/phone", phone="8")), 1)
        self.assertEqual(self.get("/clients/search/phone", phone="44"), [])
        result = self.get("/clients/sorted-by-birthday")
        self.assertEqual(result[0]["date_birthday"], "1990-01-01")
        self.assertEqual(result[1]["full_name"], "Иванов Иван Иванович")
        self.assertEqual(set(result[0]), {"full_name", "date_birthday"})

    def test_passport_year_boundary(self):
        self.assertEqual(len(self.get("/clients/search/passport-year", year=2015)), 1)
        self.assertEqual(self.get("/clients/search/passport-year", year=2016), [])
        self.assertEqual(self.get("/clients/search/passport-year", year=9999), [])

    def test_cost_and_join(self):
        self.assertEqual(len(self.get("/clients/search/tarif-cost", minSalary="600.24")), 1)
        self.assertEqual(self.get("/clients/search/tarif-cost", minSalary="600.25"), [])
        result = self.get("/clients/with-tarif")
        self.assertEqual(result[0]["tarif"]["id_tarif"], self.tarif_id)
        self.assertEqual(result[0]["tarif"]["salary"], "600.25")
        self.assertEqual(self.get("/tarifs/by-client/+79001234567")["id_tarif"], self.tarif_id)

    def test_stats_include_empty_tarifs(self):
        self.assertEqual(self.client.post(self.base + "/tarifs", json={**self.tarif, "tarif_name": "Пустой"}).status_code, 201)
        stats = self.get("/tarifs/stats/client-count")
        self.assertEqual([row["client_count"] for row in stats], [1, 0])
        full = self.get("/tarifs/with-client-count")
        self.assertEqual([row["client_count"] for row in full], [1, 0])
        self.assertIn("salary", full[0])
        self.assertEqual(self.get(f"/tarifs/{self.tarif_id}/client-count"), {"tarif_id": self.tarif_id, "count": 1})
        self.assertEqual(len(self.get("/tarifs")), 2)

    def test_client_update_assignment_and_delete(self):
        path = self.base + "/clients/+79001234567"
        response = self.client.put(path, json={"lastname": "Петров", "id_tarif": None})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lastname"], "Петров")
        self.assertIsNone(self.get("/clients/with-tarif")[0]["tarif"])
        self.assertEqual(self.client.get(self.base + "/tarifs/by-client/+79001234567").status_code, 404)
        response = self.client.patch(self.base + "/clients/tarif", params={"phone": "+79001234567", "id_tarif": self.tarif_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get(f"/tarifs/{self.tarif_id}/client-count")["count"], 1)
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.delete(path).status_code, 404)

    def test_tarif_update_and_delete_conflict(self):
        path = self.base + f"/tarifs/{self.tarif_id}"
        response = self.client.put(path, json={"salary": "0.10", "count_sms": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["salary"], "0.1")
        self.assertEqual(response.json()["internet"], 50)
        self.assertEqual(self.client.delete(path).status_code, 409)
        self.client.delete(self.base + "/clients/+79001234567")
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.delete(path).status_code, 404)

    def test_missing_and_duplicate(self):
        self.assertEqual(self.client.post(self.base + "/clients", json=self.person).status_code, 409)
        self.assertEqual(self.client.post(self.base + "/clients", json={**self.person, "number_phone": "+79001234568", "id_tarif": 9999}).status_code, 404)
        self.assertEqual(self.client.put(self.base + "/clients/+79001234567", json={"id_tarif": 9999}).status_code, 404)
        self.assertEqual(self.client.put(self.base + "/tarifs/9999", json={}).status_code, 404)
        self.assertEqual(self.client.get(self.base + "/tarifs/9999/client-count").status_code, 404)
        self.assertEqual(self.client.patch(self.base + "/clients/tarif", params={"phone": "missing", "id_tarif": self.tarif_id}).status_code, 404)
        other = {**self.person, "number_phone": "+79001234568"}
        self.client.post(self.base + "/clients", json=other)
        self.assertEqual(self.client.put(self.base + "/clients/+79001234567", json={"number_phone": other["number_phone"]}).status_code, 409)

    def test_validation(self):
        for values in ({"salary": -1}, {"salary": "1.001"}, {"internet": -1}, {"tarif_name": " "}, {"salary": None}, {"unknown": 1}):
            response = self.client.put(self.base + f"/tarifs/{self.tarif_id}", json=values)
            self.assertEqual(response.status_code, 422, response.text)
        for values in ({"firstname": None}, {"date_issue": "1990-01-01"}, {"date_birthday": "2020-01-01"}, {"pasport_serial": "123"}, {"number_phone": "abc"}):
            response = self.client.put(self.base + "/clients/+79001234567", json=values)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get(self.base + "/clients/search/phone", params={"phone": "%"}).status_code, 422)
        self.assertEqual(self.client.get(self.base + "/clients/search/passport-year", params={"year": 0}).status_code, 422)
        self.assertEqual(self.client.get(self.base + "/clients/search/tarif-cost", params={"minSalary": -1}).status_code, 422)

    def test_phone_change_and_persistence(self):
        response = self.client.put(self.base + "/clients/+79001234567", json={"number_phone": "+79001234569"})
        self.assertEqual(response.status_code, 200)
        with TestClient(app) as second:
            result = second.get(self.base + "/clients/search/phone", params={"phone": "+7"}).json()
        self.assertEqual(result[0]["number_phone"], "+79001234569")
        self.assertEqual(result[0]["pasport_serial"], "0012")

    def test_docs(self):
        self.assertEqual(self.client.get(self.base + "/docs").status_code, 200)
        schema = self.get("/openapi.json")
        self.assertIn(self.base + "/clients/tarif", schema["paths"])
        self.assertIn("patch", schema["paths"][self.base + "/clients/tarif"])


if __name__ == "__main__":
    unittest.main()
