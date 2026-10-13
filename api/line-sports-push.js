/**
 * 大直高中運動賽事 LINE 晨報 v1.2
 * 每天台北時間 07:00 由 Vercel Cron 自動呼叫。
 *
 * 資料規則：
 * - 只收錄「確定日期 + 確定時間」的賽程。
 * - 日期區間（如 10/18～10/25、10/18-10/25）排除。
 * - 待公告 / 待抽籤 / 待排定 / 待確認等排除。
 * - 一個「賽事名稱 + 分組」一張小卡。
 * - 同分組多場賽程整併在同一卡片。
 * - 晨報預設彙整「今天起 7 天內」的已確認賽程。
 * - 若 7 天內沒有確定賽程，仍推播一則「未來 7 天無已確認賽程」。
 *
 * Vercel Environment Variables:
 *   SUPABASE_URL
 *   SUPABASE_KEY
 *   LINE_CHANNEL_ACCESS_TOKEN
 *   LINE_TARGET_ID
 *   CRON_SECRET
 *   DASHBOARD_URL (optional)
 */

const DEFAULT_DASHBOARD_URL = 'https://dazhi-sports-hub.vercel.app/';
const TZ_OFFSET_MS = 8 * 60 * 60 * 1000;
const LOOKAHEAD_DAYS = 7;

function text(v) {
  return String(v ?? '').trim();
}

function isRangeDate(value) {
  const s = text(value);
  if (!s) return true;
  if (/[～~至]/.test(s)) return true;
  return /\d{1,4}[\/.-]\d{1,2}(?:[\/.-]\d{1,2})?\s*[-–—]\s*\d{1,4}[\/.-]\d{1,2}/.test(s);
}

function isPlaceholderTime(value) {
  const s = text(value);
  if (!s) return true;
  return [
    '待公告','待大會','待抽籤','待排定','待確認','未定',
    '另行公告','依大會公告','依承辦校公告'
  ].some(x => s.includes(x));
}

function extractDateOnly(value) {
  return text(value).split(/\s+/)[0] || '';
}

function extractEmbeddedTime(value) {
  const m = text(value).match(/\b([01]?\d|2[0-3]):([0-5]\d)\b/);
  return m ? `${m[1].padStart(2, '0')}:${m[2]}` : '';
}

function normalizeTime(row) {
  const explicit = text(row.match_time);
  if (explicit && !isPlaceholderTime(explicit)) {
    const m = explicit.match(/\b([01]?\d|2[0-3]):([0-5]\d)\b/);
    if (m) return `${m[1].padStart(2, '0')}:${m[2]}`;
  }
  return extractEmbeddedTime(row.match_date);
}

function rocToAdYear(y) {
  const n = Number(y);
  return n < 1911 ? n + 1911 : n;
}

function parseScheduleDate(value) {
  const date = extractDateOnly(value);
  let m;

  m = date.match(/^(\d{2,4})\/(\d{1,2})\/(\d{1,2})$/);
  if (m) {
    return new Date(Date.UTC(rocToAdYear(m[1]), Number(m[2]) - 1, Number(m[3])));
  }

  m = date.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) {
    return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  }

  m = date.match(/^(\d{1,2})\/(\d{1,2})$/);
  if (m) {
    const now = taipeiNow();
    return new Date(Date.UTC(now.getUTCFullYear(), Number(m[1]) - 1, Number(m[2])));
  }

  return null;
}

function taipeiNow() {
  return new Date(Date.now() + TZ_OFFSET_MS);
}

