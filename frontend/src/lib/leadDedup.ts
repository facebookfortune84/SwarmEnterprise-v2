/**
 * Lead deduplication utility (display-only).
 *
 * For display purposes, collapses leads sharing a non-null email
 * to a single row (the most recently created record wins).
 * Leads with email = null are always retained as distinct rows.
 */

export interface LeadRecord {
  id: string;
  email?: string | null;
  created_at?: string;
  [key: string]: unknown;
}

/**
 * Deduplicate a list of leads for display.
 *
 * - Non-null emails → keep the most recently created record per unique email.
 * - Null-email leads → all retained as distinct rows.
 *
 * @param leads - Flat array of lead records.
 * @returns Deduplicated array maintaining original relative order.
 */
export function deduplicateLeads<T extends LeadRecord>(leads: T[]): T[] {
  const seenEmails = new Map<string, T>();
  const nullEmailLeads: T[] = [];

  for (const lead of leads) {
    if (lead.email == null || lead.email === "") {
      nullEmailLeads.push(lead);
    } else {
      const existing = seenEmails.get(lead.email);
      if (!existing) {
        seenEmails.set(lead.email, lead);
      } else {
        // Keep the more recently created record
        const existingDate = existing.created_at ? new Date(existing.created_at).getTime() : 0;
        const newDate = lead.created_at ? new Date(lead.created_at).getTime() : 0;
        if (newDate > existingDate) {
          seenEmails.set(lead.email, lead);
        }
      }
    }
  }

  return [...seenEmails.values(), ...nullEmailLeads];
}
