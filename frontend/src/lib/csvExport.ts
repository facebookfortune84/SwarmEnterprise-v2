/**
 * CSV export utility — no server call required.
 *
 * Generates and immediately triggers a download of a CSV file
 * whose rows contain the data currently in scope.
 */

/**
 * Export an array of records as a CSV file.
 *
 * @param rows - Array of objects whose keys become CSV headers.
 * @param filename - Output filename (e.g. "analytics_export_2024-01-01.csv").
 */
export function exportCsv(rows: Record<string, unknown>[], filename?: string): void {
  if (rows.length === 0) {
    return;
  }

  const today = new Date().toISOString().slice(0, 10);
  const csvFilename = filename ?? `analytics_export_${today}.csv`;

  // Derive headers from the first row's keys
  const headers = Object.keys(rows[0]);
  const lines: string[] = [headers.map(escapeCsvCell).join(",")];

  for (const row of rows) {
    const cells = headers.map((h) => escapeCsvCell(String(row[h] ?? "")));
    lines.push(cells.join(","));
  }

  const csvContent = lines.join("\r\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", csvFilename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function escapeCsvCell(value: string): string {
  // Wrap in quotes if value contains comma, double-quote, or newline
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}
