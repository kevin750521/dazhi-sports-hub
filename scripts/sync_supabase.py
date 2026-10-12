import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DATA_FILE = os.environ.get("SYNC_DATA_FILE", "dashboard-sync.json")

BASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def request(method, path, payload=None, extra_headers=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = dict(BASE_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return None
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} {method} {url}: {body}", file=sys.stderr)
        raise


def fetch_all(table):
    return request("GET", f"{table}?select=*") or []


def same(record, match):
    for key, expected in match.items():
        if str(record.get(key, "")).strip() != str(expected).strip():
            return False
    return True


def sanitize_for_table(table, payload):
    cleaned = dict(payload or {})
    if table == "schedules":
        cleaned.pop("doc_url", None)
    return cleaned


def sync_table(table, operations):
    existing = fetch_all(table)
    print(f"{table}: existing {len(existing)} rows")

    for op in operations:
        match = op.get("match", {})
        values = sanitize_for_table(table, op.get("values", {}))
        default_create = dict(match)
        default_create.update(values)
        create = sanitize_for_table(table, op.get("create", default_create))
        found = next((row for row in existing if same(row, match)), None)

        if found is not None:
            row_id = found.get("id")
            if row_id is None:
                raise RuntimeError(f"Matched {table} row has no id: {found}")
            encoded = urllib.parse.quote(str(row_id), safe="")
            if values:
                request(
                    "PATCH",
                    f"{table}?id=eq.{encoded}",
                    values,
                    {"Prefer": "return=minimal"},
                )
                found.update(values)
            print(f"UPDATED {table} id={row_id}: {match}")
        else:
            inserted = request(
                "POST",
                table,
                [create],
                {"Prefer": "return=representation"},
            )
            if isinstance(inserted, list) and inserted:
                existing.append(inserted[0])
                print(f"INSERTED {table} id={inserted[0].get('id')}: {match}")
            else:
                existing.append(create)
                print(f"INSERTED {table}: {match}")


with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

sync_table("tournaments", data.get("tournaments", []))
sync_table("schedules", data.get("schedules", []))
print("Dashboard sync completed.")
