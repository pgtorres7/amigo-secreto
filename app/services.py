from __future__ import annotations

import random
import re
from typing import Any

from . import db
from .crypto_util import (
    decrypt_name,
    encrypt_name,
    generate_easy_password,
    hash_name,
    hash_token,
    name_key,
    normalize_name,
    verify_password,
)


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if not digits:
        return ""
    if digits.startswith("55") and len(digits) >= 12:
        return f"+{digits}"
    if len(digits) in {10, 11}:
        return f"+55{digits}"
    if str(phone).strip().startswith("+"):
        return f"+{digits}"
    return f"+{digits}"


def list_participants() -> list[dict]:
    return db.query_all(
        """
        SELECT id, name, name_key, phone, access_token_hash, created_at
        FROM public.participants
        ORDER BY name ASC
        """
    )


def get_participant_by_id(participant_id: str) -> dict | None:
    return db.query_one(
        "SELECT id, name, name_key, phone, access_token_hash FROM public.participants WHERE id = %s",
        (participant_id,),
    )


def get_participant_by_name(name: str) -> dict | None:
    return db.query_one(
        """
        SELECT id, name, name_key, phone, access_token_hash
        FROM public.participants
        WHERE name_key = %s
        LIMIT 1
        """,
        (name_key(name),),
    )


def list_participants_for_draw() -> list[dict]:
    participants = list_participants()
    draws = {str(row["giver_id"]) for row in db.query_all("SELECT giver_id FROM public.draws")}
    return [
        {
            "id": str(person["id"]),
            "name": person["name"],
            "has_drawn": str(person["id"]) in draws,
        }
        for person in participants
    ]


def get_draw_for_giver(giver_id: str) -> dict | None:
    row = db.query_one(
        """
        SELECT id, giver_id, receiver_ciphertext, receiver_hash, created_at
        FROM public.draws
        WHERE giver_id = %s
        """,
        (giver_id,),
    )
    if not row:
        return None
    return {
        **row,
        "receiver_name": decrypt_name(row["receiver_ciphertext"]),
    }


def list_draws_decrypted() -> list[dict]:
    rows = db.query_all(
        """
        SELECT d.id, d.giver_id, d.receiver_ciphertext, d.receiver_hash, p.name AS giver_name
        FROM public.draws d
        INNER JOIN public.participants p ON p.id = d.giver_id
        """
    )
    return [{**row, "receiver_name": decrypt_name(row["receiver_ciphertext"])} for row in rows]


def status_summary() -> dict[str, Any]:
    participants = list_participants()
    draws = db.query_all("SELECT giver_id FROM public.draws")
    drawn_ids = {str(d["giver_id"]) for d in draws}
    return {
        "total": len(participants),
        "drawn_count": len(drawn_ids),
        "remaining_count": max(len(participants) - len(drawn_ids), 0),
    }


def add_participants(raw_lines: str) -> dict:
    lines = [line.strip() for line in str(raw_lines or "").splitlines() if line.strip()]
    added = []
    skipped = 0
    passwords = []

    for line in lines:
        normalized = line.replace(";", ",").replace("|", ",")
        if "," in normalized:
            name_part, phone_part = normalized.split(",", 1)
            name = normalize_name(name_part)
            phone = normalize_phone(phone_part) or "-"
        else:
            name = normalize_name(normalized)
            phone = "-"

        if not name:
            skipped += 1
            continue

        password = generate_easy_password(name)
        row = db.execute_returning(
            """
            INSERT INTO public.participants (name, name_key, phone, access_token_hash)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name_key) DO NOTHING
            RETURNING id, name, phone
            """,
            (name, name_key(name), phone, hash_token(password)),
        )
        if row:
            added.append(row)
            passwords.append({"id": str(row["id"]), "name": row["name"], "password": password})
        else:
            skipped += 1

    return {"added": added, "skipped": skipped, "passwords": passwords}


def regenerate_password(participant_id: str) -> str | None:
    participant = get_participant_by_id(participant_id)
    if not participant:
        return None
    password = generate_easy_password(participant["name"])
    db.execute(
        "UPDATE public.participants SET access_token_hash = %s WHERE id = %s",
        (hash_token(password), participant_id),
    )
    return password


def check_participant_password(participant: dict, password: str) -> bool:
    return verify_password(password, participant.get("access_token_hash"))


def delete_participant(participant_id: str) -> tuple[bool, str]:
    participant = get_participant_by_id(participant_id)
    if not participant:
        return False, "Participante não encontrado."

    related = db.query_one(
        """
        SELECT 1 AS ok FROM public.draws
        WHERE giver_id = %s OR receiver_hash = %s
        LIMIT 1
        """,
        (participant_id, hash_name(participant["name"])),
    )
    if related:
        return False, "Não é possível remover alguém que já participou de um sorteio."

    db.execute("DELETE FROM public.participants WHERE id = %s", (participant_id,))
    return True, "Participante removido."


def reset_draws() -> None:
    db.execute("DELETE FROM public.draws")


def clear_all() -> None:
    db.execute("DELETE FROM public.draws")
    db.execute("DELETE FROM public.participants")


def _choose_receiver(giver: dict) -> tuple[dict, dict | None]:
    participants = list_participants()
    draws = list_draws_decrypted()
    taken = {d["receiver_hash"] for d in draws}

    available = [
        p
        for p in participants
        if str(p["id"]) != str(giver["id"]) and hash_name(p["name"]) not in taken
    ]
    if available:
        return random.choice(available), None

    if not draws:
        raise ValueError("Não há opções válidas para o sorteio.")

    swap_draw = random.choice(draws)
    return {"name": swap_draw["receiver_name"]}, {
        "draw_id": swap_draw["id"],
        "new_receiver": giver,
    }


def perform_draw(giver: dict) -> dict:
    existing = get_draw_for_giver(str(giver["id"]))
    if existing:
        return {
            "already_drawn": True,
            "receiver": existing["receiver_name"],
            "draw_id": str(existing["id"]),
        }

    total = db.query_one("SELECT COUNT(*)::int AS total FROM public.participants")
    if not total or total["total"] < 2:
        raise ValueError("É preciso ter pelo menos 2 participantes cadastrados.")

    receiver, swap = _choose_receiver(giver)

    with db.get_conn() as conn:
        with conn.cursor() as cur:
            if swap:
                cur.execute(
                    """
                    UPDATE public.draws
                    SET receiver_ciphertext = %s, receiver_hash = %s
                    WHERE id = %s
                    """,
                    (
                        encrypt_name(swap["new_receiver"]["name"]),
                        hash_name(swap["new_receiver"]["name"]),
                        swap["draw_id"],
                    ),
                )

            cur.execute(
                """
                INSERT INTO public.draws (giver_id, receiver_ciphertext, receiver_hash)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (giver["id"], encrypt_name(receiver["name"]), hash_name(receiver["name"])),
            )
            inserted = cur.fetchone()
        conn.commit()

    return {
        "already_drawn": False,
        "receiver": receiver["name"],
        "draw_id": str(inserted["id"]),
    }


def admin_participant_rows() -> list[dict]:
    participants = list_participants()
    draws = {
        str(row["giver_id"]): row
        for row in db.query_all("SELECT giver_id, created_at FROM public.draws")
    }
    rows = []
    for person in participants:
        draw = draws.get(str(person["id"]))
        rows.append(
            {
                "id": str(person["id"]),
                "name": person["name"],
                "phone": person["phone"],
                "has_drawn": bool(draw),
                "has_token": bool(person.get("access_token_hash")),
            }
        )
    return rows
