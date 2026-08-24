from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PYTHON_VERSION_FILE = ROOT / ".python-version"
DOCKERFILE = ROOT / "Dockerfile"
REQUIREMENTS_IN = ROOT / "requirements.in"
REQUIREMENTS_LOCK = ROOT / "requirements.txt"
DIRECT_DEPENDENCIES = {
    "av",
    "colorama",
    "coverage",
    "pytest",
    "pytest-asyncio",
    "google-auth",
    "google-cloud-bigquery",
    "gspread",
    "httpx",
    "pillow",
    "python-dotenv",
    "python-telegram-bot[job-queue,rate-limiter]",
    "tzdata",
}


def running_python_version() -> str:
    return ".".join(str(part) for part in sys.version_info[:3])


def configured_python_version() -> str:
    return PYTHON_VERSION_FILE.read_text(encoding="ascii").strip()


def set_python_version(version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Invalid stable Python version: {version}")
    PYTHON_VERSION_FILE.write_text(f"{version}\n", encoding="ascii")
    docker_text = DOCKERFILE.read_text(encoding="utf-8")
    updated = re.sub(
        r"(?m)^FROM python:\d+\.\d+\.\d+-slim(?P<stage>\s+AS\s+[A-Za-z0-9_-]+)?$",
        rf"FROM python:{version}-slim\g<stage>",
        docker_text,
        count=1,
    )
    if updated == docker_text and f"FROM python:{version}-slim" not in docker_text:
        raise RuntimeError("Dockerfile does not contain the expected pinned Python image")
    DOCKERFILE.write_text(updated, encoding="utf-8")


def check_versions() -> list[str]:
    errors: list[str] = []
    expected = configured_python_version()
    actual = running_python_version()
    if actual != expected:
        errors.append(f"Local Python is {actual}; project requires {expected}")

    docker_text = DOCKERFILE.read_text(encoding="utf-8")
    if f"FROM python:{expected}-slim" not in docker_text:
        errors.append(f"Dockerfile must use python:{expected}-slim")

    requested = {
        line.strip().lower()
        for line in REQUIREMENTS_IN.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if requested != DIRECT_DEPENDENCIES:
        errors.append("requirements.in does not match the expected direct dependencies")

    locked = {
        line.split("==", 1)[0].strip().lower()
        for line in REQUIREMENTS_LOCK.read_text(encoding="utf-8").splitlines()
        if "==" in line
    }
    locked_direct_dependencies = {
        dependency.split("[", 1)[0] for dependency in DIRECT_DEPENDENCIES
    }
    missing = sorted(locked_direct_dependencies - locked)
    if missing:
        errors.append(f"Direct dependencies missing from requirements.txt: {', '.join(missing)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep Windows, CI and Docker Python versions aligned.")
    parser.add_argument("--set-running", action="store_true", help="Write the running Python patch version to project files.")
    args = parser.parse_args()

    if args.set_running:
        set_python_version(running_python_version())

    errors = check_versions()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Runtime aligned on Python {configured_python_version()} with a complete dependency lock.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
