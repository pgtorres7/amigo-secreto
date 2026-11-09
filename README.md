# Amigo Secreto (Flask)

Sistema de amigo secreto em **Python + Flask**, preparado para ficar público na web com foco em segurança no servidor.

## Segurança (o que realmente protege)

Bloquear F12 / Ctrl+U **não é segurança real** — qualquer pessoa consegue ver o HTML/JS do navegador.  
A proteção deste sistema é outra:

- resultado do sorteio **criptografado** no banco (AES-GCM + hash HMAC)
- a pessoa seleciona o **próprio nome** e sorteia (ou vê o resultado se já sorteou)
- resultado criptografado; o organizador **não vê** quem tirou quem
- admin com senha + sessão Flask + **CSRF**
- headers de segurança (CSP, X-Frame-Options, nosniff, etc.)
- rate limit no sorteio e no login admin

Mesmo abrindo F12, não há lista de resultados nem segredos do servidor no front.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

- Site: http://127.0.0.1:3000
- Admin: http://127.0.0.1:3000/admin/login

## Cadastro

No admin, um nome por linha:

```text
Ana Silva
Bruno Costa
Carla Mendes
```

No site, cada pessoa seleciona o nome e clica em **Ver / Sortear**.

## Variáveis (.env)

Veja `.env.example`. Em produção (Vercel):

- `SESSION_COOKIE_SECURE=true`
- `FORCE_HTTPS=true`
## GitHub + Vercel

1. Suba o código (`.env` não vai no Git)
2. Na Vercel, configure as variáveis de ambiente
3. Deploy com o `vercel.json` (entrada `api/index.py`)

> Observação: Flask em serverless na Vercel funciona, mas para carga maior Render/Railway/Fly também são ótimas opções.
