import importlib
import subprocess
import sys
import os
import json


CONFIG_PATH       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
REQUIREMENTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")


def load_config() -> dict:
    """Load project config from config.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def load_requirements() -> list:
    """
    Parse requirements.txt and return a list of dependency dicts.
    Skips blank lines and comments.
    Format: [{"import_name": ..., "install_name": ..., "version": ...}]
    """
    deps = []
    with open(REQUIREMENTS_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split package name and version constraint
            # e.g. "psutil>=5.9.0" -> ("psutil", ">=5.9.0")
            for op in (">=", "<=", "==", ">", "<", "!="):
                if op in line:
                    name, version = line.split(op, 1)
                    version = op + version
                    break
            else:
                name, version = line, ""

            # Map install name to import name
            # Some packages have different install vs import names
            import_name_map = {
                "python-dotenv": "dotenv",
            }
            install_name = name.strip()
            import_name  = import_name_map.get(install_name, install_name)

            deps.append({
                "import_name":  import_name,
                "install_name": install_name,
                "version":      version,
            })
    return deps


def check_dependency(dep: dict) -> bool:
    """Return True if the package is already installed."""
    try:
        importlib.import_module(dep["import_name"])
        return True
    except ImportError:
        return False


def install_dependency(dep: dict) -> bool:
    """Install a missing package via pip. Returns True if successful."""
    package = f"{dep['install_name']}{dep['version']}"
    print(f"  Installing {package}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def run_setup() -> bool:
    """
    Read requirements.txt, check each dependency,
    and install any that are missing.
    Returns True if all dependencies are satisfied.
    """
    try:
        config = load_config()
        print(f"Setting up {config.get('project', 'project')} v{config.get('version', '')}...\n")
    except FileNotFoundError:
        print("  [ERROR] config.json not found.")
        return False

    try:
        deps = load_requirements()
    except FileNotFoundError:
        print(f"  [ERROR] requirements.txt not found at {REQUIREMENTS_PATH}")
        return False

    already_ok = []
    installed  = []
    failed     = []

    for dep in deps:
        if check_dependency(dep):
            already_ok.append(dep["install_name"])
        else:
            if install_dependency(dep):
                installed.append(dep["install_name"])
            else:
                failed.append(dep["install_name"])

    if already_ok:
        print(f"  [OK]     Already installed : {', '.join(already_ok)}")
    if installed:
        print(f"  [OK]     Newly installed   : {', '.join(installed)}")
    if failed:
        print(f"  [FAILED] Could not install : {', '.join(failed)}")
        print(f"\n  Try manually: pip install -r requirements.txt")

    print()
    return len(failed) == 0


if __name__ == "__main__":
    success = run_setup()
    if not success:
        sys.exit(1)
    print("All dependencies satisfied.\n")