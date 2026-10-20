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
    if any(mark in text for mark in ("～", "~", "至")):
        return True
    # Also treat 10/26-10/28, 115/10/26 - 115/10/28, etc. as ranges.
    return bool(re.search(r"\d{1,4}[/.\-]\d{1,2}(?:[/.\-]\d{1,2})?\s*[-–—]\s*\d{1,4}[/.\-]\d{1,2}", text))


def is_placeholder_time(value):
    text = str(value or "").strip()
    if not text:
        return True
    return any(word in text for word in ("待公告", "待大會", "待抽籤", "待排定", "待確認"))


def canonical_tournament_name(value):
    """Normalize equivalent tournament labels used by old summary rows and new detailed rows.

    Example:
      '115學年度 教育盃錦標賽'
      '115學年度教育盃排球賽'
      '臺北市115學年度教育盃中等學校排球錦標賽'
    all map to the same practical key: '115學年度教育盃'.
    """
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    for token in (
        "臺北市", "台北市", "中等學校", "中小學", "高級中學", "國民中學",
        "籃球", "排球", "羽球", "足球", "擊劍", "空手道", "高爾夫",
        "錦標賽", "競賽", "比賽", "賽",
    ):
        text = text.replace(token, "")
    return text


def sanitize_for_table(table, payload):
    cleaned = dict(payload or {})
    if table == "schedules":
        cleaned.pop("doc_url", None)

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

            if table == "schedules" and create:
                for key in ("match_date", "match_time"):
                    if key in create:
                        values[key] = create[key]

            # Preserve manually entered match results against later official-sheet re-syncs.
            # Only schedule metadata from source documents may change; result remains authoritative.
            if table == "schedules" and "已完賽" in str(found.get("status", "")):
                values.pop("status", None)

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
    """Delete old range-summary rows once precise rows for the same tournament exist.

    Tournament names in legacy rows are not always identical to the newer official name,
    so comparison is done with canonical_tournament_name(), not raw text equality.
    """
    rows = fetch_all("schedules")

    precise_keys = {
        canonical_tournament_name(r.get("tournament_name", ""))
        for r in rows
        if canonical_tournament_name(r.get("tournament_name", ""))
        and not is_range_date(r.get("match_date", ""))
        and not is_placeholder_time(r.get("match_time", ""))
    }

    deleted = 0
    for row in rows:
        tournament = str(row.get("tournament_name", "")).strip()
        tournament_key = canonical_tournament_name(tournament)
        if tournament_key in precise_keys and is_range_date(row.get("match_date", "")):
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
            print(
                "DELETED superseded range schedule "
                f"id={row_id}: {tournament} / {row.get('match_date')} / key={tournament_key}"
            )

    print(f"cleanup: deleted {deleted} superseded range schedule rows")


def cleanup_known_basketball_division_error():
    """Force the 115/10/28 09:00 Dazhi vs Jingmei game to 國女乙B組 and delete duplicates."""
    rows = fetch_all("schedules")
    targets = []
    for row in rows:
        tournament = str(row.get("tournament_name", ""))
        date = date_base(row.get("match_date", ""))
        time = str(row.get("match_time", "")).strip()
        opponents = str(row.get("opponents_draw", ""))
        if (
            "籃球" in tournament
            and date == "115/10/28"
            and time == "09:00"
            and "大直高中" in opponents
            and "景美國中" in opponents
        ):
            targets.append(row)

    if not targets:
        print("basketball correction: no matching row found")
        return

    # Keep one canonical row; patch it to the correct division.
    targets.sort(key=lambda r: int(r.get("id", 0)) if str(r.get("id", "")).isdigit() else 0)
    keep = targets[0]
    keep_id = urllib.parse.quote(str(keep.get("id")), safe="")
    request(
        "PATCH",
        f"schedules?id=eq.{keep_id}",
        {"division": "國女乙B組"},
        {"Prefer": "return=minimal"},
    )
    print(f"basketball correction: patched id={keep.get('id')} to 國女乙B組")

    # Remove any duplicate rows for the same game, regardless of their old division label.
    for row in targets[1:]:
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
        print(f"basketball correction: deleted duplicate id={row_id} division={row.get('division')}")


with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

sync_table("tournaments", data.get("tournaments", []))
sync_table("schedules", data.get("schedules", []))
cleanup_known_basketball_division_error()
cleanup_superseded_schedule_ranges()
print("Dashboard sync completed.")
