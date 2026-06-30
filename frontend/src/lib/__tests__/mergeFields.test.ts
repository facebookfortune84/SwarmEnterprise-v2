import { describe, it, expect } from "vitest";
import { renderTemplate } from "@/lib/mergeFields";
import * as fc from "fast-check";

describe("renderTemplate", () => {
  it("substitutes first_name", () => {
    expect(renderTemplate("Hello {{first_name}}", { first_name: "Alice" })).toBe("Hello Alice");
  });

  it("substitutes all supported fields", () => {
    const result = renderTemplate("{{first_name}} {{last_name}} at {{company}} ({{website}})", {
      first_name: "Alice",
      last_name: "Smith",
      company: "Acme",
      website: "https://acme.com",
    });
    expect(result).toBe("Alice Smith at Acme (https://acme.com)");
  });

  it("replaces null field with empty string", () => {
    const result = renderTemplate("Hi {{first_name}}", { first_name: null });
    expect(result).toBe("Hi ");
    expect(result).not.toContain("{{");
  });

  it("replaces undefined field with empty string", () => {
    const result = renderTemplate("Hi {{first_name}}", {});
    expect(result).toBe("Hi ");
  });

  it("replaces unknown token with empty string", () => {
    const result = renderTemplate("Hi {{unknown_field}}", {});
    expect(result).toBe("Hi ");
    expect(result).not.toContain("{{");
  });

  it("leaves text without tokens unchanged", () => {
    expect(renderTemplate("No tokens here.", {})).toBe("No tokens here.");
  });

  // Property test: no raw tokens survive
  it("property: no raw {{token}} survives", () => {
    fc.assert(
      fc.property(
        fc.string({ maxLength: 200 }),
        fc.record({
          first_name: fc.option(fc.string({ maxLength: 50 })),
          last_name: fc.option(fc.string({ maxLength: 50 })),
          company: fc.option(fc.string({ maxLength: 100 })),
          website: fc.option(fc.string({ maxLength: 100 })),
        }),
        (template, prospect) => {
          const result = renderTemplate(template, prospect as Record<string, string | null>);
          expect(/\{\{[a-z_]+\}\}/.test(result)).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });
});