function startOfTaipeiTodayUTC() {
  const now = taipeiNow();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

function inMorningWindow(row) {
  const d = parseScheduleDate(row.match_date);
  if (!d) return false;

  const start = startOfTaipeiTodayUTC();
  const end = new Date(start.getTime() + LOOKAHEAD_DAYS * 86400000);

  return d >= start && d < end;
}

function hasConfirmedDateTime(row) {
  const date = extractDateOnly(row.match_date);
  const time = normalizeTime(row);

  if (!date || isRangeDate(row.match_date)) return false;
  if (!time || isPlaceholderTime(time)) return false;

  const validDate =
    /^\d{2,4}\/\d{1,2}\/\d{1,2}$/.test(date) ||
    /^\d{1,2}\/\d{1,2}$/.test(date) ||
    /^\d{4}-\d{1,2}-\d{1,2}$/.test(date);

  return validDate && /^([01]?\d|2[0-3]):[0-5]\d$/.test(time);
}

function cleanDivision(v) {
  return text(v).replace(/\s+/g, ' ').replace(/組組/g, '組') || '未標示分組';
}

function sportEmoji(sport) {
  const s = text(sport);
  if (s.includes('籃球')) return '🏀';
  if (s.includes('排球')) return '🏐';
  if (s.includes('羽球')) return '🏸';
  if (s.includes('網球')) return '🎾';
  if (s.includes('棒球')) return '⚾';
  if (s.includes('足球')) return '⚽';
  if (s.includes('擊劍')) return '🤺';
  if (s.includes('空手道')) return '🥋';
  if (s.includes('高爾夫')) return '⛳';
  return '🏅';
}

function displayDate(v) {
  return extractDateOnly(v).replace(/^115\//, '');
}

function groupMorningSchedules(rows) {
  const groups = new Map();

  rows
    .filter(hasConfirmedDateTime)
    .filter(inMorningWindow)
    .forEach(row => {
      const tournament = text(row.tournament_name) || '運動賽事';
      const division = cleanDivision(row.division);
      const key = `${tournament}|||${division}`;

      if (!groups.has(key)) {
        groups.set(key, {
          tournament_name: tournament,
          division,
          sport: text(row.sport),
          matches: [],
        });
      }

      groups.get(key).matches.push({
        date: extractDateOnly(row.match_date),
        time: normalizeTime(row),
        matchup: text(row.opponents_draw) || '對戰待確認',
        venue: text(row.venue) || '地點待確認',
      });
    });

  for (const g of groups.values()) {
    g.matches.sort((a,b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`, 'zh-Hant'));
  }

  return [...groups.values()].sort((a,b) => {
    const aa = a.matches[0] ? `${a.matches[0].date} ${a.matches[0].time}` : '';
    const bb = b.matches[0] ? `${b.matches[0].date} ${b.matches[0].time}` : '';
    return aa.localeCompare(bb, 'zh-Hant');
  });
}

function t(textValue, size='sm', color='#475569', weight='regular') {
  return { type:'text', text:String(textValue), size, color, weight, wrap:true };
}

function matchBlock(m, last) {
  const items = [
    { type:'box', layout:'baseline', spacing:'sm', contents:[
      t('📅','sm','#64748B'), t(`${displayDate(m.date)}  ${m.time}`,'md','#334155','bold')
    ]},
    { type:'box', layout:'baseline', spacing:'sm', contents:[
      t('👥','sm','#64748B'), t(m.matchup,'sm','#334155','bold')
    ]},
    { type:'box', layout:'baseline', spacing:'sm', contents:[
      t('📍','sm','#64748B'), t(m.venue,'sm','#64748B')
    ]}
  ];
  if (!last) items.push({type:'separator', margin:'md', color:'#E2E8F0'});
  return {type:'box', layout:'vertical', spacing:'xs', margin:'md', contents:items};
}

function groupBubble(g, dashboardUrl) {
  return {
    type:'bubble',
    size:'mega',
    body:{
      type:'box', layout:'vertical', spacing:'sm', paddingAll:'18px',
      contents:[
        {type:'box', layout:'baseline', spacing:'sm', contents:[
          t(sportEmoji(g.sport),'xl','#0F172A'),
          t(g.tournament_name,'lg','#0F172A','bold')
        ]},
        {type:'box', layout:'horizontal', margin:'sm', contents:[
          {type:'text', text:g.division, size:'sm', weight:'bold', color:'#1D4ED8', flex:0}
        ]},
        ...g.matches.map((m,i)=>matchBlock(m, i===g.matches.length-1))
      ]
    },
    footer:{
      type:'box', layout:'vertical', paddingAll:'12px',
      contents:[{
        type:'button', style:'primary', color:'#2563EB', height:'sm',
        action:{type:'uri', label:'查看完整面板', uri:dashboardUrl}
      }]
    }
  };
}

function morningMessages(groups, dashboardUrl) {
  if (!groups.length) {
    return [{
      type:'text',
      text:'☀️ 大直高中運動賽事晨報\n未來 7 天目前沒有「已確認日期＋時間」的比賽。\n區間日期與待公告賽程不列入晨報。'
    }];
  }

  const chunks = [];
  for (let i=0; i<groups.length; i+=12) chunks.push(groups.slice(i,i+12));

  return chunks.map((chunk, idx)=>( {
    type:'flex',
    altText: chunks.length===1
      ? `大直高中晨報｜未來7天 ${chunk.length} 個分組`
      : `大直高中晨報 ${idx+1}/${chunks.length}`,
    contents:{ type:'carousel', contents:chunk.map(g=>groupBubble(g,dashboardUrl)) }
  }));
}

async function fetchSchedules() {
  const url = (process.env.SUPABASE_URL || '').replace(/\/$/,'');
  const key = process.env.SUPABASE_KEY || '';
  if (!url || !key) throw new Error('缺少 SUPABASE_URL 或 SUPABASE_KEY');

  const r = await fetch(
    `${url}/rest/v1/schedules?select=id,sport,division,tournament_name,match_date,match_time,venue,opponents_draw,status&order=match_date.asc`,
    { headers:{ apikey:key, Authorization:`Bearer ${key}` } }
  );
  if (!r.ok) throw new Error(`Supabase ${r.status}: ${await r.text()}`);
  return await r.json();
}

async function pushLine(messages) {
  const token = process.env.LINE_CHANNEL_ACCESS_TOKEN || '';
  const target = process.env.LINE_TARGET_ID || '';
  if (!token || !target) throw new Error('缺少 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_TARGET_ID');

  for (let i=0; i<messages.length; i+=5) {
    const r = await fetch('https://api.line.me/v2/bot/message/push', {
      method:'POST',
      headers:{ Authorization:`Bearer ${token}`, 'Content-Type':'application/json' },
      body:JSON.stringify({to:target, messages:messages.slice(i,i+5)})
    });
    if (!r.ok) throw new Error(`LINE ${r.status}: ${await r.text()}`);
  }
}

export default async function handler(req, res) {
  try {
    const secret = process.env.CRON_SECRET || '';
    if (secret && req.headers.authorization !== `Bearer ${secret}`) {
      return res.status(401).json({ok:false, error:'Unauthorized'});
    }

    const rows = await fetchSchedules();
    const groups = groupMorningSchedules(rows);
    const dashboardUrl = process.env.DASHBOARD_URL || DEFAULT_DASHBOARD_URL;
    const messages = morningMessages(groups, dashboardUrl);

    await pushLine(messages);

    return res.status(200).json({
      ok:true,
      pushed:true,
      windowDays:LOOKAHEAD_DAYS,
      confirmedGroups:groups.length,
      lineMessages:messages.length
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ok:false, error:err?.message || String(err)});
  }
}
