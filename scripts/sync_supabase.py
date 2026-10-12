import json
import os
import re
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


def date_base(value):
    """Return the date portion so rows remain matchable after display time is appended."""
    text = str(value or "").strip()
    return text.split(" ", 1)[0]


def same(record, match):
    for key, expected in match.items():
        actual = record.get(key, "")
        if key == "match_date":
            if date_base(actual) != date_base(expected):
                return False
        elif str(actual).strip() != str(expected).strip():
            return False
    return True


def is_range_date(value):
    text = str(value or "")
    return any(mark in text for mark in ("～", "~", "至"))


def is_placeholder_time(value):
    text = str(value or "").strip()
    if not text:
        return True
    return any(word in text for word in ("待公告", "待大會", "待抽籤", "待排定", "待確認"))


def sanitize_for_table(table, payload):
    cleaned = dict(payload or {})
    if table == "schedules":
        # Supabase schedules schema目前沒有 doc_url 欄位。
        cleaned.pop("doc_url", None)

        # 表列模式只顯示 match_date，因此在有明確時間時把時間併入顯示欄位。
        # match_time 仍保留，之後若前端新增獨立時間欄可直接使用。
        match_date = str(cleaned.get("match_date", "")).strip()
        match_time = str(cleaned.get("match_time", "")).strip()
        if match_date and match_time and not is_range_date(match_date) and not is_placeholder_time(match_time):
            base = date_base(match_date)
            cleaned["match_date"] = f"{base} {match_time}"
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

            # Even when dashboard-sync values is {}, keep display date/time current from create.
            # This is needed because older rows stored only the date in match_date.
            if table == "schedules" and create:
                for key in ("match_date", "match_time"):
                    if key in create:
                        values[key] = create[key]

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


def cleanup_superseded_schedule_ranges():
    """
    User rule: once a tournament has precise schedule rows, remove its old date-range summary rows.
    This keeps the dashboard from showing both '10/18～10/29' and individual game times.
    """
    rows = fetch_all("schedules")
    precise_tournaments = {
        str(r.get("tournament_name", "")).strip()
        for r in rows
        if str(r.get("tournament_name", "")).strip()
        and not is_range_date(r.get("match_date", ""))
        and not is_placeholder_time(r.get("match_time", ""))
    }

    deleted = 0
    for row in rows:
        tournament = str(row.get("tournament_name", "")).strip()
        if tournament in precise_tournaments and is_range_date(row.get("match_date", "")):
            row_id = row.get("id")
            if row_id is None:
                continue
            encoded = urllib.parse.quote(str(row_id), safe="")
            request(
                "DELETE",
                f"schedules?id=eq.{encoded}",
                None,
                {"Prefer": "return=minimal"},
            )
            deleted += 1
            print(f"DELETED superseded range schedule id={row_id}: {tournament} / {row.get('match_date')}")

    print(f"cleanup: deleted {deleted} superseded range schedule rows")


with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

sync_table("tournaments", data.get("tournaments", []))
sync_table("schedules", data.get("schedules", []))
cleanup_superseded_schedule_ranges()
print("Dashboard sync completed.")
