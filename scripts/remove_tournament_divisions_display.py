from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')
original = s

# Remove tournament-card competition/division block to reduce card height.
card_block = '''                    <div class="detail-item">
                      <span class="detail-lbl">👥 參賽組別 (點擊文字可直接開啟官方來源查驗)</span>
                      <div class="detail-val">${customDivisionHtml}</div>
                    </div>
'''
s = s.replace(card_block, '')

# Remove tournament table division column (header + body cell).
s = s.replace('                    <th>參賽組別 (點擊查驗來源)</th>\n', '')

table_cell = '''                <td style="max-width:260px; font-size:0.8rem; font-weight:600;">
                  ${t.divisions && (t.divisions.includes('孔') || t.divisions.includes('劉')) ? `<span style="background:#fef3c7; color:#92400e; border:1px solid #fde68a; padding:1px 6px; border-radius:4px; font-weight:800; font-size:0.72rem; display:inline-block; margin-bottom:3px;">🌟 代表選手出賽</span><br>` : ''}
                  ${renderDivisionTableHtml(t, false)}
                </td>
'''
s = s.replace(table_cell, '')

# Remove the explicit division text inside the fencing athlete info badge as well.
s = s.replace('                    參賽組別：<strong>國中男子鈍劍個人組</strong><br>\n', '')

if s == original:
    print('No tournament division display blocks found; index.html unchanged.')
else:
    p.write_text(s, encoding='utf-8')
    print('Removed tournament division/group display from cards and tournament table.')
