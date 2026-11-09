from decimal import Decimal

from fastapi import HTTPException


def get_tarif(db, tarif_id):
    row = db.execute("SELECT * FROM tarif WHERE id_tarif = ?", (tarif_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Тариф не найден")
    return tarif_data(row)


def tarif_data(row):
    result = dict(row)
    result["salary"] = Decimal(result["salary"]) / 100
    return result


def get_client(db, phone):
    row = db.execute("SELECT * FROM client WHERE number_phone = ?", (phone,)).fetchone()
    if row is None:
        raise HTTPException(404, "Клиент не найден")
    return dict(row)


def require_tarif(db, tarif_id):
    if tarif_id is not None:
        get_tarif(db, tarif_id)


def update(db, table, key, value, data):
    if data:
        fields = ", ".join(f"{field} = ?" for field in data)
        db.execute(f"UPDATE {table} SET {fields} WHERE {key} = ?", (*data.values(), value))


def joined_clients(db, min_salary=None):
    sql = """SELECT c.*, t.tarif_name, t.internet, t.count_minutes, t.count_sms, t.salary
             FROM client c LEFT JOIN tarif t ON c.id_tarif = t.id_tarif"""
    params = ()
    if min_salary is not None:
        sql += " WHERE t.salary > ?"
        params = (int(min_salary * 100),)
    result = []
    for row in db.execute(sql + " ORDER BY c.number_phone", params):
        data = dict(row)
        tarif = {key: data.pop(key) for key in ("tarif_name", "internet", "count_minutes", "count_sms", "salary")}
        data["tarif"] = tarif_data({"id_tarif": data["id_tarif"], **tarif}) if data["id_tarif"] is not None else None
        result.append(data)
    return result
