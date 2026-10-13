import handler from './line-sports-push.js';

export default async function manualPush(req, res) {
  req.headers.authorization = `Bearer ${process.env.CRON_SECRET || ''}`;
  return handler(req, res);
}
