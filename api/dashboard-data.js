// Same-origin read-only endpoint for the public sports dashboard.
// Uses the same publishable key and row-level security as the browser client.
// Does not expose service-role credentials or mutate the database.
const SUPABASE_URL = "https://hdxrublbpaptthmflnrn.supabase.co";
const PUBLISHABLE_KEY = "sb_publishable_n3ONLlgwYQ0TAOcxkKoNhg_ZwL6M9wP";

async function fetchRows(table) {
  const result = [];
  const pageSize = 1000;
  for (let offset = 0; offset < 100000; offset += pageSize) {
    const url = SUPABASE_URL + '/rest/v1/' + table +
      '?select=*&order=id.asc&offset=' + offset + '&limit=' + pageSize;
    const res = await fetch(url, {
      headers: {
        apikey: PUBLISHABLE_KEY,
        Authorization: 'Bearer ' + PUBLISHABLE_KEY,
        Accept: 'application/json'
      },
      signal: AbortSignal.timeout(12000),
      cache: 'no-store'
    });
    if (!res.ok) {
      throw new Error(table + ' public read failed with HTTP ' + res.status);
    }
    const page = await res.json();
    if (!Array.isArray(page)) throw new Error('Unexpected response type from ' + table);
    result.push(...page);
    if (page.length < pageSize) break;
  }
  return result;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  if (req.method !== 'GET') return res.status(405).json({error:'Method not allowed'});
  try {
    const [tournaments, schedules] = await Promise.all([
      fetchRows('tournaments'),
      fetchRows('schedules')
    ]);
    return res.status(200).json({
      tournaments, schedules, fetched_at: new Date().toISOString(),
      counts: { tournaments: tournaments.length, schedules: schedules.length }
    });
  } catch (error) {
    console.error('Sports dashboard public data read failure:', error.message);
    return res.status(503).json({error:'Unable to fetch current sports schedules'});
  }
};
