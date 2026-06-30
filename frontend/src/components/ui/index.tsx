import React from "react";

// ── Button ────────────────────────────────────────────────────────────────────

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-500 focus-visible:ring-brand-500 disabled:bg-neutral-700 disabled:text-neutral-400",
  secondary:
    "bg-neutral-700 text-white hover:bg-neutral-600 focus-visible:ring-neutral-500 disabled:bg-neutral-800 disabled:text-neutral-500",
  ghost:
    "bg-transparent text-neutral-300 border border-neutral-700 hover:bg-neutral-800 hover:text-white focus-visible:ring-neutral-500 disabled:text-neutral-600",
  danger:
    "bg-danger-700 text-white hover:bg-danger-500 focus-visible:ring-danger-500 disabled:bg-neutral-700 disabled:text-neutral-400",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs rounded",
  md: "px-4 py-2 text-sm rounded-md",
  lg: "px-6 py-3 text-base rounded-lg",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={[
        "inline-flex items-center justify-center gap-2 font-semibold transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950",
        "cursor-pointer disabled:cursor-not-allowed",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(" ")}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
        />
      )}
      {children}
    </button>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────

export type BadgeVariant = "success" | "warning" | "danger" | "neutral" | "info";
export type BadgeSize = "sm" | "md";

export interface BadgeProps {
  variant?: BadgeVariant;
  /** Alias for variant — accepted for compatibility */
  color?: BadgeVariant;
  size?: BadgeSize;
  children: React.ReactNode;
  className?: string;
}

const badgeVariantClasses: Record<BadgeVariant, string> = {
  success: "bg-success-50 text-success-700 border border-success-500/30",
  warning: "bg-warning-50 text-warning-700 border border-warning-500/30",
  danger: "bg-danger-50 text-danger-700 border border-danger-500/30",
  neutral: "bg-neutral-800 text-neutral-300 border border-neutral-700",
  info: "bg-brand-950 text-brand-300 border border-brand-500/30",
};

const badgeSizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export function Badge({ variant, color, size = "sm", children, className = "" }: BadgeProps) {
  const resolvedVariant: BadgeVariant = variant ?? color ?? "neutral";
  return (
    <span
      className={[
        "inline-flex items-center font-semibold rounded-full uppercase tracking-wide",
        badgeVariantClasses[resolvedVariant],
        badgeSizeClasses[size],
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

export interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={["animate-pulse bg-neutral-800 rounded", className].join(" ")}
    />
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = "", id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-sm text-neutral-300 font-medium">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          {...props}
          className={[
            "bg-neutral-900 border rounded-md px-3 py-2 text-sm text-neutral-100",
            "placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            error ? "border-danger-500" : "border-neutral-700",
            className,
          ].join(" ")}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
        />
        {error && (
          <span id={`${inputId}-error`} className="text-xs text-danger-500" role="alert">
            {error}
          </span>
        )}
        {helperText && !error && (
          <span id={`${inputId}-helper`} className="text-xs text-neutral-500">
            {helperText}
          </span>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";

// ── Select ────────────────────────────────────────────────────────────────────

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  label?: string;
  error?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ options, label, error, className = "", id, ...props }, ref) => {
    const selectId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={selectId} className="text-sm text-neutral-300 font-medium">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          {...props}
          className={[
            "bg-neutral-900 border rounded-md px-3 py-2 text-sm text-neutral-100",
            "focus:outline-none focus:ring-2 focus:ring-brand-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            error ? "border-danger-500" : "border-neutral-700",
            className,
          ].join(" ")}
          aria-invalid={!!error}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <span className="text-xs text-danger-500" role="alert">
            {error}
          </span>
        )}
      </div>
    );
  },
);
Select.displayName = "Select";

// ── Textarea ──────────────────────────────────────────────────────────────────

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  showCharCount?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, showCharCount = false, className = "", id, maxLength, value, ...props }, ref) => {
    const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    const charCount = typeof value === "string" ? value.length : 0;
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={textareaId} className="text-sm text-neutral-300 font-medium">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          value={value}
          maxLength={maxLength}
          {...props}
          className={[
            "bg-neutral-900 border rounded-md px-3 py-2 text-sm text-neutral-100 resize-y",
            "placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            error ? "border-danger-500" : "border-neutral-700",
            className,
          ].join(" ")}
          aria-invalid={!!error}
        />
        <div className="flex justify-between">
          {error ? (
            <span className="text-xs text-danger-500" role="alert">
              {error}
            </span>
          ) : (
            <span />
          )}
          {showCharCount && maxLength && (
            <span className="text-xs text-neutral-500">
              {charCount}/{maxLength}
            </span>
          )}
        </div>
      </div>
    );
  },
);
Textarea.displayName = "Textarea";

