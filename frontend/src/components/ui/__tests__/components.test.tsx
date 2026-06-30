import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  Button,
  Badge,
  Skeleton,
  Input,
  Select,
  Textarea,
  Modal,
  DataTable,
  Tabs,
  Card,
  PageHeader,
} from "@/components/ui/index";

// ── Button tests ──────────────────────────────────────────────────────────────

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeDefined();
  });

  it("calls onClick when clicked", () => {
    const handler = vi.fn();
    render(<Button onClick={handler}>Click</Button>);
    fireEvent.click(screen.getByText("Click"));
    expect(handler).toHaveBeenCalledOnce();
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByText("Disabled")).toBeDisabled();
  });

  it("is disabled when loading is true", () => {
    render(<Button loading>Loading</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("does not call onClick when disabled", () => {
    const handler = vi.fn();
    render(<Button disabled onClick={handler}>Disabled</Button>);
    fireEvent.click(screen.getByText("Disabled"));
    expect(handler).not.toHaveBeenCalled();
  });

  it("applies primary variant class by default", () => {
    render(<Button>Primary</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-brand-600");
  });

  it("applies danger variant class", () => {
    render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole("button").className).toContain("bg-danger-700");
  });

  it("applies ghost variant class", () => {
    render(<Button variant="ghost">Ghost</Button>);
    expect(screen.getByRole("button").className).toContain("bg-transparent");
  });

  it("applies sm size class", () => {
    render(<Button size="sm">Small</Button>);
    expect(screen.getByRole("button").className).toContain("text-xs");
  });

  it("applies lg size class", () => {
    render(<Button size="lg">Large</Button>);
    expect(screen.getByRole("button").className).toContain("text-base");
  });
});

// ── Badge tests ───────────────────────────────────────────────────────────────

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeDefined();
  });

  it("applies success variant", () => {
    render(<Badge variant="success">OK</Badge>);
    expect(screen.getByText("OK").className).toContain("text-success-700");
  });

  it("applies danger variant", () => {
    render(<Badge variant="danger">Error</Badge>);
    expect(screen.getByText("Error").className).toContain("text-danger-700");
  });

  it("applies warning variant", () => {
    render(<Badge variant="warning">Warn</Badge>);
    expect(screen.getByText("Warn").className).toContain("text-warning-700");
  });

  it("applies neutral variant by default", () => {
    render(<Badge>Neutral</Badge>);
    expect(screen.getByText("Neutral").className).toContain("bg-neutral-800");
  });

  it("applies info variant", () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByText("Info").className).toContain("bg-brand-950");
  });
});

// ── Skeleton tests ────────────────────────────────────────────────────────────

describe("Skeleton", () => {
  it("renders with animate-pulse class", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toBeDefined();
    expect((container.firstChild as Element).className).toContain("animate-pulse");
  });

  it("accepts and applies className", () => {
    const { container } = render(<Skeleton className="h-8 w-32" />);
    const el = container.firstChild as Element;
    expect(el.className).toContain("h-8");
    expect(el.className).toContain("w-32");
  });

  it("is aria-hidden", () => {
    const { container } = render(<Skeleton />);
    expect((container.firstChild as Element).getAttribute("aria-hidden")).toBe("true");
  });
});

// ── Input tests ───────────────────────────────────────────────────────────────

