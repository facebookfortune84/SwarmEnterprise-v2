import json
from pathlib import Path


def fix_phase_mode_tools():
    """Fix the missing comma in phase_mode_tools.json"""
    file_path = Path("assets/tools/phase_mode_tools.json")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the problematic line and add comma
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines):
        if (
            '"Note: Before coming up with phase breakdown' in line
            and '"parameters"' in lines[i + 1]
        ):
            # Add comma to this line
            if not line.endswith(","):
                line = line.rstrip() + ","
        fixed_lines.append(line)

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(fixed_lines))

    # Validate
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
        print("✅ Fixed phase_mode_tools.json")
    except json.JSONDecodeError as e:
        print(f"❌ Still broken: {e}")


def fix_agent_tools():
    """Remove duplicate content from Agent Tools.json"""
    file_path = Path("assets/tools/Agent Tools.json")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the first complete JSON object
    import re

    match = re.search(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", content, re.DOTALL)

    if match:
        json_str = match.group(1)
        data = json.loads(json_str)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print("✅ Fixed Agent Tools.json")
    else:
        print("❌ Could not extract JSON from Agent Tools.json")


if __name__ == "__main__":
    print("Fixing JSON files...")
    fix_phase_mode_tools()
    fix_agent_tools()
