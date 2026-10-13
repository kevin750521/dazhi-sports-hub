import json
from pathlib import Path

PATH = Path('dashboard-sync.json')
with PATH.open('r', encoding='utf-8') as f:
    data = json.load(f)

data['audit_date'] = '2026-10-13'

tournament_name = '臺北市115學年度教育盃中等學校排球錦標賽'
source_url = 'https://drive.google.com/file/d/1OR97vdJ0Wcr148m_eGpetPL-87LpO4Wr/view'
source_file = '教育盃排球賽總賽程表.pdf'

# Upsert tournament summary operation
new_tournament = {
    'match': {'name': tournament_name},
    'values': {
        'sport': '排球',
        'divisions': '高男乙I組、教女A組（大直高中已有明確預賽）',
        'competition_dates': '115/10/23～10/25（大直高中4場明確預賽）',
        'venue': '臺北市立明湖國中、臺北市立內湖高中',
        'doc_url': source_url,
        'status': '✅ 最新賽程已整合：大直高中高男乙I組2場、教女A組2場，共4場明確賽程；決賽資格賽程待預賽結果後再補',
        'registration_status': '已報名'
    },
    'create': {
        'name': tournament_name,
        'sport': '排球',
        'divisions': '高男乙I組、教女A組（大直高中已有明確預賽）',
        'competition_dates': '115/10/23～10/25（大直高中4場明確預賽）',
        'venue': '臺北市立明湖國中、臺北市立內湖高中',
        'doc_url': source_url,
        'status': '✅ 最新賽程已整合：大直高中高男乙I組2場、教女A組2場，共4場明確賽程；決賽資格賽程待預賽結果後再補',
        'registration_status': '已報名'
    }
}

def same_tournament(op):
    return (op.get('match') or {}).get('name') == tournament_name

tournaments = data.setdefault('tournaments', [])
replaced = False
for i, op in enumerate(tournaments):
    if same_tournament(op):
        tournaments[i] = new_tournament
        replaced = True
        break
if not replaced:
    tournaments.append(new_tournament)

schedules_to_add = [
    {
        'match': {
            'tournament_name': tournament_name,
            'match_date': '115/10/23',
            'match_time': '14:20',
            'division': '高男乙I組'
        },
        'values': {},
        'create': {
            'sport': '🏐 排球',
            'division': '高男乙I組',
            'tournament_name': tournament_name,
            'match_date': '115/10/23',
            'match_time': '14:20',
            'venue': '臺北市立明湖國中（第一場地）',
            'opponents_draw': '中正高中 vs 大直高中',
            'advancement_rule': '高男乙預賽I組循環；分組第1名晉級決賽',
            'source_file': source_file,
            'doc_url': source_url,
            'status': '賽程已公告'
        }
    },
    {
        'match': {
            'tournament_name': tournament_name,
            'match_date': '115/10/24',
            'match_time': '11:00',
            'division': '高男乙I組'
        },
        'values': {},
        'create': {
            'sport': '🏐 排球',
            'division': '高男乙I組',
            'tournament_name': tournament_name,
            'match_date': '115/10/24',
            'match_time': '11:00',
            'venue': '臺北市立明湖國中（第一場地）',
            'opponents_draw': '大直高中 vs 景文高中',
            'advancement_rule': '高男乙預賽I組循環；分組第1名晉級決賽',
            'source_file': source_file,
            'doc_url': source_url,
            'status': '賽程已公告'
        }
    },
    {
        'match': {
            'tournament_name': tournament_name,
            'match_date': '115/10/25',
            'match_time': '11:50',
            'division': '教女A組'
        },
        'values': {},
        'create': {
            'sport': '🏐 排球',
            'division': '教女A組',
            'tournament_name': tournament_name,
            'match_date': '115/10/25',
            'match_time': '11:50',
            'venue': '臺北市立內湖高中（第四場地）',
            'opponents_draw': '延平中學 vs 大直高中',
            'advancement_rule': '教女預賽A組循環；分組第1名晉級決賽',
            'source_file': source_file,
            'doc_url': source_url,
            'status': '賽程已公告'
        }
    },
    {
        'match': {
            'tournament_name': tournament_name,
            'match_date': '115/10/25',
            'match_time': '15:30',
            'division': '教女A組'
        },
        'values': {},
        'create': {
            'sport': '🏐 排球',
            'division': '教女A組',
            'tournament_name': tournament_name,
            'match_date': '115/10/25',
            'match_time': '15:30',
            'venue': '臺北市立內湖高中（第三場地）',
            'opponents_draw': '大直高中 vs 中山女中',
            'advancement_rule': '教女預賽A組循環；分組第1名晉級決賽',
            'source_file': source_file,
            'doc_url': source_url,
            'status': '賽程已公告'
        }
    },
]

schedules = data.setdefault('schedules', [])

def key(op):
    m = op.get('match') or {}
    return (m.get('tournament_name'), m.get('match_date'), m.get('match_time'), m.get('division'))

for new_op in schedules_to_add:
    new_key = key(new_op)
    found = False
    for i, old in enumerate(schedules):
        if key(old) == new_key:
            schedules[i] = new_op
            found = True
            break
    if not found:
        schedules.append(new_op)

with PATH.open('w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('Applied volleyball schedule update:', len(schedules_to_add), 'confirmed Dazhi matches')
