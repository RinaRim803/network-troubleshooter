import json
import importlib
import subprocess
import sys
import os


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_dependencies() -> list:
    """Load dependency list from config.json."""
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    return config.get("dependencies", [])


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
    Check all dependencies from config.json.
    Install any that are missing.
    Returns True if all dependencies are satisfied.
    """
    print("Checking dependencies...\n")

    try:
        deps = load_dependencies()
    except FileNotFoundError:
        print(f"  [ERROR] config.json not found at {CONFIG_PATH}")
        return False
    except json.JSONDecodeError:
        print("  [ERROR] config.json is malformed.")
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
        for dep in deps:
            if dep["install_name"] in failed:
                print(f"    pip install {dep['install_name']}{dep['version']}")

    print()
    return len(failed) == 0


if __name__ == "__main__":
    success = run_setup()
    if not success:
        sys.exit(1)
    print("All dependencies satisfied.\n")
