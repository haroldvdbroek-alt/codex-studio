"""Dezelfde volledige testopdracht lokaal en in GitHub Actions; publiceert niets."""

from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main() -> int:
    node = shutil.which("node")
    tasks = [("Generator, menu, manifest en zelfstandige projecten", ROOT)]
    tasks.extend((f"Template: {name}", ROOT / "templates" / name)
                 for name in ("python-app", "web-app", "ai-app", "automation"))
    failures = []
    if node is None:
        print("FOUT: Node.js ontbreekt; JavaScript-controles kunnen niet worden uitgevoerd.", flush=True)
        failures.append("Node.js ontbreekt")
    else:
        try:
            result = subprocess.run([node, "--version"], capture_output=True, text=True,
                                    check=True, timeout=10)
            major = int(result.stdout.strip().removeprefix("v").split(".")[0])
            if major < 22:
                print("FOUT: gebruik Node.js 22 of hoger.", flush=True)
                failures.append("Node.js te oud")
        except (OSError, ValueError, subprocess.SubprocessError):
            failures.append("Node.js-versie niet vast te stellen")
    for label, directory in tasks:
        print(f"\n=== {label} ===", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=directory, timeout=180,
            )
            if result.returncode:
                failures.append(label)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"FOUT: {label}: {type(error).__name__}", flush=True)
            failures.append(label)
    if node is not None:
        print("\n=== JavaScript-webtests ===", flush=True)
        try:
            result = subprocess.run([node, "--test", "tests/counter.test.cjs"],
                                    cwd=ROOT / "templates/web-app", timeout=60)
            if result.returncode:
                failures.append("JavaScript-webtests")
        except (OSError, subprocess.TimeoutExpired):
            failures.append("JavaScript-webtests")
    if failures:
        print("\nNiet volledig geslaagd: " + ", ".join(failures), flush=True)
        return 1
    print("\nAlle testsuites geslaagd; controleer gemelde skips afzonderlijk.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
