#!/usr/bin/env python3
"""Provision a read-only snapshot with the server key. Never run in a browser."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


EXPECTED_KEYS = {"transactions", "chequing", "payments", "statements", "manual_entries"}


def request_json(url: str, secret: str, method: str = "GET", body: object | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {secret}",
            "apikey": secret,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"Provisioning request failed ({error.code}): {detail}") from None


def find_user(url: str, secret: str, email: str) -> str:
    page = 1
    while True:
        result = request_json(f"{url}/auth/v1/admin/users?page={page}&per_page=1000", secret)
        users = result.get("users", [])
        for user in users:
            if str(user.get("email", "")).lower() == email.lower():
                return str(user["id"])
        if len(users) < 1000:
            raise SystemExit(f"No authenticated user exists for {email}.")
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an authenticated read-only profile snapshot.")
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--owner", required=True, help="Existing Supabase Auth owner email")
    parser.add_argument("--viewer", required=True, action="append", help="Existing viewer email; repeat as needed")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--title", default="Expense Tracker")
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    secret = os.environ.get("SUPABASE_SECRET_KEY", "")
    if not url or not secret:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SECRET_KEY in the server environment.")

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != EXPECTED_KEYS:
        raise SystemExit(f"Payload must contain exactly: {', '.join(sorted(EXPECTED_KEYS))}.")
    if any(not isinstance(payload[key], list) for key in EXPECTED_KEYS):
        raise SystemExit("Every snapshot payload field must be an array.")

    owner_id = find_user(url, secret, args.owner)
    profile = request_json(
        f"{url}/rest/v1/exp_shared_profiles?select=id",
        secret,
        "POST",
        {"owner_user_id": owner_id, "slug": args.slug, "display_name": args.name,
         "title": args.title, "schema_version": 1, "payload": payload},
    )[0]
    members = [
        {"profile_id": profile["id"], "user_id": find_user(url, secret, email), "role": "viewer"}
        for email in args.viewer
    ]
    request_json(f"{url}/rest/v1/exp_shared_profile_members", secret, "POST", members)
    print(f"Created profile {args.slug!r} for {len(members)} read-only viewer(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
