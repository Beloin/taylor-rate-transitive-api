from __future__ import annotations

USERS: dict[str, str] = {
    "duda": "dudinha123pass!!",
    "belois": "belois123pass!!",
    "taylor": "taylor123pass!!",
}


def authenticate(username: str, password: str) -> bool:
    return USERS.get(username) == password