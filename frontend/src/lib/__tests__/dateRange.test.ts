import { describe, it, expect } from "vitest";
import { filterByDateRange, buildDailyPoints } from "@/lib/dateRange";
import * as fc from "fast-check";

describe("filterByDateRange", () => {
  const data = [
    { date: "2024-01-01", value: 1 },
    { date: "2024-01-10", value: 2 },
    { date: "2024-01-20", value: 3 },
    { date: "2024-02-01", value: 4 },
  ];

  it("returns all records within inclusive range", () => {
    const result = filterByDateRange(data, new Date("2024-01-01"), new Date("2024-01-20"));
    expect(result).toHaveLength(3);
  });

  it("returns empty array for empty input", () => {
    expect(filterByDateRange([], new Date("2024-01-01"), new Date("2024-12-31"))).toEqual([]);
  });

  it("excludes records outside range", () => {
    const result = filterByDateRange(data, new Date("2024-01-05"), new Date("2024-01-15"));
    expect(result).toHaveLength(1);
    expect(result[0].value).toBe(2);
  });
  it("falls back to created_at when date is missing", () => {
    const data = [
      { created_at: "2024-01-10T10:00:00Z", value: 5 },
    ];
    const result = filterByDateRange(data, new Date("2024-01-09"), new Date("2024-01-11"));
    expect(result).toHaveLength(1);
  });

  it("returns false for items with no date field", () => {
    const data = [{ value: 1 }];
    const result = filterByDateRange(data, new Date("2024-01-01"), new Date("2024-12-31"));
    expect(result).toHaveLength(0);
  });
});

describe("buildDailyPoints", () => {
  it("returns one point per calendar day in range", () => {
    const start = new Date("2024-01-01");
    const end = new Date("2024-01-07");
    const result = buildDailyPoints([], start, end);
    expect(result).toHaveLength(7);
  });

  it("fills missing days with zero", () => {
    const start = new Date("2024-01-01");
    const end = new Date("2024-01-03");
    const result = buildDailyPoints([], start, end);
    expect(result.every((p) => p.value === 0)).toBe(true);
  });

  it("sums values per day", () => {
    const data = [
      { date: "2024-01-02", value: 5 },
      { date: "2024-01-02", value: 3 },
    ];
    const result = buildDailyPoints(data, new Date("2024-01-01"), new Date("2024-01-03"));
    const day2 = result.find((p) => p.date === "2024-01-02");
    expect(day2?.value).toBe(8);
  });

  it("sorts output ascending by date", () => {
    const data = [
      { date: "2024-01-03", value: 1 },
      { date: "2024-01-01", value: 2 },
    ];
    const result = buildDailyPoints(data, new Date("2024-01-01"), new Date("2024-01-03"));
    expect(result[0].date).toBe("2024-01-01");
    expect(result[2].date).toBe("2024-01-03");
  });

  it("uses created_at as fallback key in buildDailyPoints", () => {
    const data = [{ created_at: "2024-01-02T00:00:00Z", value: 7 }];
    const result = buildDailyPoints(data, new Date("2024-01-01"), new Date("2024-01-03"), "value");
    const day2 = result.find((p) => p.date === "2024-01-02");
    expect(day2?.value).toBe(7);
  });

  it("skips items without any date in buildDailyPoints", () => {
    const data = [{ value: 3 }]; // no date, no created_at
    const result = buildDailyPoints(data, new Date("2024-01-01"), new Date("2024-01-03"), "value");
    // All days should be 0
    expect(result.every((p) => p.value === 0)).toBe(true);
  });

  it("skips items outside the date range in buildDailyPoints", () => {
    const data = [
      { date: "2023-01-01", value: 99 }, // outside range
      { date: "2024-01-02", value: 5 },
    ];
    const result = buildDailyPoints(data, new Date("2024-01-01"), new Date("2024-01-03"), "value");
    const day1 = result.find((p) => p.date === "2024-01-01");
    expect(day1?.value).toBe(0);
    const day2 = result.find((p) => p.date === "2024-01-02");
    expect(day2?.value).toBe(5);
  });

  // Property test: CSV export rows match date-filtered data
  it("property: filtered data length is subset of total", () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            date: fc
              .date({ min: new Date("2024-01-01"), max: new Date("2024-12-31") })
              .map((d) => d.toISOString().slice(0, 10)),
            value: fc.integer({ min: 0, max: 100 }),
          }),
          { maxLength: 50 },
        ),
        (data) => {
          const start = new Date("2024-06-01");
          const end = new Date("2024-06-30");
          const filtered = filterByDateRange(data, start, end);
          expect(filtered.length).toBeLessThanOrEqual(data.length);
        },
      ),
      { numRuns: 100 },
    );
  });
});
