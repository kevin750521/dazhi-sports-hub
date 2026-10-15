const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  const indexPath = path.join(process.cwd(), 'index.html');
  let html = fs.readFileSync(indexPath, 'utf8');

  const dynamicCalendarScript = `
<script>
(() => {
  function rocDateParts(value) {
    const text = String(value || '').trim();
    if (!text || /[～~至]/.test(text)) return null;
    const base = text.split(' ')[0];
    const m = base.match(/^(\\d{2,4})\\/(\\d{1,2})\\/(\\d{1,2})$/);
    if (!m) return null;
    let year = Number(m[1]);
    if (year < 1911) year += 1911;
    const month = Number(m[2]);
    const day = Number(m[3]);
    const d = new Date(year, month - 1, day);
    if (Number.isNaN(d.getTime())) return null;
    return { date: d, year, month, day, key: year + '-' + String(month).padStart(2,'0') + '-' + String(day).padStart(2,'0') };
  }

  function fmtMD(d) {
    return (d.getMonth() + 1) + '/' + String(d.getDate()).padStart(2, '0');
  }

  function addDays(d, n) {
    const x = new Date(d);
    x.setDate(x.getDate() + n);
    return x;
  }

  function sportStyle(sport) {
    const s = String(sport || '');
    if (s.includes('籃球')) return { icon:'🏀', color:'#2563eb', bg:'#eff6ff', text:'#1e3a8a' };
    if (s.includes('排球')) return { icon:'🏐', color:'#0ea5e9', bg:'#f0f9ff', text:'#075985' };
    if (s.includes('擊劍')) return { icon:'🤺', color:'#16a34a', bg:'#f0fdf4', text:'#14532d' };
    if (s.includes('空手道')) return { icon:'🥋', color:'#7c3aed', bg:'#f5f3ff', text:'#6b21a8' };
    if (s.includes('網球')) return { icon:'🎾', color:'#059669', bg:'#ecfdf5', text:'#047857' };
    if (s.includes('棒球') || s.includes('黑豹旗')) return { icon:'⚾', color:'#dc2626', bg:'#fef2f2', text:'#991b1b' };
    return { icon:'🏅', color:'#64748b', bg:'#f8fafc', text:'#334155' };
  }

  function escHtml(v) {
    return String(v ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
  }

  window.renderCalendarView = function renderCalendarView() {
    const container = document.getElementById('contentContainer');
    if (!container) return;

    const all = Array.isArray(window.schedules) ? window.schedules : (typeof schedules !== 'undefined' ? schedules : []);
    const precise = all
      .map(s => ({ s, p: rocDateParts(s.match_date) }))
      .filter(x => x.p && String(x.s.match_time || '').trim() && !/待公告|待抽籤|待排定|待確認/.test(String(x.s.match_time || '')));

    const today = new Date(2026, 9, 15);
    today.setHours(0,0,0,0);
    const horizon = addDays(today, 31);
    const visible = precise.filter(x => x.p.date >= today && x.p.date <= horizon);

    let minDate = visible.length ? new Date(Math.min(...visible.map(x => x.p.date.getTime()))) : today;
    let maxDate = visible.length ? new Date(Math.max(...visible.map(x => x.p.date.getTime()))) : addDays(today, 21);

    const gridStart = addDays(minDate, -minDate.getDay());
    const gridEnd = addDays(maxDate, 6 - maxDate.getDay());

    const byDate = {};
    visible.forEach(({s,p}) => {
      (byDate[p.key] ||= []).push(s);
    });
    Object.values(byDate).forEach(list => list.sort((a,b) => String(a.match_time || '').localeCompare(String(b.match_time || ''))));

    const weekdays = ['週日','週一','週二','週三','週四','週五','週六'];
    let html = '<div class="calendar-view-panel">';
    html += '<div style="text-align:center; font-weight:900; font-size:1.15rem; margin-bottom:12px; color:var(--navy-dark);">📅 大直代表隊近期已確認出賽賽程行事曆</div>';
    html += '<div style="text-align:center; font-size:.76rem; color:#64748b; margin:-4px 0 12px;">直接讀取目前賽程資料；同一天有多場比賽會全部列出</div>';
    html += '<div class="calendar-matrix">';
    weekdays.forEach(w => html += '<div class="cal-day-col" style="background:#0f2942; color:white; min-height:auto; text-align:center; font-weight:800; padding:8px;">' + w + '</div>');

    for (let d = new Date(gridStart); d <= gridEnd; d = addDays(d,1)) {
      const key = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
      const items = byDate[key] || [];
      html += '<div class="cal-day-col"><span class="cal-num-badge">' + fmtMD(d) + '</span>';
      items.forEach(s => {
        const style = sportStyle(s.sport);
        const time = String(s.match_time || '').trim();
        const division = String(s.division || '').trim();
        const opp = String(s.opponents_draw || '').trim();
        const title = [time, division, opp, s.venue].filter(Boolean).join('｜');
        html += '<div class="cal-match-pill" style="border-left-color:' + style.color + '; color:' + style.text + '; background:' + style.bg + '; white-space:normal; line-height:1.28; margin-top:5px;" title="' + escHtml(title) + '">' +
          '<strong>' + escHtml(time) + '</strong> ' + style.icon + ' ' + escHtml(division || s.sport || '賽程') +
          (opp ? '<div style="font-size:.68rem; margin-top:2px;">' + escHtml(opp) + '</div>' : '') +
          '</div>';
      });
      html += '</div>';
    }
    html += '</div></div>';
    container.innerHTML = html;
  };
})();
</script>`;

  html = html.replace('</body>', dynamicCalendarScript + '\n</body>');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.status(200).send(html);
};
