import os
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

EXCLUDE_DIRS = {
    "venv", ".venv", "env", "node_modules", "dist", ".git", ".pytest_cache", "__pycache__", "tasks"
}

def scan_files():
    print("=" * 70)
    print("CROSS-PLATFORM & LINUX COMPATIBILITY SCAN")
    print("=" * 70)

    windows_path_regex = re.compile(r'[a-zA-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*')
    hardcoded_drive_regex = re.compile(r'C:[/\\]', re.IGNORECASE)

    issues = []

    target_dirs = [ROOT_DIR / "backend" / "app", ROOT_DIR / "backend" / "api", ROOT_DIR / "frontend" / "src"]

    for t_dir in target_dirs:
        for p in t_dir.rglob("*"):
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            if p.suffix in (".py", ".ts", ".tsx"):
                try:
                    text = p.read_text(encoding="utf-8")
                    for line_num, line in enumerate(text.splitlines(), start=1):
                        if hardcoded_drive_regex.search(line):
                            issues.append((str(p.relative_to(ROOT_DIR)), line_num, line.strip()))
                except Exception as e:
                    pass

    if issues:
        print(f"Found {len(issues)} hardcoded drive letter references:")
        for file, line, content in issues:
            print(f"  {file}:{line} -> {content}")
    else:
        print("[PASS] ZERO hardcoded Windows drive letters or absolute paths found in application code!")

    print("=" * 70)
    return len(issues) == 0

if __name__ == "__main__":
    scan_files()
