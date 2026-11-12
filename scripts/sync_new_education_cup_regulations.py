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
    "divisions": "大直已報名：硬式國男甲、國女甲、高男甲、高女甲團體／單打／雙打及高中甲混雙；軟式國男、國女、高男、高女團體／單打／雙打及高中混雙。依實際報名表共33名不重複選手、47報名項次（硬式24、軟式23）。",
    "competition_dates": "正式規程：硬式115/11/09～11/17、軟式115/11/18～11/19；最新BJB115.xlsx場序：硬式11/09～11/13、軟式11/16～11/17（軟式日期與正式規程不一致，待主辦確認）",
    "venue": "臺北市網球中心（臺北市內湖區民權東路六段208號；場序表記載8面硬地）",
    "reg_start": "115/10/15",
    "reg_deadline": "115/10/23 16:00",
    "reg_method": "大直報名表已取得：33名選手、47報名項次；硬網24（4團體、9單打、8雙打、3混雙），軟網23（4團體、7單打、9雙打、3混雙）。教練：歐陽振漢、胡浩陽。官方場序：https://drive.google.com/file/d/1_sWNd3B2kdfJ4ouJIpVbYQk23P09TiXW/view",
    "doc_url": "https://drive.google.com/file/d/1sR_PTX845Oeq9wQGCxBUSCMztRoiLgRc/view",
    "registration_status": "已報名",
    "status": "✅ 大直高中已提供正式報名表（33選手、47報名項次）。115/11/04已取得BJB115.xlsx全大會場序；硬網團體11/09、硬網單雙打11/10～11/12、硬網混雙11/13；軟網場序列11/16～11/17，與正式規程11/18～11/19衝突。已收到成績：硬式高男團體第三、高女團體第三、李○瑾國女單打第三、曾○謙高男單打第四；其餘報名組別仍待賽／成績待確認。四筆成績逐場日期、比分待官方成績單核對。"
}
upsert_by_sport(rows, "網球", tennis)

