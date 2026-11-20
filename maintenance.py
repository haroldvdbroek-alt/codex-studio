"""Begrensde onderhoudscontrole; geen imports van onderzochte code of reparaties."""

import ast
import os
import re
import time
import tomllib
import warnings

import backup
import quality
import reporting
import studio


def finding(status, label, message):
    return studio.CheckResult(status, "VASTSTELLING | " + label, message)


def advice(label, message):
    return studio.CheckResult("WARN", "AANBEVELING | " + label, message)


def python_generator_files(root):
    """Lees uitsluitend de letterlijke TEMPLATE_FILES-lijst, voer niets uit."""
    source = studio.read_bytes_file(root / "create_project.py")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Parserwaarschuwingen kunnen bronregels tonen.
        tree = ast.parse(source)
    assignments = [node.value for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "TEMPLATE_FILES"
                           for target in node.targets)]
    if len(assignments) != 1:
        return None
    value = ast.literal_eval(assignments[0])
    if (not isinstance(value, (tuple, list)) or not value
            or len(value) > quality.MAX_ITEMS or not all(isinstance(item, str) for item in value)):
        raise ValueError("Geen geldige bestandenlijst")
    return tuple(studio.safe_relative_path(item).as_posix() for item in value)


def extra_checks(root, deadline):
    results = []
    quality.check_deadline(deadline)
    try:
        files = python_generator_files(root)
        spec = studio.template_spec("python")
        expected = tuple(studio.safe_relative_path(item).as_posix() for item in spec["files"])
        if files is None:
            results.append(finding("SKIP", "Generator en manifest", "Geen unieke letterlijke TEMPLATE_FILES-lijst; consistentie vereist aanvullende analyse."))
        elif len(files) != len(set(files)) or set(files) != set(expected):
            results.append(finding("FAIL", "Generator en manifest", "Python-bestandenlijst van generator en manifest verschilt of bevat duplicaten."))
        else:
            results.append(finding("PASS", "Generator en manifest", "Gedeclareerde Python-bestandenlijsten komen overeen; dit bewijst geen werkende generatie."))
    except (OSError, ValueError, TypeError, SyntaxError, RecursionError):
        results.append(finding("FAIL", "Generator en manifest", "Bestandenlijst of manifest onleesbaar, onveilig of niet geldig te analyseren; broninhoud niet getoond."))

    for kind in sorted(studio.PROJECT_TYPES):
        quality.check_deadline(deadline)
        try:
            spec = studio.template_spec(kind)
            directory = root / "templates" / studio.safe_relative_path(spec["directory"])
            if not os.path.lexists(directory) and kind in quality.PLANNED:
                results.append(finding("SKIP", "Projectversie " + kind, "Templatebron is gepland en ontbreekt; geen pakketversie beoordeeld."))
                continue
            studio.reject_links(directory)
            if "pyproject.toml" not in spec["files"]:
                results.append(finding("SKIP", "Projectversie " + kind, "Geen pyproject.toml gedeclareerd; geen Python-pakketversie vereist."))
                continue
            config = tomllib.loads(studio.read_bytes_file(directory / "pyproject.toml").decode("utf-8-sig"))
            version = config.get("project", {}).get("version")
            if version is None and "version" in config.get("project", {}).get("dynamic", []):
                results.append(finding("SKIP", "Projectversie " + kind, "Dynamische pakketversie; vaststellen zou aanvullende analyse vereisen."))
                continue
            studio.parse_semver(version)
            results.append(finding("PASS", "Projectversie " + kind, "Pakketversie is geldig MAJOR.MINOR.PATCH; deze staat los van de templateversie."))
        except (OSError, ValueError, TypeError, AttributeError, RecursionError):
            results.append(finding("FAIL", "Projectversie " + kind, "Gedeclareerde pakketconfiguratie of MAJOR.MINOR.PATCH-versie ontbreekt, is onveilig of ongeldig."))

    quality.check_deadline(deadline)
    try:
        text = studio.read_bytes_file(root / "CHANGELOG.md").decode("utf-8-sig")
        headings = re.findall(r"^##\s+\[([^\]\r\n]+)\]", text, flags=re.MULTILINE)
        for heading in headings:
            if heading != "Unreleased":
                studio.parse_semver(heading)
        if len(headings) != len(set(headings)):
            raise ValueError("Dubbele secties")
        if not headings:
            results.append(finding("FAIL", "Changelog", "Geen sectie ## [Unreleased] of ## [MAJOR.MINOR.PATCH] gevonden."))
        else:
            results.append(finding("PASS", "Changelog", "Gevonden changelogversies zijn geldig en secties zijn uniek; inhoud en publicatie niet geverifieerd."))
        results.append(finding("SKIP", "Studioreleaseversie", "Geen centrale gezaghebbende studioreleaseversie afgesproken; template- en pakketversies worden niet als studioversie gebruikt."))
    except (OSError, ValueError, TypeError, RecursionError):
        results.append(finding("FAIL", "Changelog", "Changelog onleesbaar/onveilig of gevonden versies/secties ongeldig; inhoud niet herhaald."))
    results.extend([
        finding("SKIP", "Testdekking", "Niet vastgesteld. Testbestanden en syntaxis bewijzen geen dekking; aanvullende analyse van gedrag en tests is nodig."),
        finding("SKIP", "Testuitvoering", "Geen tests, projectcode, Git- of andere subprocessen gestart."),
        advice("Inhoudelijke beoordeling", "Beoordeel of handleidingen, templatevoorbeelden en tests het gewenste gedrag beschrijven; aanwezigheid bewijst geen volledigheid."),
        advice("Releasebeoordeling", "Verifieer changeloginhoud, GitHub Actions, reviews en overige externe releasevoorwaarden zelf; deze controle geeft geen publicatiegoedkeuring."),
    ])
    return results


def collect():
    results = []
    try:
        deadline = time.monotonic() + quality.STATIC_SECONDS
        root = backup.local_path(quality.STUDIO_ROOT)
        studio.reject_links(root)
        root = root.resolve(strict=True)
        # Hergebruik de veilige structurele controles, maar start ook geen Git.
        for item in quality.static_checks(include_git=False):
            if item.label == "Handmatige beoordeling":
                continue
            if item.status == "WARN" and item.label.startswith("Template "):
                # Het ontbreken is objectief; 'gepland' is geen kapotte aanwezige template.
                results.append(finding("SKIP", item.label, item.message))
            else:
                results.append(finding(item.status, item.label, item.message))
        results.extend(extra_checks(root, deadline))
        quality.check_deadline(deadline)
        return reporting.build(results, command="maintenance")
    except KeyboardInterrupt:
        results.append(finding("SKIP", "Onderhoudscontrole", "Geannuleerd; geen automatische reparaties uitgevoerd."))
        return reporting.build(results, command="maintenance", completion="cancelled", exit_code=130)
    except Exception:
        results.append(finding("FAIL", "Onderhoudscontrole", "Controle onvolledig: onveilig pad, leesfout of verwerkingslimiet; details niet getoond."))
        return reporting.build(results, command="maintenance", completion="error", exit_code=1)


def run(output_format="text"):
    # Bewust geen --output of --run-tests; uitsluitend stdout en veilige stderr-logs.
    return reporting.run(collect, output_format=output_format, command="maintenance")
