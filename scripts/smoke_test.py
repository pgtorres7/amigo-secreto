import requests

BASE = "http://127.0.0.1:3000"


def main() -> None:
    s = requests.Session()
    csrf = s.get(f"{BASE}/api/csrf").json()["csrf_token"]
    headers = {"X-CSRFToken": csrf, "Content-Type": "application/json"}

    assert s.get(f"{BASE}/").status_code == 200
    assert s.get(f"{BASE}/sortear").status_code == 200
    assert "Família Monti" in s.get(f"{BASE}/").text

    s.post(f"{BASE}/api/admin/login", headers=headers, json={"password": "natal2026"}).raise_for_status()
    csrf = s.get(f"{BASE}/api/csrf").json()["csrf_token"]
    headers["X-CSRFToken"] = csrf

    s.post(f"{BASE}/api/admin/clear-all", headers=headers, json={}).raise_for_status()
    add = s.post(
        f"{BASE}/api/admin/participants",
        headers=headers,
        json={"names": "Ana Silva\nBruno Costa\nCarla Mendes"},
    )
    add.raise_for_status()
    passwords = {p["name"]: p["password"] for p in add.json()["passwords"]}

    bad = s.post(
        f"{BASE}/api/sortear",
        headers=headers,
        json={"name": "Ana Silva", "password": "errada99"},
    )
    assert bad.status_code == 401

    ok = s.post(
        f"{BASE}/api/sortear",
        headers=headers,
        json={"name": "Ana Silva", "password": passwords["Ana Silva"]},
    )
    ok.raise_for_status()
    assert ok.json()["receiver"]
    print("smoke ok")


if __name__ == "__main__":
    main()
