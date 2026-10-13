from pathlib import Path
import json

# 1) Correct the basketball division in dashboard-sync.json.
json_path = Path('dashboard-sync.json')
data = json.loads(json_path.read_text(encoding='utf-8'))

for t in data.get('tournaments', []):
    if t.get('match', {}).get('name') == '臺北市115學年度教育盃中等學校籃球錦標賽':
        values = t.setdefault('values', {})
        divisions = str(values.get('divisions', ''))
        values['divisions'] = divisions.replace('國女甲B組、', '').replace('國女甲B組', '國女乙B組')
        if 'create' in t:
            cdiv = str(t['create'].get('divisions', ''))
            t['create']['divisions'] = cdiv.replace('國女甲B組、', '').replace('國女甲B組', '國女乙B組')

for op in data.get('schedules', []):
    match = op.get('match', {})
    if (match.get('tournament_name') == '115學年度教育盃籃球賽'
        and str(match.get('match_date', '')).startswith('115/10/28')
        and match.get('match_time') == '09:00'):
        # Match by stable date/time instead of the incorrect division, so future syncs remain idempotent.
        match.pop('division', None)
        op.setdefault('values', {})['division'] = '國女乙B組'
        op.setdefault('create', {})['division'] = '國女乙B組'

json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# 2) Hybrid card-grid rendering:
#    - competitions with 2+ precise scheduled matches: one aggregated wide card
#    - information-light / not-yet-drawn competitions: old-style compact cards side-by-side
html_path = Path('index.html')
text = html_path.read_text(encoding='utf-8')
marker = '      } else {\n        // 大直出賽賽程'
marker_pos = text.find(marker)
if marker_pos == -1:
    raise SystemExit('schedule section marker not found')

grid_start = text.find("        if (currentView === 'grid') {", marker_pos)
table_start = text.find("        } else if (currentView === 'table') {", grid_start)
if grid_start == -1 or table_start == -1:
    raise SystemExit('schedule grid/table boundary not found')

