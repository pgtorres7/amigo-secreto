from app import create_app
from app.services import add_participants, list_participants, list_participants_for_draw, status_summary

app = create_app()
with app.app_context():
    print("before", status_summary(), len(list_participants()))
    result = add_participants("Ana Silva\nBruno Costa\nCarla Mendes")
    print("add", result)
    print("after", status_summary(), list_participants_for_draw())
    client = app.test_client()
    home = client.get("/")
    print("home", home.status_code)
    print("has Ana", b"Ana Silva" in home.data)
    draw = client.post(
        "/sortear",
        data={"name": "Ana Silva", "submit": "Ver / Sortear"},
        follow_redirects=True,
    )
    # need CSRF - get token first
    home = client.get("/")
    import re

    html = home.data.decode("utf-8")
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    draw = client.post(
        "/sortear",
        data={"csrf_token": token, "name": "Ana Silva", "submit": "Ver / Sortear"},
        follow_redirects=True,
    )
    print("draw", draw.status_code)
    print("result?", "amigo secreto" in draw.data.decode("utf-8").lower())
    print(draw.data.decode("utf-8")[draw.data.decode("utf-8").find("result") : draw.data.decode("utf-8").find("result") + 300])
