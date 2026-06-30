import { describe, it, expect } from "vitest";
import { deduplicateLeads } from "@/lib/leadDedup";
import * as fc from "fast-check";

describe("deduplicateLeads", () => {
  it("returns empty array for empty input", () => {
    expect(deduplicateLeads([])).toEqual([]);
  });

  it("keeps single lead with non-null email", () => {
    const leads = [{ id: "1", email: "a@example.com", created_at: "2024-01-01" }];
    expect(deduplicateLeads(leads)).toHaveLength(1);
  });

  it("collapses duplicate non-null emails to one row", () => {
    const leads = [
      { id: "1", email: "a@example.com", created_at: "2024-01-01" },
      { id: "2", email: "a@example.com", created_at: "2024-01-02" },
    ];
    const result = deduplicateLeads(leads);
    expect(result.filter((l) => l.email === "a@example.com")).toHaveLength(1);
  });

  it("keeps most recent record for duplicate email", () => {
    const leads = [
      { id: "old", email: "dup@example.com", created_at: "2024-01-01" },
      { id: "new", email: "dup@example.com", created_at: "2024-06-01" },
    ];
    const result = deduplicateLeads(leads);
    expect(result[0].id).toBe("new");
  });

  it("always retains null-email leads as distinct rows", () => {
    const leads = [
      { id: "a", email: null, created_at: "2024-01-01" },
      { id: "b", email: null, created_at: "2024-01-02" },
    ];
    const result = deduplicateLeads(leads);
    expect(result).toHaveLength(2);
  });

  it("handles mixed null and non-null emails", () => {
    const leads = [
      { id: "1", email: "a@b.com", created_at: "2024-01-01" },
      { id: "2", email: null, created_at: "2024-01-01" },
      { id: "3", email: null, created_at: "2024-01-02" },
      { id: "4", email: "a@b.com", created_at: "2024-01-03" },
    ];
    const result = deduplicateLeads(leads);
    // 1 unique email + 2 null-email leads
    expect(result).toHaveLength(3);
  });

  // Property test: dedup invariants
  it("property: unique non-null emails → exactly one row each; null emails all retained", () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.uuid(),
            email: fc.option(fc.emailAddress(), { nil: null }),
            created_at: fc.date().map((d) => d.toISOString()),
          }),
          { maxLength: 30 },
        ),
        (leads) => {
          const result = deduplicateLeads(leads);
          const nullCount = leads.filter((l) => l.email == null).length;
          const uniqueEmails = new Set(leads.filter((l) => l.email != null).map((l) => l.email));

          // All null-email leads present
          const resultNullCount = result.filter((l) => l.email == null).length;
          expect(resultNullCount).toBe(nullCount);

          // Each unique non-null email appears exactly once
          for (const email of uniqueEmails) {
            const count = result.filter((l) => l.email === email).length;
            expect(count).toBe(1);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