new_grid = r'''        if (currentView === 'grid') {
          // 混合卡片模式：
          // 1. 已有多場明確日期+時間的賽事，彙整為同一張寬卡。
          // 2. 尚未抽籤 / 僅有區間日期 / 資訊量少的賽事，維持舊式小卡並排。
          // 3. 表格式頁面完全不受影響。
          if (list.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding:60px; color:#94a3b8; font-weight:700;">無符合條件之賽程紀錄</div>';
            return;
          }

          const hasPreciseDateTime = s => {
            const d = String(s.match_date || '');
            const t = String(s.match_time || '');
            if (/[～~至]/.test(d)) return false;
            if (/待公告|待抽籤|待排定|待確認|未定/.test(t)) return false;
            return /\b([01]?\d|2[0-3]):[0-5]\d\b/.test(d) || /\b([01]?\d|2[0-3]):[0-5]\d\b/.test(t);
          };

          const groupedCompetitions = new Map();
          list.forEach(s => {
            const visual = getSportVisual(s.sport);
            const coreTitle = extractCoreTournamentName(s.tournament_name, s.sport);
            const groupKey = `${visual.cleanName}|||${coreTitle}`;
            if (!groupedCompetitions.has(groupKey)) {
              groupedCompetitions.set(groupKey, { visual, coreTitle, rows: [] });
            }
            groupedCompetitions.get(groupKey).rows.push(s);
          });

          const sortRows = rows => rows.slice().sort((a, b) =>
            String(a.match_date || '').localeCompare(String(b.match_date || ''), 'zh-Hant', { numeric:true }) ||
            String(a.match_time || '').localeCompare(String(b.match_time || ''), 'zh-Hant', { numeric:true })
          );

          const compactCard = s => {
            const visual = getSportVisual(s.sport);
            const coreTitle = extractCoreTournamentName(s.tournament_name, s.sport);
            return `
              <div class="sport-card" style="border-top-color:${visual.color};">
                <div>
                  <div class="card-top-bar">
                    <div class="sport-visual-pill" style="background:${visual.bg}; border:1px solid ${visual.border}; color:${visual.accent};">
                      <div class="sport-visual-icon-box">${visual.icon}</div>
                      <div class="sport-visual-pill-name">
                        <span class="sport-zh">${visual.cleanName}</span>
                        <span class="sport-en">${visual.en}</span>
                      </div>
                    </div>
                    <span class="status-tag tag-active">${s.status || '資料待補'}</span>
                  </div>
                  <div class="card-core-title-box">
                    <h3 class="card-core-name">${coreTitle}</h3>
                  </div>
                  <div class="card-venue-row" style="align-items:flex-start;">
                    <span style="margin-top:2px;">👥</span>
                    <div style="flex:1;"><strong>${s.division || '組別待確認'}</strong></div>
                  </div>
                  <div class="card-date-chip"><span>📅</span> ${s.match_date || '日期待確認'}</div>
                  <div class="card-details-box">
                    <div class="detail-item"><span class="detail-val">🎯 ${s.opponents_draw || '尚未抽籤 / 對戰待確認'}</span></div>
                    <div class="detail-item"><span class="detail-val">📍 ${s.venue || '場地待確認'}</span></div>
                    <div class="detail-item"><span class="detail-val">🏆 ${s.advancement_rule || '-'}</span></div>
                  </div>
                </div>
              </div>
            `;
          };

          let html = '<div class="cards-grid-layout">';

          groupedCompetitions.forEach(group => {
            const rows = sortRows(group.rows);
            const preciseRows = rows.filter(hasPreciseDateTime);

            // 資訊量不足時維持舊的小卡並排，不硬撐成一張超寬空卡。
            if (preciseRows.length < 2) {
              rows.forEach(s => { html += compactCard(s); });
              return;
            }

            const divisions = new Map();
            preciseRows.forEach(s => {
              const division = (s.division || '未標示組別').trim();
              if (!divisions.has(division)) divisions.set(division, []);
              divisions.get(division).push(s);
            });

            const visual = group.visual;
            const first = preciseRows[0];
            let divisionBlocks = '';
            divisions.forEach((divisionRows, division) => {
              divisionBlocks += `
                <section style="border:1px solid #dbe3ee; border-radius:12px; background:#fff; padding:12px 14px; min-width:0;">
                  <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:4px;">
                    <div style="font-size:0.92rem; font-weight:900; color:${visual.accent};">👥 ${division}</div>
                    <span style="font-size:0.68rem; color:#64748b; background:#f8fafc; border:1px solid #e2e8f0; border-radius:999px; padding:2px 7px;">${divisionRows.length} 場</span>
                  </div>
                  ${divisionRows.map((s, idx) => `
                    <div style="padding:9px 0; ${idx ? 'border-top:1px solid #e2e8f0;' : ''}">
                      <div style="display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap; margin-bottom:4px;">
                        <strong style="color:#0f172a;">📅 ${s.match_date || ''}</strong>
                        ${s.status ? `<span style="font-size:0.68rem; font-weight:800; color:#047857; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:999px; padding:2px 7px;">${s.status}</span>` : ''}
                      </div>
                      <div style="font-size:0.86rem; font-weight:800; color:#1e3a8a;">🎯 ${s.opponents_draw || '對戰待確認'}</div>
                      <div style="font-size:0.76rem; color:#475569; margin-top:3px;">📍 ${s.venue || '場地待確認'}</div>
                    </div>
                  `).join('')}
                </section>
              `;
            });

            html += `
              <div class="sport-card" style="border-top-color:${visual.color}; grid-column:1 / -1;">
                <div>
                  <div class="card-top-bar" style="margin-bottom:8px;">
                    <div class="sport-visual-pill" style="background:${visual.bg}; border:1px solid ${visual.border}; color:${visual.accent};">
                      <div class="sport-visual-icon-box">${visual.icon}</div>
                      <div class="sport-visual-pill-name">
                        <span class="sport-zh">${visual.cleanName}</span>
                        <span class="sport-en">${visual.en}</span>
                      </div>
                    </div>
                    <span class="status-tag tag-active">${divisions.size} 組・${preciseRows.length} 場</span>
                  </div>
                  <div class="card-core-title-box" style="margin-bottom:12px;">
                    <h3 class="card-core-name">${group.coreTitle}</h3>
                    <div style="font-size:0.74rem; color:#64748b; margin-top:2px;">${first?.tournament_name || group.coreTitle}</div>
                  </div>
                  <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(270px,1fr)); gap:10px; align-items:start;">
                    ${divisionBlocks}
                  </div>
                </div>
                <div class="card-action-footer" style="justify-content:flex-end; margin-top:12px;">
                  <span style="font-size:0.74rem; color:#64748b; font-weight:700;">共 ${divisions.size} 個組別・${preciseRows.length} 場明確賽程</span>
                </div>
              </div>
            `;
          });

          html += '</div>';
          container.innerHTML = html;
'''

text = text[:grid_start] + new_grid + text[table_start:]
html_path.write_text(text, encoding='utf-8')
print('Corrected 國女乙B組 and applied hybrid grouped/compact schedule cards.')
