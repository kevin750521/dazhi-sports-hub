import json
import os
import urllib.parse
import urllib.request
import urllib.error

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

SOURCE_FILE = "興雅國中（國女乙、高女乙）1014 1644.pdf"
SOURCE_URL = "https://drive.google.com/file/d/17KRMJ3eGu63T4tWW-FQh_w-KaoSoAEkt/view"
VENUE = "臺北市立興雅國中"

CANONICAL_GAMES = [
    {
        "date": "115/10/27",
        "time": "14:50",
        "opponents": ("育成高中", "大直高中"),
        "opponents_draw": "育成高中 vs 大直高中",
    },
    {
        "date": "115/10/30",
        "time": "11:20",
        "opponents": ("大直高中", "華江高中"),
        "opponents_draw": "大直高中 vs 華江高中",
    },
    {
        "date": "115/10/31",
        "time": "11:20",
        "opponents": ("大直高中", "泰北高中"),
        "opponents_draw": "大直高中 vs 泰北高中",
    },
]


def request(method, path, payload=None, prefer=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = dict(HEADERS)
    if prefer:
        headers["Prefer"] = prefer
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {body}") from e


def fetch_all(table):
    return request("GET", f"{table}?select=*") or []


def contains_pair(text, pair):
    text = str(text or "")
    return all(team in text for team in pair)


def row_id_sort(row):
    rid = row.get("id")
    try:
        return int(rid)
    except (TypeError, ValueError):
        return 10**18


def patch_high_girls_schedule():
    rows = fetch_all("schedules")

    for game in CANONICAL_GAMES:
        matches = []
        for row in rows:
            if "籃球" not in str(row.get("tournament_name", "")):
                continue
            if str(row.get("division", "")).strip() != "高女乙B組":
                continue
            if contains_pair(row.get("opponents_draw", ""), game["opponents"]):
                matches.append(row)

        if not matches:
            payload = {
                "sport": "🏀 籃球",
                "division": "高女乙B組",
                "tournament_name": "115學年度教育盃籃球賽",
                "match_date": f'{game["date"]} {game["time"]}',
                "match_time": game["time"],
                "venue": VENUE,
                "opponents_draw": game["opponents_draw"],
                "advancement_rule": "第一輪分組預賽",
                "source_file": SOURCE_FILE,
                "status": "賽程已公告（10/14更新）",
            }
            request("POST", "schedules", [payload], prefer="return=minimal")
            print("Inserted corrected game:", game)
            continue

        matches.sort(key=row_id_sort)
        keep = matches[0]
        keep_id = urllib.parse.quote(str(keep["id"]), safe="")
        payload = {
            "division": "高女乙B組",
            "match_date": f'{game["date"]} {game["time"]}',
            "match_time": game["time"],
            "venue": VENUE,
            "opponents_draw": game["opponents_draw"],
            "source_file": SOURCE_FILE,
            "status": "賽程已公告（10/14更新）",
        }
        request("PATCH", f"schedules?id=eq.{keep_id}", payload, prefer="return=minimal")
        print(f"Patched schedule id={keep.get('id')} -> {game['date']} {game['time']}")

        for dup in matches[1:]:
            dup_id = urllib.parse.quote(str(dup["id"]), safe="")
            request("DELETE", f"schedules?id=eq.{dup_id}", prefer="return=minimal")
            print(f"Deleted duplicate stale schedule id={dup.get('id')}")


def patch_tournament_summary():
    rows = fetch_all("tournaments")
    for row in rows:
        name = str(row.get("name", ""))
        if "教育盃" in name and "籃球" in name:
            rid = row.get("id")
            if rid is None:
                continue
            rid_q = urllib.parse.quote(str(rid), safe="")
            payload = {
                "competition_dates": "115/10/17～10/31（大直高中已公告明確場次）",
                "venue": "臺北市泰北國際雙語學校、臺北市立興雅國中、臺北市立永春高級中學",
                "doc_url": SOURCE_URL,
                "status": "✅ 10/14女子乙組新版賽程已整合：大直高中共13場明確賽程；高女乙B組更新至10/31",
            }
            request("PATCH", f"tournaments?id=eq.{rid_q}", payload, prefer="return=minimal")
            print(f"Patched tournament summary id={rid}")


if __name__ == "__main__":
    patch_high_girls_schedule()
    patch_tournament_summary()
    print("High-school girls basketball correction completed.")
