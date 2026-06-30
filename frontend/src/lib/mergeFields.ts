/**
 * Merge-field template interpolation.
 *
 * Substitutes {{first_name}}, {{last_name}}, {{company}}, {{website}}
 * from a prospect dictionary.  Null or missing fields become empty strings.
 * All other {{token}} patterns are also replaced with empty strings to ensure
 * no raw merge tokens appear in the rendered output.
 */

export interface ProspectFields {
  first_name?: string | null;
  last_name?: string | null;
  company?: string | null;
  website?: string | null;
  [key: string]: string | null | undefined;
}

const MERGE_FIELD_RE = /\{\{([a-z_]+)\}\}/g;

/**
 * Render a template string by substituting merge fields from a prospect.
 *
 * @param template - Template string containing optional {{field}} tokens.
 * @param prospect - Record with field values (null/undefined → empty string).
 * @returns The rendered string with all {{token}} patterns replaced.
 */
export function renderTemplate(template: string, prospect: ProspectFields): string {
  return template.replace(MERGE_FIELD_RE, (_match, field: string) => {
    const value = prospect[field];
    return value != null ? String(value) : "";
  });
}
