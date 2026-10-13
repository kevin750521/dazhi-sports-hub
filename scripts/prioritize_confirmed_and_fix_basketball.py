from pathlib import Path
import json

# 1) Permanently correct the known basketball division in sync data.
json_path = Path('dashboard-sync.json')
data = json.loads(json_path.read_text(encoding='utf-8'))

for t in data.get('tournaments', []):
    if '籃球' in str(t.get('match', {}).get('name', '')):
        for bucket in ('values', 'create'):
            if bucket in t and isinstance(t[bucket], dict):
                divisions = str(t[bucket].get('divisions', ''))
                if divisions:
                    t[bucket]['divisions'] = divisions.replace('國女甲B組', '國女乙B組')

for op in data.get('schedules', []):
    match = op.get('match', {})
    create = op.get('create', {})
    opponent = str(create.get('opponents_draw', ''))
    date = str(match.get('match_date', create.get('match_date', '')))
    time = str(match.get('match_time', create.get('match_time', '')))
    tournament = str(match.get('tournament_name', create.get('tournament_name', '')))
    if ('籃球' in tournament and date.startswith('115/10/28') and time == '09:00'
        and '大直高中' in opponent and '景美國中' in opponent):
        # Do not match by the previously-wrong division; date/time/opponents are the stable identity.
        match.pop('division', None)
        op.setdefault('values', {})['division'] = '國女乙B組'
        op.setdefault('create', {})['division'] = '國女乙B組'

json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# 2) Make Supabase cleanup authoritative: patch every matching row and remove duplicates.
sync_path = Path('scripts/sync_supabase.py')
sync = sync_path.read_text(encoding='utf-8')

func_marker = 'def cleanup_known_basketball_division_error():'
if func_marker not in sync:
    insert_at = sync.find('\n\nwith open(DATA_FILE, "r", encoding="utf-8") as f:')
    if insert_at == -1:
        raise SystemExit('sync insertion point not found')
    cleanup_func = r'''

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
'''
    sync = sync[:insert_at] + cleanup_func + sync[insert_at:]

# Ensure cleanup is invoked after normal sync, before range cleanup.
old_calls = 'sync_table("tournaments", data.get("tournaments", []))\nsync_table("schedules", data.get("schedules", []))\ncleanup_superseded_schedule_ranges()'
new_calls = 'sync_table("tournaments", data.get("tournaments", []))\nsync_table("schedules", data.get("schedules", []))\ncleanup_known_basketball_division_error()\ncleanup_superseded_schedule_ranges()'
if old_calls in sync:
    sync = sync.replace(old_calls, new_calls, 1)
elif 'cleanup_known_basketball_division_error()\ncleanup_superseded_schedule_ranges()' not in sync:
    raise SystemExit('sync call block not found')

sync_path.write_text(sync, encoding='utf-8')

# 3) In card-grid view, put competitions with precise date/time first; range/pending cards last.
html_path = Path('index.html')
html = html_path.read_text(encoding='utf-8')
needle = '          groupedCompetitions.forEach(group => {'
if needle in html and 'orderedCompetitionGroups' not in html:
    replacement = r'''          // Confirmed date/time competitions first; interval/pending schedules are pushed to the bottom.
          const orderedCompetitionGroups = Array.from(groupedCompetitions.values()).sort((a, b) => {
            const aPrecise = a.rows.some(hasPreciseDateTime);
            const bPrecise = b.rows.some(hasPreciseDateTime);
            if (aPrecise !== bPrecise) return aPrecise ? -1 : 1;

            const firstDate = group => {
              const row = group.rows.slice().sort((x, y) =>
                String(x.match_date || '').localeCompare(String(y.match_date || ''), 'zh-Hant', { numeric:true }) ||
                String(x.match_time || '').localeCompare(String(y.match_time || ''), 'zh-Hant', { numeric:true })
              )[0];
              return `${row?.match_date || ''} ${row?.match_time || ''}`;
            };
            return firstDate(a).localeCompare(firstDate(b), 'zh-Hant', { numeric:true });
          });

          orderedCompetitionGroups.forEach(group => {'''
    html = html.replace(needle, replacement, 1)
elif 'orderedCompetitionGroups' not in html:
    raise SystemExit('hybrid card grouping marker not found')

html_path.write_text(html, encoding='utf-8')
print('Applied definitive 國女乙B組 correction and prioritized precise schedules in card grid.')
