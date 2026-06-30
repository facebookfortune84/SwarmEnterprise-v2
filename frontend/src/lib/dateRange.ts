/**
 * Date range utilities for the Analytics page.
 */

export interface Dated {
  date?: string;
  created_at?: string;
  [key: string]: unknown;
}

/**
 * Filter an array of dated records to only those within [start, end] (inclusive).
 * Uses the `date` field if present, otherwise `created_at`.
 */
export function filterByDateRange<T extends Dated>(data: T[], start: Date, end: Date): T[] {
  return data.filter((item) => {
    const rawDate = item.date ?? item.created_at;
    if (!rawDate) return false;
    const d = new Date(rawDate as string);
    return d >= start && d <= end;
  });
}

/**
 * Build an array of daily data points within [start, end].
 * Each point contains the ISO date string and the summed numeric value.
 *
 * @param data - Array of dated records with a `value` numeric property (or custom valueKey).
 * @param start - Start of date range.
 * @param end - End of date range.
 * @param valueKey - Key to sum for each day (default "value").
 */
export function buildDailyPoints(
  data: Dated[],
  start: Date,
  end: Date,
  valueKey = "value",
): { date: string; value: number }[] {
  const byDate: Map<string, number> = new Map();

  // Pre-populate all days in the range with 0
  const cursor = new Date(start);
  cursor.setUTCHours(0, 0, 0, 0);
  const endNorm = new Date(end);
  endNorm.setUTCHours(23, 59, 59, 999);

  while (cursor <= endNorm) {
    byDate.set(cursor.toISOString().slice(0, 10), 0);
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }

  // Accumulate values
  for (const item of data) {
    const rawDate = item.date ?? item.created_at;
    if (!rawDate) continue;
    const d = new Date(rawDate as string);
    if (d < start || d > endNorm) continue;
    const key = d.toISOString().slice(0, 10);
    const val = Number(item[valueKey] ?? 0);
    byDate.set(key, (byDate.get(key) ?? 0) + val);
  }

  return Array.from(byDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, value]) => ({ date, value }));
}
