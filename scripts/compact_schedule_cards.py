from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')
original = text

replacements = [
    ('                    <span class="card-full-name-sub" title="${s.tournament_name}">📋 ${s.tournament_name}</span>\n', ''),
    ('                  <span class="detail-lbl">🎯 對戰隊伍 / 分組籤位 (查核來源)</span>\n', ''),
    ('                  <span class="detail-lbl">🎯 對戰隊伍 / 分組籤位</span>\n', ''),
    ('                      <span class="detail-lbl">📍 比賽場館</span>\n                      <span class="detail-val">${s.venue}</span>', '                      <span class="detail-val">📍 ${s.venue}</span>'),
    ('                      <span class="detail-lbl">🏆 晉級賽制</span>\n                      <span class="detail-val">${s.advancement_rule || \'-\'}</span>', '                      <span class="detail-val">🏆 ${s.advancement_rule || \'-\'}</span>'),
    ('                  <span class="detail-val" style="color:#6d28d9; font-weight:800;">${s.opponents_draw}</span>', '                  <span class="detail-val" style="color:#6d28d9; font-weight:800;">🎯 ${s.opponents_draw}</span>'),
    ('                  <span class="detail-val" style="color:#047857; font-weight:800;">${s.opponents_draw}</span>', '                  <span class="detail-val" style="color:#047857; font-weight:800;">🎯 ${s.opponents_draw}</span>'),
    ('                  <span class="detail-val" style="color:#1e40af;">${s.opponents_draw}</span>', '                  <span class="detail-val" style="color:#1e40af;">🎯 ${s.opponents_draw}</span>'),
    ('                  <span style="font-size:0.75rem; color:#64748b;">來源：${s.source_file || \'官方公文\'}</span>\n', ''),
]

for old, new in replacements:
    text = text.replace(old, new)

# Keep action buttons aligned after removing source filename.
text = text.replace(
    '<div class="card-action-footer">\n                  <div style="display:flex; gap:6px;">',
    '<div class="card-action-footer" style="justify-content:flex-end;">\n                  <div style="display:flex; gap:6px;">'
)

if text == original:
    raise SystemExit('No expected schedule-card patterns were found; index.html was not changed.')

path.write_text(text, encoding='utf-8')
print('Compact schedule-card layout applied to index.html')