// ── Modal ─────────────────────────────────────────────────────────────────────

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: string;
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidth = "max-w-lg",
}: ModalProps) {
  React.useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        className={["bg-neutral-900 border border-neutral-700 rounded-xl shadow-2xl w-full", maxWidth].join(" ")}
      >
        {title && (
          <div className="flex justify-between items-center px-6 py-4 border-b border-neutral-800">
            <h2 id="modal-title" className="text-lg font-semibold text-white">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-white text-2xl leading-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              aria-label="Close dialog"
            >
              &times;
            </button>
          </div>
        )}
        <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-neutral-800 flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────
// Re-exported helpers wrapping react-hot-toast for a consistent API

export { default as toast } from "react-hot-toast";

// ── DataTable ─────────────────────────────────────────────────────────────────

export interface ColumnDef<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  width?: string;
}

export interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  onSort?: (key: string, direction: "asc" | "desc") => void;
  emptyMessage?: string;
  footer?: React.ReactNode;
  /** Optional row key extractor; defaults to row index */
  keyExtractor?: (row: T) => string;
  /** Optional row click handler */
  onRowClick?: (row: T) => void;
  /** Optional pagination slot rendered below table */
  pagination?: React.ReactNode;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function DataTable<T = any>({
  columns,
  data,
  onSort,
  emptyMessage = "No data available.",
  footer,
  keyExtractor,
  onRowClick,
  pagination,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = React.useState<string | null>(null);
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("asc");

  const handleSort = (key: string) => {
    const newDir = sortKey === key && sortDir === "asc" ? "desc" : "asc";
    setSortKey(key);
    setSortDir(newDir);
    onSort?.(key, newDir);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left text-neutral-300">
        <thead className="text-xs text-neutral-500 uppercase border-b border-neutral-800">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                scope="col"
                style={col.width ? { width: col.width } : undefined}
                className={["px-4 py-3", col.sortable ? "cursor-pointer select-none hover:text-white" : ""].join(" ")}
                onClick={col.sortable ? () => handleSort(String(col.key)) : undefined}
                aria-sort={
                  sortKey === String(col.key)
                    ? sortDir === "asc"
                      ? "ascending"
                      : "descending"
                    : undefined
                }
              >
                {col.header}
                {col.sortable && sortKey === String(col.key) && (
                  <span aria-hidden="true" className="ml-1">
                    {sortDir === "asc" ? "↑" : "↓"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-neutral-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={keyExtractor ? keyExtractor(row) : i}
                className={["border-b border-neutral-800", onRowClick ? "cursor-pointer hover:bg-neutral-800/60" : "hover:bg-neutral-800/40"].join(" ")}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((col) => (
                  <td key={String(col.key)} className="px-4 py-3">
                    {col.render
                      ? col.render(row)
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      : String((row as any)[col.key as string] ?? "")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      {footer && <div className="px-4 py-3 border-t border-neutral-800">{footer}</div>}
      {pagination && <div className="px-4 py-3 border-t border-neutral-800 flex justify-between items-center">{pagination}</div>}
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

export interface Tab {
  key: string;
  label: string;
  content: React.ReactNode;
}

export interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (key: string) => void;
}

export function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div>
      <div role="tablist" className="flex gap-0 border-b border-neutral-800 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            aria-controls={`panel-${tab.key}`}
            id={`tab-${tab.key}`}
            onClick={() => onChange(tab.key)}
            className={[
              "px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors",
              activeTab === tab.key
                ? "border-brand-500 text-brand-400"
                : "border-transparent text-neutral-500 hover:text-neutral-300",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.key}
          role="tabpanel"
          id={`panel-${tab.key}`}
          aria-labelledby={`tab-${tab.key}`}
          hidden={activeTab !== tab.key}
          className="mt-4"
        >
          {activeTab === tab.key ? tab.content : null}
        </div>
      ))}
    </div>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────

export interface CardProps {
  header?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

export function Card({ header, children, footer, onClick, className = "" }: CardProps) {
  return (
    <div
      className={[
        "bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden",
        onClick ? "cursor-pointer hover:border-neutral-700 transition-colors" : "",
        className,
      ].join(" ")}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onClick();
            }
          : undefined
      }
    >
      {header && (
        <div className="px-5 py-4 border-b border-neutral-800 font-semibold text-white">
          {header}
        </div>
      )}
      <div className="px-5 py-4">{children}</div>
      {footer && (
        <div className="px-5 py-4 border-t border-neutral-800 text-sm text-neutral-400">
          {footer}
        </div>
      )}
    </div>
  );
}

// ── PageHeader ────────────────────────────────────────────────────────────────

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-neutral-400 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2 items-center">{actions}</div>}
    </div>
  );
}
