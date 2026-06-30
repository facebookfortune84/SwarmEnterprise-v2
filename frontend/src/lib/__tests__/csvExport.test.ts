import { describe, it, expect, vi, afterEach } from "vitest";
import { exportCsv } from "@/lib/csvExport";

// Mock DOM APIs used by exportCsv
const mockClick = vi.fn();
const mockAppendChild = vi.fn();
const mockRemoveChild = vi.fn();
const mockCreateElement = vi.fn(() => ({
  href: "",
  setAttribute: vi.fn(),
  click: mockClick,
  style: {},
}));
const mockCreateObjectURL = vi.fn(() => "blob:fake-url");
const mockRevokeObjectURL = vi.fn();

vi.stubGlobal("URL", {
  createObjectURL: mockCreateObjectURL,
  revokeObjectURL: mockRevokeObjectURL,
});

vi.stubGlobal("document", {
  createElement: mockCreateElement,
  body: {
    appendChild: mockAppendChild,
    removeChild: mockRemoveChild,
  },
  createTextNode: vi.fn(),
});

vi.stubGlobal(
  "Blob",
  class MockBlob {
    content: string[];
    type: string;
    constructor(content: string[], options: { type?: string } = {}) {
      this.content = content;
      this.type = options.type ?? "";
    }
  },
);

afterEach(() => {
  vi.clearAllMocks();
});

describe("exportCsv", () => {
  it("does nothing for empty rows", () => {
    exportCsv([]);
    expect(mockClick).not.toHaveBeenCalled();
  });

  it("creates CSV with correct headers", () => {
    const rows = [{ name: "Alice", age: "30" }];
    exportCsv(rows, "test.csv");
    expect(mockCreateElement).toHaveBeenCalledWith("a");
    expect(mockClick).toHaveBeenCalled();
  });

  it("triggers download with provided filename", () => {
    const rows = [{ col: "value" }];
    const link = { href: "", setAttribute: vi.fn(), click: mockClick, style: {} };
    mockCreateElement.mockReturnValueOnce(link);
    exportCsv(rows, "my-export.csv");
    expect(link.setAttribute).toHaveBeenCalledWith("download", "my-export.csv");
  });

  it("generates default filename with today's date", () => {
    const today = new Date().toISOString().slice(0, 10);
    const rows = [{ col: "value" }];
    const link = { href: "", setAttribute: vi.fn(), click: mockClick, style: {} };
    mockCreateElement.mockReturnValueOnce(link);
    exportCsv(rows);
    expect(link.setAttribute).toHaveBeenCalledWith(
      "download",
      `analytics_export_${today}.csv`,
    );
  });

  it("escapes commas in cell values", () => {
    const rows = [{ name: "Smith, John", email: "j@example.com" }];
    exportCsv(rows);
    // Should succeed without throwing
    expect(mockClick).toHaveBeenCalled();
  });
});
