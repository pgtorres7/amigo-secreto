import re

import requests

BASE = "http://127.0.0.1:3000"


def csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1)


def main() -> None:
    s = requests.Session()
    login = s.get(f"{BASE}/admin/login")
    s.post(
        f"{BASE}/admin/login",
        data={"csrf_token": csrf(login.text), "password": "natal2026", "submit": "Entrar"},
        allow_redirects=True,
    )
    dash = s.get(f"{BASE}/admin/")
    s.post(f"{BASE}/admin/limpar", data={"csrf_token": csrf(dash.text)}, allow_redirects=True)
    dash = s.get(f"{BASE}/admin/")
    add = s.post(
        f"{BASE}/admin/participantes",
        data={
            "csrf_token": csrf(dash.text),
            "names": "Ana Silva\nBruno Costa\nCarla Mendes",
            "submit": "Adicionar à lista",
        },
        allow_redirects=True,
    )
    pairs = re.findall(
        r"<strong>([^<]+)</strong>\s*<small>Senha: <strong>([^<]+)</strong></small>",
        add.text,
    )
    print("pairs", pairs)
    assert len(pairs) >= 3
    ana_pass = next(pw for name, pw in pairs if name == "Ana Silva")

    u = requests.Session()
    page = u.get(f"{BASE}/")
    bad = u.post(
        f"{BASE}/sortear",
        data={
            "csrf_token": csrf(page.text),
            "name": "Ana Silva",
            "access_password": "errada99",
            "submit": "Ver / Sortear",
        },
        allow_redirects=True,
    )
    assert "incorreta" in bad.text.lower(), bad.text[:500]

    page = u.get(f"{BASE}/")
    ok = u.post(
        f"{BASE}/sortear",
        data={
            "csrf_token": csrf(page.text),
            "name": "Ana Silva",
            "access_password": ana_pass,
            "submit": "Ver / Sortear",
        },
        allow_redirects=True,
    )
    assert "amigo secreto é" in ok.text.lower()
    print("smoke ok", ana_pass)


if __name__ == "__main__":
    main()
