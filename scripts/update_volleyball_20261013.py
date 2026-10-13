import json
from pathlib import Path

path = Path('dashboard-sync.json')
data = json.loads(path.read_text(encoding='utf-8'))

name = '臺北市115學年度教育盃中等學校排球錦標賽'
values = {
    'competition_dates': '115/10/22～10/27',
    'venue': '臺北市立明湖國民中學學生活動中心4樓、臺北市立內湖高級中學學生活動中心4樓',
    'reg_deadline': '115/09/29',
    'status': '✅ 官方更新：10/07已公告抽籤分組表；正式比賽10/22～10/27。因目前尚未取得可核實的大直高中逐場日期與時間，LINE晨報暫不列入排球賽程。',
    'reg_method': '依競賽規程辦理；抽籤已於115/10/07 10:00在明湖國中完成；領隊會議115/10/22 10:00於明湖國中學生活動中心4樓。'
}

tournaments = data.setdefault('tournaments', [])
found = False
for op in tournaments:
    if op.get('match', {}).get('name') == name:
        op.setdefault('values', {}).update(values)
        found = True
        break

if not found:
    tournaments.append({
        'match': {'name': name},
        'values': values,
        'create': {
            'name': name,
            'sport': '排球',
            **values
        }
    })

data['audit_date'] = '2026-10-13'
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('updated', name)
