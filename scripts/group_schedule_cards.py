from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')

marker = '      } else {\n        // 大直出賽賽程'
marker_pos = text.find(marker)
if marker_pos == -1:
    raise SystemExit('schedule section marker not found')

grid_start = text.find("        if (currentView === 'grid') {", marker_pos)
if grid_start == -1:
    raise SystemExit('schedule grid start not found')

table_start = text.find("        } else if (currentView === 'table') {", grid_start)
if table_start == -1:
    raise SystemExit('schedule table branch not found')

new_grid = r'''        if (currentView === 'grid') {
          // 卡片網格：同一運動賽事彙整在同一個資訊框中。
          // 例如教育盃籃球的高男、高女、國男、國女與教職員組，全部整併為一張賽事卡。
          // 表格式頁面維持逐場條列，不受此邏輯影響。
          if (list.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding:60px; color:#94a3b8; font-weight:700;">無符合條件之賽程紀錄</div>';
            return;
          }

          const groupedCompetitions = new Map();

          list.forEach(s => {
            const visual = getSportVisual(s.sport);
            const coreTitle = extractCoreTournamentName(s.tournament_name, s.sport);
            // sport + 核心賽事名稱作為彙整鍵，可容忍正式名稱前綴略有不同。
            const groupKey = `${visual.cleanName}|||${coreTitle}`;

            if (!groupedCompetitions.has(groupKey)) {
              groupedCompetitions.set(groupKey, {
                visual,
                coreTitle,
                officialNames: new Set(),
                rows: []
              });
            }

            const group = groupedCompetitions.get(groupKey);
            group.officialNames.add(s.tournament_name || coreTitle);
            group.rows.push(s);
          });

          const sortScheduleRows = rows => rows.slice().sort((a, b) =>
            String(a.match_date || '').localeCompare(String(b.match_date || ''), 'zh-Hant', { numeric: true }) ||
            String(a.match_time || '').localeCompare(String(b.match_time || ''), 'zh-Hant', { numeric: true })
          );

          let html = '<div class="cards-grid-layout">';

          groupedCompetitions.forEach(group => {
            const rows = sortScheduleRows(group.rows);
            const divisions = new Map();

            rows.forEach(s => {
              const division = (s.division || '未標示組別').trim();
              if (!divisions.has(division)) divisions.set(division, []);
              divisions.get(division).push(s);
            });

            const first = rows[0];
            const officialName = first?.tournament_name || group.coreTitle;
            const visual = group.visual;
            const groupCount = divisions.size;
            const matchCount = rows.length;

            let divisionBlocks = '';
            divisions.forEach((divisionRows, division) => {
              const divisionVisual = divisionRows.map((s, idx) => {
                const opponent = s.opponents_draw || '對戰 / 籤位待確認';
                const venue = s.venue || '場地待確認';
                const rule = s.advancement_rule || '';
                const status = s.status || '';
                return `
                  <div style="padding:10px 0; ${idx ? 'border-top:1px solid #e2e8f0;' : ''}">
                    <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-bottom:5px;">
                      <div style="font-size:0.92rem; font-weight:900; color:#0f172a;">📅 ${s.match_date || '日期待確認'}</div>
                      ${status ? `<span style="font-size:0.7rem; font-weight:800; color:#047857; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:999px; padding:2px 7px;">${status}</span>` : ''}
                    </div>
                    <div style="font-size:0.88rem; font-weight:800; color:#1e3a8a; line-height:1.45; margin-bottom:4px;">🎯 ${opponent}</div>
                    <div style="font-size:0.78rem; color:#475569; line-height:1.45;">📍 ${venue}</div>
                    ${rule ? `<div style="font-size:0.76rem; color:#64748b; line-height:1.45; margin-top:3px;">🏆 ${rule}</div>` : ''}
                  </div>
                `;
              }).join('');

              divisionBlocks += `
                <section style="border:1px solid #dbe3ee; border-radius:12px; background:#ffffff; padding:12px 14px; min-width:0;">
                  <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:2px;">
                    <div style="font-size:0.92rem; font-weight:900; color:${visual.accent};">👥 ${division}</div>
                    <span style="font-size:0.68rem; color:#64748b; background:#f8fafc; border:1px solid #e2e8f0; border-radius:999px; padding:2px 7px; white-space:nowrap;">${divisionRows.length} 場</span>
                  </div>
                  ${divisionVisual}
                </section>
              `;
            });

            let footerActions = '';
            if (first?.sport && first.sport.includes('擊劍')) {
              footerActions = `
                <a href="https://www.ccjh.tp.edu.tw/" target="_blank" class="doc-link-btn" style="color:#16a34a;">🎯 承辦校籤表 ↗</a>
                <button class="btn-detail-outline" onclick="openDrawVerificationModal('fencing')">💡 查核說明</button>
              `;
            } else if (first?.sport && first.sport.includes('空手道')) {
              footerActions = `
                <a href="https://kfcjc.neoqqf.com.tw/" target="_blank" class="doc-link-btn" style="color:#7c3aed;">🎯 查核籤表 ↗</a>
                <button class="btn-detail-outline" onclick="openDrawVerificationModal('karate')">💡 查核說明</button>
              `;
            } else {
              footerActions = `<span style="font-size:0.74rem; color:#64748b; font-weight:700;">共 ${groupCount} 個組別・${matchCount} 場明確賽程</span>`;
            }

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
                    <span class="status-tag tag-active">${groupCount} 組・${matchCount} 場</span>
                  </div>

                  <div class="card-core-title-box" style="margin-bottom:12px;">
                    <h3 class="card-core-name">${group.coreTitle}</h3>
                    <div style="font-size:0.74rem; color:#64748b; margin-top:2px;">${officialName}</div>
                  </div>

                  <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(270px,1fr)); gap:10px; align-items:start;">
                    ${divisionBlocks}
                  </div>
                </div>

                <div class="card-action-footer" style="justify-content:flex-end; margin-top:12px;">
                  <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; justify-content:flex-end;">
                    ${footerActions}
                  </div>
                </div>
              </div>
            `;
          });

          html += '</div>';
          container.innerHTML = html;
'''

text = text[:grid_start] + new_grid + text[table_start:]
path.write_text(text, encoding='utf-8')
print('Updated schedule grid to aggregate one card per competition; table branch untouched.')