describe("Input", () => {
  it("renders label", () => {
    render(<Input label="Email" />);
    expect(screen.getByText("Email")).toBeDefined();
  });

  it("shows error message", () => {
    render(<Input label="Email" error="Required" />);
    expect(screen.getByText("Required")).toBeDefined();
  });

  it("has aria-invalid when error is set", () => {
    render(<Input label="Email" error="Required" />);
    const input = screen.getByRole("textbox");
    expect(input.getAttribute("aria-invalid")).toBe("true");
  });

  it("is disabled when disabled prop is set", () => {
    render(<Input label="Email" disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });

  it("shows helper text when no error", () => {
    render(<Input helperText="We never share your email" />);
    expect(screen.getByText("We never share your email")).toBeDefined();
  });
});

// ── Select tests ──────────────────────────────────────────────────────────────

describe("Select", () => {
  const opts = [
    { value: "a", label: "Option A" },
    { value: "b", label: "Option B" },
  ];

  it("renders all options", () => {
    render(<Select options={opts} />);
    expect(screen.getByText("Option A")).toBeDefined();
    expect(screen.getByText("Option B")).toBeDefined();
  });

  it("renders label", () => {
    render(<Select options={opts} label="Choose" />);
    expect(screen.getByText("Choose")).toBeDefined();
  });

  it("shows error", () => {
    render(<Select options={opts} error="Required" />);
    expect(screen.getByText("Required")).toBeDefined();
  });

  it("is disabled when disabled prop set", () => {
    render(<Select options={opts} disabled />);
    expect(screen.getByRole("combobox")).toBeDisabled();
  });
});

// ── Textarea tests ────────────────────────────────────────────────────────────

describe("Textarea", () => {
  it("renders label", () => {
    render(<Textarea label="Message" value="" onChange={() => {}} />);
    expect(screen.getByText("Message")).toBeDefined();
  });

  it("shows error", () => {
    render(<Textarea error="Too short" value="" onChange={() => {}} />);
    expect(screen.getByText("Too short")).toBeDefined();
  });

  it("shows character counter when showCharCount and maxLength are set", () => {
    render(<Textarea showCharCount maxLength={100} value="hello" onChange={() => {}} />);
    expect(screen.getByText("5/100")).toBeDefined();
  });
});

// ── Modal tests ───────────────────────────────────────────────────────────────

describe("Modal", () => {
  it("does not render when isOpen is false", () => {
    render(
      <Modal isOpen={false} onClose={() => {}}>
        Content
      </Modal>,
    );
    expect(screen.queryByText("Content")).toBeNull();
  });

  it("renders children when isOpen is true", () => {
    render(
      <Modal isOpen={true} onClose={() => {}}>
        Modal Content
      </Modal>,
    );
    expect(screen.getByText("Modal Content")).toBeDefined();
  });

  it("renders title", () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="My Modal">
        Content
      </Modal>,
    );
    expect(screen.getByText("My Modal")).toBeDefined();
  });

  it("calls onClose when × is clicked", () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} title="Test">
        Content
      </Modal>,
    );
    fireEvent.click(screen.getByLabelText("Close dialog"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose on backdrop click", () => {
    const onClose = vi.fn();
    const { container } = render(
      <Modal isOpen={true} onClose={onClose}>
        Content
      </Modal>,
    );
    const backdrop = container.firstChild as Element;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose on Escape key", () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose}>
        Content
      </Modal>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("has role=dialog and aria-modal", () => {
    render(
      <Modal isOpen={true} onClose={() => {}}>
        Content
      </Modal>,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
  });
});

// ── DataTable tests ───────────────────────────────────────────────────────────

describe("DataTable", () => {
  const columns = [
    { key: "name" as const, header: "Name", sortable: true },
    { key: "status" as const, header: "Status" },
  ];
  const data = [
    { name: "Alice", status: "active" },
    { name: "Bob", status: "inactive" },
  ];

  it("renders all rows", () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByText("Alice")).toBeDefined();
    expect(screen.getByText("Bob")).toBeDefined();
  });

  it("renders empty state", () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="No results" />);
    expect(screen.getByText("No results")).toBeDefined();
  });

  it("renders column headers", () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Status")).toBeDefined();
  });

  it("calls onSort when sortable header is clicked", () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={data} onSort={onSort} />);
    fireEvent.click(screen.getByText("Name"));
    expect(onSort).toHaveBeenCalledWith("name", "asc");
  });

  it("toggles sort direction on second click", () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={data} onSort={onSort} />);
    fireEvent.click(screen.getByText("Name"));
    fireEvent.click(screen.getByText("Name"));
    expect(onSort).toHaveBeenLastCalledWith("name", "desc");
  });
});

// ── Tabs tests ────────────────────────────────────────────────────────────────

describe("Tabs", () => {
  const tabs = [
    { key: "a", label: "Tab A", content: <div>Content A</div> },
    { key: "b", label: "Tab B", content: <div>Content B</div> },
  ];

  it("shows active tab content", () => {
    render(<Tabs tabs={tabs} activeTab="a" onChange={() => {}} />);
    expect(screen.getByText("Content A")).toBeDefined();
  });

  it("hides inactive tab content", () => {
    render(<Tabs tabs={tabs} activeTab="a" onChange={() => {}} />);
    // Tab B content should be hidden
    expect(screen.queryByText("Content B")).toBeNull();
  });

  it("calls onChange when tab is clicked", () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} activeTab="a" onChange={onChange} />);
    fireEvent.click(screen.getByText("Tab B"));
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("has correct ARIA attributes", () => {
    render(<Tabs tabs={tabs} activeTab="a" onChange={() => {}} />);
    const tablist = screen.getByRole("tablist");
    expect(tablist).toBeDefined();
    const activeTab = screen.getByRole("tab", { name: "Tab A" });
    expect(activeTab.getAttribute("aria-selected")).toBe("true");
  });
});

// ── Card tests ────────────────────────────────────────────────────────────────

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Card body</Card>);
    expect(screen.getByText("Card body")).toBeDefined();
  });

  it("renders header slot", () => {
    render(<Card header={<span>Header</span>}>Body</Card>);
    expect(screen.getByText("Header")).toBeDefined();
  });

  it("renders footer slot", () => {
    render(<Card footer={<span>Footer</span>}>Body</Card>);
    expect(screen.getByText("Footer")).toBeDefined();
  });

  it("calls onClick when clicked and onClick is set", () => {
    const onClick = vi.fn();
    render(<Card onClick={onClick}>Clickable</Card>);
    fireEvent.click(screen.getByText("Clickable"));
    expect(onClick).toHaveBeenCalled();
  });

  it("has role=button when onClick is set", () => {
    render(<Card onClick={() => {}}>Clickable</Card>);
    expect(screen.getByRole("button")).toBeDefined();
  });
});

// ── PageHeader tests ──────────────────────────────────────────────────────────

describe("PageHeader", () => {
  it("renders title as h1", () => {
    render(<PageHeader title="Dashboard" />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1.textContent).toBe("Dashboard");
  });

  it("renders subtitle", () => {
    render(<PageHeader title="T" subtitle="Subtitle text" />);
    expect(screen.getByText("Subtitle text")).toBeDefined();
  });

  it("renders actions slot", () => {
    render(<PageHeader title="T" actions={<button>Action</button>} />);
    expect(screen.getByText("Action")).toBeDefined();
  });

  it("does not render subtitle when not provided", () => {
    render(<PageHeader title="T" />);
    expect(screen.queryByTestId("subtitle")).toBeNull();
  });
});