# 臺北市115學年度教育盃中等學校桌球錦標賽競賽規程（115教育盃桌球.pdf）
table_tennis = {
    "name": "臺北市115學年度教育盃中等學校桌球錦標賽",
    "sport": "桌球",
    "divisions": "大直已報名4組：國男乙（團體1隊、單打3、雙打3）、國女乙（單打3、雙打2）、高男乙（單打3、雙打1）、高女乙（單打1、雙打1）；共19位不重複選手、18報名項次（團體1、單打10、雙打7）",
    "competition_dates": "115/12/12～12/17（各組實際出賽日期、對手和時間等待115/11/19抽籤公告）",
    "venue": "臺北市立麗山國民中學活動中心3樓（臺北市內湖區內湖路1段629巷42號）",
    "reg_start": "即日起",
    "reg_deadline": "115/11/06",
    "reg_method": "115/11/04取得4組線上系統產生的正式報名表。已報名：國男乙05156（團體／單打／雙打）、國女乙05144（單打／雙打）、高男乙05154（單打／雙打）、高女乙05143（單打／雙打）。報名表須校內核章並掛號郵寄麗山國中體育組；是否已寄送尚待確認。報名表：https://drive.google.com/file/d/1PicxSGlyLEiAHXsOL0rHry83_ftr576j/view（國男）；https://drive.google.com/file/d/1qYxq9XFBgYUvgXU6GBGgCxM2S_Sdp398/view（國女）；https://drive.google.com/file/d/1z5MPWfHxPq8R6STDso3sNo5Ng2XW8ehq/view（高男）；https://drive.google.com/file/d/174Da0JMBcIy6sMm36AgE38bI93i7-E_B/view（高女）",
    "doc_url": "https://drive.google.com/file/d/1tpdOCCjrt25KNb5JOjGmKqQeEbiY2DKr/view",
    "registration_status": "已報名",
    "status": "✅ 已有4組線上報名表、19名選手、18報名項次；尚須確認校內核章紙本是否於115/11/06前寄送／送達。115/11/19 15:00麗山國中領隊會議及抽籤；大直各場對手／時間待公告。"
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


# 115學年度中等學校排球聯賽競賽規程（運動部115/10/29備查）
# 此為「中等學校排球聯賽」，與「教育盃排球錦標賽」是兩項不同賽事。
volleyball_league = {
    "name": "115學年度中等學校排球聯賽",
    "sport": "排球",
    "divisions": "高中男生／高中女生／國中男生／國中女生各分甲級、乙級；大直實際報名組別尚待確認",
    "competition_dates": "各階段賽程、場次及日期尚待主辦單位公告（依正式規程未指定固定逐場日期）",
    "venue": "甲級由主辦實地勘查排定；乙級縣市預賽由競賽管理協調場地、複決賽另行公告",
    "reg_start": "即日起",
    "reg_deadline": "115/11/08（甲級）；115/11/15（乙級）",
    "reg_method": "中華民國高級中等學校體育總會線上報名；確認後列印報名表，學校核章及關防、連同職隊員個資授權書掛號郵寄體總（臺北市中山區朱崙街20號13樓）。甲級每隊最多14人、乙級最多18人；乙級每場可提出12人出賽。應完成執行教練證照與隨隊教師證明文件上傳。紙本及報名完成狀態待確認。",
    "doc_url": "https://drive.google.com/file/d/1bLyM-SO6vO8o5hgyEnPSJTESSg2owC_d/view",
    "registration_status": "待確認",
    "status": "📄 115學年度中等學校排球聯賽正式規程已取得：甲級115/11/08截止、乙級115/11/15截止。大直是否參賽及參賽級別尚待確認；各階段正式賽程／對戰／時間均待公告。"
}
league_found = next(
    (row for row in rows if "115" in str(row.get("name", ""))
     and "排球" in str(row.get("name", ""))
     and "聯賽" in str(row.get("name", ""))), None
)
if league_found:
    rid = urllib.parse.quote(str(league_found["id"]), safe="")
    request("PATCH", f"tournaments?id=eq.{rid}", volleyball_league, "return=minimal")
    print(f"UPDATED volleyball league: id={league_found['id']}")
else:
    inserted = request("POST", "tournaments", [volleyball_league], "return=representation")
    if inserted:
        rows.append(inserted[0])
    print("INSERTED volleyball league")


# 羽球已建立於賽程表，但主賽事表過去漏建，造成 KPI 計數未增加。
# 大直報名是否完成仍待確認；不將賽事區間當作個人實際出賽日。
badminton = {
    "name": "臺北市115學年度教育盃中等學校羽球錦標賽",
    "sport": "羽球",
    "divisions": "大直已確認報名2隊：高中男子乙組團體（10名學生），高中教師男子團體（7名教職員）；合計17名參賽人員。未見其他組別報名，勿列為大直出賽組別。",
    "competition_dates": "115/12/21～12/25（大會賽事區間；兩隊個別出賽日期及對手待11/17抽籤後公告）",
    "venue": "臺北體育館7樓羽球場（臺北市松山區南京東路4段10號）",
    "reg_start": "即日起",
    "reg_deadline": "115/11/03 17:00",
    "reg_method": "已取得大直羽球報名名單（報名序號115169781375、報名日期115/10/22）；高中男子乙組團體10人、高中教師男子團體7人。報名表：https://drive.google.com/file/d/1E7hWZRx2gqBcgAyquuSRvXTdhZZ5HQeG/view。正式規程要求核章紙本送達松山高中，是否送達尚待查證；115/11/05 16:00前公布接受名單、115/11/17 10:00松山高中抽籤。",
    "doc_url": "https://drive.google.com/file/d/10tNQo0Ggs-YTjz2DJ5Og46UhYEkpjqxB/view",
    "registration_status": "已報名",
    "status": "✅ 大直高中羽球團體報名名單已核對：高中男子乙組10人＋高中教師男子組7人，共2隊17人；115/10/22線上報名完成。比賽日期115/12/21～12/25；個別籤表、場次及核章紙本送達情形待確認。"
}
upsert_by_sport(rows, "羽球", badminton)

# 115學年度教育盃中小學空手道：教育局115/11/04核定規程（與全國中正盃不同賽事）
# 報名名單未提供，先列管報名待確認；不可沿用中正盃的孔同學資料。
education_cup_karate = {
    "name": "臺北市115學年度教育盃中小學空手道錦標賽",
    "sport": "空手道",
    "divisions": "正式規程設國中男子／女子、高中男子／女子形團體、形個人（甲乙丙）、對打個人（甲乙及體重級別）；大直高中實際報名組別和選手均待確認",
    "competition_dates": "115/12/11（五）～12/13（日）；個別組別賽程及場次待115/11/27抽籤後公告",
    "venue": "臺北市立內湖高級中學活動中心4樓（臺北市內湖區文德路218號）",
    "reg_start": "即日起",
    "reg_deadline": "115/11/24（二）線上報名；115/11/26（四）前寄送核章紙本",
    "reg_method": "https://tpekon.neoqqf.com.tw/index.php 線上報名並上傳段／級證書；列印報名表核章，於115/11/26前送交內湖高中體育組（郵寄、教育局聯絡箱228或親送）。115/11/27（五）09:30內湖高中體育組抽籤。大直報名情形尚待確認。",
    "doc_url": "https://drive.google.com/file/d/1Ckxipimf_2w3MJnxXLJdUwwiNjPkjL__/view",
    "registration_status": "未報名",
    "status": "📄 115/11/04教育局正式規程已取得；11/24線上報名截止、11/26核章紙本期限、11/27 09:30抽籤；12/11～12/13內湖高中比賽。大直報名程序待辦，尚無已完成報名紀錄；個別場次待確認。"
}
upsert_by_sport(rows, "空手道", education_cup_karate)

print("Education Cup regulations sync completed.")
