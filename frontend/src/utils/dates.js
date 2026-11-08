// Calendar days as ISO strings ("2026-10-23"), always in UTC: pass dates are UTC days.

export const DAY_MS = 86400000;

const dayFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const shortFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

export const toDate = iso => new Date(iso + "T00:00:00Z");
export const toIso = date => date.toISOString().slice(0, 10);
export const dayMs = iso => toDate(iso).getTime();
export const addDays = (iso, n) => toIso(new Date(dayMs(iso) + n * DAY_MS));
export const daysBetween = (a, b) => Math.round((dayMs(b) - dayMs(a)) / DAY_MS);
export const todayIso = (now = new Date()) => toIso(now);

// True for a real calendar day written as YYYY-MM-DD (not "2026-02-30", not free text from the URL).
export function isIsoDay(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = toDate(value);
  return !Number.isNaN(date.getTime()) && toIso(date) === value;
}

export const fmtDay = iso => dayFmt.format(toDate(iso));      // 23 Oct 2026
export const fmtShort = iso => shortFmt.format(toDate(iso));  // 23 Oct
