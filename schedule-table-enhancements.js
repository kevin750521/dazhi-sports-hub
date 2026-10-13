(() => {
  const RANGE_RE = /[～~至]|\d{1,4}[\/.\-]\d{1,2}(?:[\/.\-]\d{1,2})?\s*[-–—]\s*\d{1,4}[\/.\-]\d{1,2}/;

  function normalize(s) {
    return (s || '').replace(/\s+/g, ' ').trim();
  }

  function parseRocDate(value) {
    const s = normalize(value).split(/\s+/)[0];
    let m = s.match(/^(\d{2,4})\/(\d{1,2})\/(\d{1,2})$/);
    if (m) {
      let y = Number(m[1]);
      if (y < 1911) y += 1911;
      return Date.UTC(y, Number(m[2]) - 1, Number(m[3]));
    }
    m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (m) return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return Number.POSITIVE_INFINITY;
  }

  function isScheduleTable(table) {
    const headers = [...table.querySelectorAll('thead th')].map(th => normalize(th.textContent));
    return headers.includes('運動種類') &&
      headers.includes('賽事名稱') &&
      headers.some(h => h.includes('大直出賽組別')) &&
      headers.includes('比賽日期') &&
      headers.some(h => h.includes('來源檔案'));
  }

  function removeRedundantRangeRows(table) {
    const rows = [...table.querySelectorAll('tbody tr')];
    if (!rows.length) return;

    const exactKeys = new Set();
    for (const row of rows) {
      const cells = row.cells;
      if (cells.length < 4) continue;
      const key = [normalize(cells[0]?.textContent), normalize(cells[1]?.textContent), normalize(cells[2]?.textContent)].join('|||');
      const dateText = normalize(cells[3]?.textContent);
      if (dateText && !RANGE_RE.test(dateText)) exactKeys.add(key);
    }

    for (const row of rows) {
      const cells = row.cells;
      if (cells.length < 4) continue;
      const key = [normalize(cells[0]?.textContent), normalize(cells[1]?.textContent), normalize(cells[2]?.textContent)].join('|||');
      const dateText = normalize(cells[3]?.textContent);
      if (RANGE_RE.test(dateText) && exactKeys.has(key)) {
        row.remove();
      }
    }
  }

  function addFilters(table) {
    const thead = table.tHead;
    if (!thead || thead.querySelector('.schedule-filter-row')) return;
    const headerRow = thead.rows[0];
    const filterRow = document.createElement('tr');
    filterRow.className = 'schedule-filter-row';

    [...headerRow.cells].forEach((th, index) => {
      const cell = document.createElement('th');
      const input = document.createElement('input');
      input.type = 'search';
      input.placeholder = '篩選';
      input.setAttribute('aria-label', `篩選 ${normalize(th.textContent)}`);
      input.style.cssText = 'width:100%;min-width:72px;padding:5px 7px;border:1px solid #cbd5e1;border-radius:6px;font-size:.75rem;background:#fff;color:#334155;';
      input.addEventListener('input', () => applyFilters(table));
      cell.appendChild(input);
      filterRow.appendChild(cell);
    });
    thead.appendChild(filterRow);
  }

  function applyFilters(table) {
    const inputs = [...table.querySelectorAll('.schedule-filter-row input')];
    [...table.querySelectorAll('tbody tr')].forEach(row => {
      const visible = inputs.every((input, idx) => {
        const q = normalize(input.value).toLowerCase();
        if (!q) return true;
        return normalize(row.cells[idx]?.textContent).toLowerCase().includes(q);
      });
      row.style.display = visible ? '' : 'none';
    });
  }

  function addSort(table) {
    const headerRow = table.tHead?.rows?.[0];
    if (!headerRow || headerRow.dataset.sortReady === '1') return;
    headerRow.dataset.sortReady = '1';

    [...headerRow.cells].forEach((th, index) => {
      th.style.cursor = 'pointer';
      th.title = '點擊排序';
      const label = normalize(th.textContent);
      th.dataset.baseLabel = label;
      th.addEventListener('click', () => {
        const current = th.dataset.sortDir === 'asc' ? 'desc' : 'asc';
        [...headerRow.cells].forEach(x => {
          x.dataset.sortDir = '';
          if (x.dataset.baseLabel) x.textContent = x.dataset.baseLabel;
        });
        th.dataset.sortDir = current;
        th.textContent = `${th.dataset.baseLabel} ${current === 'asc' ? '▲' : '▼'}`;

        const body = table.tBodies[0];
        const rows = [...body.rows];
        rows.sort((a, b) => {
          const av = normalize(a.cells[index]?.textContent);
          const bv = normalize(b.cells[index]?.textContent);
          let cmp;
          if (th.dataset.baseLabel === '比賽日期') {
            const ad = parseRocDate(av);
            const bd = parseRocDate(bv);
            cmp = ad === bd ? av.localeCompare(bv, 'zh-Hant', { numeric: true }) : ad - bd;
          } else {
            cmp = av.localeCompare(bv, 'zh-Hant', { numeric: true });
          }
          return current === 'asc' ? cmp : -cmp;
        });
        rows.forEach(r => body.appendChild(r));
      });
    });
  }

  function enhance() {
    document.querySelectorAll('table').forEach(table => {
      if (!isScheduleTable(table)) return;
      removeRedundantRangeRows(table);
      addFilters(table);
      addSort(table);
    });
  }

  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      enhance();
    });
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhance, { once: true });
  } else {
    enhance();
  }
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
