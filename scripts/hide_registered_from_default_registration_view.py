from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')

old = """          if (hideDeclined && currentRegFilter === '全部' && regStatus === '不報名') return false;\n          return matchSearch && matchSport && matchRegPill;"""
new = """          // 報名掌控的預設「全部」視圖只保留仍需處理的項目：\n          // 已報名與不報名都先隱藏；若使用者主動點選對應狀態仍可查看。\n          if (currentRegFilter === '全部' && regStatus === '已報名') return false;\n          if (hideDeclined && currentRegFilter === '全部' && regStatus === '不報名') return false;\n          return matchSearch && matchSport && matchRegPill;"""

if old not in text:
    raise SystemExit('target filter block not found')
text = text.replace(old, new, 1)

old_label = '預設過濾「不報名」項目 (精簡介面)'
new_label = '預設隱藏「已報名」與「不報名」項目 (只看待處理)'
text = text.replace(old_label, new_label, 1)

path.write_text(text, encoding='utf-8')
print('Updated registration control default view: hide registered and declined items.')
