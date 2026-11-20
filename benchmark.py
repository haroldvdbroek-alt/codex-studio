"""Meet uitsluitend fictieve tijdelijke projecten, nooit een opgegeven projectroot."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import tempfile
import time

import backup
import reporting
import studio
from studio_logging import log_event

TYPES = ("python", "web", "ai", "automation")
PREFIX = "codex-studio-benchmark-"
MAX_PROJECTS = 200
MAX_REPEAT = 10
MAX_FILES = 5000
MAX_BYTES = 2 * 1024 * 1024
TIME_LIMIT = 60


def check_deadline(deadline):
    if time.monotonic() > deadline:
        raise ValueError("Benchmarktermijn overschreden.")


@dataclass(frozen=True)
class Workspace:
    path: Path
    parent: Path
    identity: tuple


def identity(path):
    info = path.lstat()
    return info.st_dev, info.st_ino, info.st_mode


def make_workspace():
    parent = backup.local_path(Path(tempfile.gettempdir()))
    studio.reject_links(parent)
    parent = parent.resolve(strict=True)
    studio_root = Path(studio.__file__).absolute().parent
    excluded = (studio_root, studio_root.parent, backup.local_path(Path.home() / "Projects"))
    if any(parent.is_relative_to(path) for path in excluded):
        raise ValueError("Tijdelijke basis ligt in een projectomgeving.")
    # Alleen markerbestaan controleren, nooit projecten hierin scannen of lezen.
    for ancestor in (parent, *parent.parents):
        if os.path.lexists(ancestor / studio.METADATA_FILE) or os.path.lexists(ancestor / ".git"):
            raise ValueError("Tijdelijke basis ligt binnen een geregistreerd project of repository.")
    path = Path(tempfile.mkdtemp(prefix=PREFIX, dir=parent)).absolute()
    studio.reject_links(path)
    return Workspace(path, parent, identity(path))


def cleanup(workspace):
    """Controleer het absolute doel vóór uitsluitend de eigen boom te verwijderen."""
    path = workspace.path
    if not os.path.lexists(path):
        return
    studio.reject_links(path)
    resolved = path.resolve(strict=True)
    if (resolved != path or resolved.parent != workspace.parent or not path.name.startswith(PREFIX)
            or identity(path) != workspace.identity):
        raise ValueError("Onveilig of vervangen tijdelijk opruimdoel; niets verwijderd.")
    shutil.rmtree(path)


def fixture_plan(projects):
    catalog = studio.update_catalog()
    if any(kind not in catalog or catalog[kind]["reason"] for kind in TYPES):
        raise ValueError("Geen compleet geldig lokaal manifest.")
    specs = {kind: studio.template_spec(kind) for kind in TYPES}
    files, total = [], 0
    for number in range(projects):
        kind = TYPES[number % len(TYPES)]
        name = f"bench-{number:04d}"
        metadata = {"schema_version": 1, "project": {"name": name}, "generator": {"version": None},
                    "template": {"id": kind, "version": specs[kind]["version"]}}
        content = {studio.METADATA_FILE: json.dumps(metadata).encode("utf-8")}
        for value in specs[kind]["files"]:
            relative = studio.safe_relative_path(value.replace("project_package", name.replace("-", "_")))
            if not backup.archive_name_safe(relative) or relative.as_posix() in content:
                raise ValueError("Onveilig/conflicterend fictief bestand.")
            if relative.name == "pyproject.toml":
                data = f'[project]\nname = "{name}"\nversion = "0.0.0"\n'.encode()
            elif relative.suffix == ".py":
                data = b"raise RuntimeError('Fictieve benchmarkcode mag nooit worden uitgevoerd')\n"
            else:
                data = b"# Uitsluitend fictieve benchmarkinhoud\n"
            content[relative.as_posix()] = data
        total += sum(len(value) for value in content.values())
        if sum(len(item[2]) for item in files) + len(content) > MAX_FILES or total > MAX_BYTES:
            raise ValueError("Fictieve dataset overschrijdt grenzen.")
        files.append((name, kind, content))
    return files


def seed(workspace, plan, deadline):
    root = workspace.path / "projects"
    root.mkdir()
    for name, _, files in plan:
        directory = root / name
        directory.mkdir()
        for relative, content in files.items():
            check_deadline(deadline)
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            studio.reject_links(path.parent)
            with path.open("xb") as output:
                output.write(content)
    return root


def fingerprint(root, plan, deadline):
    expected = {f"{name}/{path}" for name, _, files in plan for path in files}
    found = set()
    for current, directories, files in os.walk(root, followlinks=False):
        check_deadline(deadline)
        studio.reject_links(Path(current))
        for name in (*directories, *files):
            if studio.is_link((Path(current) / name).lstat()):
                raise ValueError("Koppeling in fictieve dataset.")
        found.update((Path(current) / name).relative_to(root).as_posix() for name in files)
        if len(found) > MAX_FILES:
            raise ValueError("Onverwachte datasetgroei.")
    if found != expected:
        raise ValueError("Fictieve dataset is gewijzigd.")
    result = []
    for relative in sorted(found):
        check_deadline(deadline)
        path = root / relative
        data = studio.read_bytes_file(path)
        result.append((relative, len(data), hashlib.sha256(data).hexdigest(), path.stat().st_mtime_ns))
    return tuple(result)


def measure(name, operation, validate, projects, repeat, deadline):
    check_deadline(deadline)
    validate(operation())  # Eén opwarmronde, buiten de cijfers.
    samples = []
    for _ in range(repeat):
        check_deadline(deadline)
        start = time.perf_counter_ns()
        value = operation()
        elapsed = time.perf_counter_ns() - start
        if elapsed < 0:
            raise ValueError("Ongeldige tijdmeting.")
        validate(value)  # Correctheidscontrole buiten het gemeten interval.
        samples.append(elapsed / 1_000_000)
    average = statistics.fmean(samples)
    return reporting.Timing(name, projects, tuple(round(value, 6) for value in samples),
                            round(min(samples), 6), round(statistics.median(samples), 6),
                            round(average, 6), round(max(samples), 6),
                            round(projects * 1000 / average, 2) if average > 0 else None)


def collect(projects=12, repeat=3):
    workspace, timings, results, unchanged, removed, counts = None, [], [], False, False, ()
    completion, code = "complete", 0
    try:
        if type(projects) is not int or not 4 <= projects <= MAX_PROJECTS or type(repeat) is not int or not 1 <= repeat <= MAX_REPEAT:
            raise ValueError("Ongeldige benchmarkomvang.")
        deadline = time.monotonic() + TIME_LIMIT
        plan = fixture_plan(projects)
        counts = tuple((kind, sum(item[1] == kind for item in plan)) for kind in TYPES)
        workspace = make_workspace()
        root = seed(workspace, plan, deadline)
        before = fingerprint(root, plan, deadline)
        names = {item[0] for item in plan}
        def validate_list(value):
            found, warnings = value
            if warnings or len(found) != projects or {item.name for item in found} != names:
                raise ValueError("List-resultaat wijkt af.")
        def validate_updates(value):
            found, warnings, missing = value
            if (warnings or missing or len(found) != projects or {item.name for item in found} != names
                    or any(item.status != "ACTUEEL" or item.problem for item in found)):
                raise ValueError("Updates-resultaat wijkt af.")
        def check_all():
            found = []
            for name, _, _ in plan:
                check_deadline(deadline)
                found.append(studio.check_project(root, name, run_tests=False))
            return found
        def validate_checks(value):
            if len(value) != projects or any(any(item.status == "FAIL" for item in row) or not any(
                    item.label == "Tests" and item.status == "SKIP" for item in row) for row in value):
                raise ValueError("Check-resultaat wijkt af.")
        for name, operation, validate in (
                ("list", lambda: studio.list_projects(root), validate_list),
                ("updates", lambda: studio.project_updates(root), validate_updates),
                ("check", check_all, validate_checks)):
            timings.append(measure(name, operation, validate, projects, repeat, deadline))
            results.append(studio.CheckResult("PASS", name, "Alle fictieve projecten verwerkt met het verwachte resultaat."))
        unchanged = fingerprint(root, plan, deadline) == before
        if not unchanged:
            raise ValueError("Datasetinhoud gewijzigd.")
        results.append(studio.CheckResult("PASS", "Dataset", "Inhoud, bestandslijst en wijzigingstijden van de fictieve bestanden zijn ongewijzigd."))
        results.append(studio.CheckResult("WARN", "Meetbereik", "Kleine fictieve projecten, zonder Git-repository of testuitvoering; dit voorspelt geen snelheid van echte projecten of andere computers."))
    except KeyboardInterrupt:
        completion, code = "cancelled", 130
        results.append(studio.CheckResult("SKIP", "Benchmark", "Geannuleerd; onvolledige metingen zijn geen geslaagde benchmark."))
    except (OSError, ValueError, RecursionError):
        log_event("BENCHMARK_FAILED")
        completion, code = "error", 1
        results.append(studio.CheckResult("FAIL", "Benchmark", "Dataset, tijdelijke locatie, manifest, controle-uitkomst of tijd-/groottelimiet ongeldig; geen volledig resultaat."))
    finally:
        if workspace is not None:
            try:
                cleanup(workspace)
                removed = not os.path.lexists(workspace.path)
                if not removed:
                    raise ValueError("Tijdelijke map bestaat nog.")
                results.append(studio.CheckResult("PASS", "Opruimen", "Uitsluitend de eigen gecontroleerde tijdelijke map verwijderd."))
            except (OSError, ValueError, KeyboardInterrupt):
                log_event("BENCHMARK_CLEANUP_FAILED")
                completion = "error" if code != 130 else "cancelled"
                code = 1 if code != 130 else 130
                results.append(studio.CheckResult("FAIL", "Opruimen", "Eigen tijdelijke map kon niet veilig worden verwijderd; fictieve bestanden kunnen achterblijven. Geen ander opruimdoel gebruikt."))
    info = reporting.BenchmarkInfo(projects if type(projects) is int else 0, repeat if type(repeat) is int else 0,
                                   counts, tuple(timings), unchanged, removed)
    return reporting.build(results, command="benchmark", benchmark=info, completion=completion, exit_code=code)


def run(projects=12, repeat=3, output_format="text"):
    return reporting.run(lambda: collect(projects, repeat), command="benchmark", output_format=output_format)
