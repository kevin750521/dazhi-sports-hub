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
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def fetch_tournaments():
    return request("GET", "tournaments?select=*") or []


def find_tournament(rows, sport_keyword):
    for row in rows:
        name = str(row.get("name", ""))
        if "教育盃" in name and sport_keyword in name:
            return row
    return None


def upsert_by_sport(rows, sport_keyword, payload):
    found = find_tournament(rows, sport_keyword)
    if found:
        row_id = urllib.parse.quote(str(found["id"]), safe="")
        request("PATCH", f"tournaments?id=eq.{row_id}", payload, "return=minimal")
        print(f"UPDATED {sport_keyword}: id={found['id']} name={found.get('name')}")
    else:
        inserted = request("POST", "tournaments", [payload], "return=representation")
        if inserted:
            rows.append(inserted[0])
        print(f"INSERTED {sport_keyword}: {payload['name']}")


rows = fetch_tournaments()

# 最新版：臺北市政府教育局115/10/14北市教體字第1153108248號函附件
# Drive 檔案：29714949_1153108248_ATTCH1.pdf
# 舊 BJ115.pdf 已由使用者自 Drive 刪除，不再作為來源。
tennis = {
    "name": "臺北市115學年度教育盃中學網球錦標賽",
    "sport": "網球",
    "divisions": "硬式：高男甲、高女甲、國男甲、國女甲、高中甲混雙、國中甲混雙；軟式：高男、高女、國男、國女、高中混雙、國中混雙",
    "competition_dates": "115/11/09～11/17（硬式）；115/11/18～11/19（軟式）",
    "venue": "臺北市網球中心（臺北市內湖區民權東路六段208號）",
    "reg_start": "115/10/15",
    "reg_deadline": "115/10/23 16:00",
    "reg_method": "新興國中網站『中學教育盃網球賽報名』線上報名；核章報名表於115/10/30 16:00前送190聯絡箱－新興國中學務處體育組",
    "doc_url": "https://drive.google.com/file/d/1sR_PTX845Oeq9wQGCxBUSCMztRoiLgRc/view",
    "status": "✅ 最新115/10/14正式規程已校正；115/10/26 16:00前公布接受名單；115/11/02 09:00於新興國中抽籤；大直高中實際報名組別與籤表待後續確認"
}
upsert_by_sport(rows, "網球", tennis)

# 臺北市115學年度教育盃中等學校桌球錦標賽競賽規程（115教育盃桌球.pdf）
table_tennis = {
    "name": "臺北市115學年度教育盃中等學校桌球錦標賽",
    "sport": "桌球",
    "divisions": "教師男/女團體；學生甲/乙組團體、單打、雙打；高中甲組/國中甲組混合雙打",
    "competition_dates": "115/12/12～12/17",
    "venue": "臺北市立麗山國民中學活動中心3樓（臺北市內湖區內湖路1段629巷42號）",
    "reg_start": "即日起",
    "reg_deadline": "115/11/06",
    "reg_method": "麗山國中教育盃桌球錦標賽報名系統線上報名＋核章紙本掛號郵寄或送達麗山國中體育組",
    "doc_url": "https://drive.google.com/file/d/1tpdOCCjrt25KNb5JOjGmKqQeEbiY2DKr/view",
    "status": "競賽規程已取得；115/11/19 15:00領隊會議後公開抽籤；大直高中實際報名項目與籤表待後續確認"
}
upsert_by_sport(rows, "桌球", table_tennis)


# 臺北市115學年度教育盃中小學滑輪溜冰錦標賽
# 最新來源：115/10/15 北市教體字第1153109189號函附件（2026/10/20 上傳）
skating = {
    "name": "臺北市115學年度教育盃中小學滑輪溜冰錦標賽",
    "sport": "滑輪溜冰",
    "divisions": "國中男、國中女、高中男、高中女、教師男、教師女；競速、自由式輪滑、花式溜冰（實際報名組別待確認）",
    "competition_dates": "自由式輪滑：115/12/07；競速：115/12/15～12/16（雨備12/17～12/18）；花式：116/05/03～05/04",
    "venue": "自由式輪滑、花式：臺北市大同運動中心5樓；競速：臺北市立迎風河濱公園",
    "reg_start": "115/10/19（競速、自由式輪滑）；116/03/22（花式）",
    "reg_deadline": "115/10/30 16:00（競速、自由式輪滑）；116/03/29 16:00（花式）",
    "reg_method": "葫蘆國小網站『溜冰錦標賽』或 https://tpska.neoqqf.com.tw/index.php 線上報名；列印核章後掃描，於各類截止前寄至 ckh5225@hrps.tp.edu.tw。競速／自由式輪滑抽籤115/11/09 14:00；花式抽籤116/04/12 10:00，均在葫蘆國小",
    "doc_url": "https://drive.google.com/file/d/1HbHAibau9z4dfNvRXjWe3oHJceFL1UM-/view",
    "status": "最新115/10/15正式規程；競速與自由式輪滑115/10/30 16:00截止，花式116/03/29 16:00截止；大直是否報名、選手名單及各場時間均待確認"
}
upsert_by_sport(rows, "滑輪溜冰", skating)

print("Education Cup regulations sync completed.")
