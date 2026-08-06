#!/usr/bin/env python3
"""Validate and scaffold the branch-local camera device-tree artifact catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


INDEX_PATH = Path("ci/camera-device-tree-artifacts.json")
FRAGMENT_DIR = Path("ci/camera-device-tree-artifacts")
SUPPORTED_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
OUTPUT_PATTERN = re.compile(r"^[A-Za-z0-9_+.-]+\.dtb(?:o)?$")
SOURCE_PATTERN = re.compile(r"^[A-Za-z0-9_+./-]+\.dts$")
GROUP_PATTERN = re.compile(r"^(?:(?:official|partners)/[a-z0-9][a-z0-9.-]*|shared)$")

PLATFORM_TOKENS = (
    ("nru-161v-awp", "nru-161v-awp"),
    ("jco-6000-orn-a", "jco-6000-orn-a"),
    ("afe-r750", "afe-r750-orinnx"),
    ("aie510-onx", "aie510-onx"),
    ("aie900a", "aie900a-ao"),
    ("eac5000", "eac-5000"),
    ("d133oxb", "d133oxb"),
    ("2nor0x", "2nor0x"),
    ("j401", "j401"),
    ("x6-orn", "x6-orin"),
    ("tek-orin", "tek-orin"),
    ("p3767-camera-p3768", "orin-nano"),
    ("p3737-camera-vls", "agx-orin"),
)
SUPPORTED_PRODUCT_PLATFORMS = {
    "orin-nano",
    "agx-orin",
    "2nor0x",
    "afe-r750-orinnx",
    "aie510-onx",
    "aie900a-ao",
    "d133oxb",
    "eac-5000",
    "j401",
    "jco-6000-orn-a",
    "nru-161v-awp",
    "x6-orin",
}
OFFICIAL_PLATFORMS = {"orin-nano", "agx-orin"}


class CatalogError(ValueError):
    """Raised when Makefile, DTS, and catalog inventories disagree."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CatalogError(f"branch-local catalog file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"catalog document must be an object: {path}")
    return value


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def discover_makefile_outputs(root: Path) -> dict[str, dict[str, str]]:
    outputs: dict[str, dict[str, str]] = {}
    for makefile in sorted(root.rglob("Makefile")):
        text = makefile.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\\\r?\n", " ", text)
        for match in re.finditer(
            r"^\s*(dtb-y|dtbo-y)\s*\+=\s*(.*?)\s*(?:#.*)?$",
            text,
            re.MULTILINE,
        ):
            variable = match.group(1)
            suffix = ".dtbo" if variable == "dtbo-y" else ".dtb"
            for token in re.findall(r"[A-Za-z0-9_+./-]+\.dtb(?:o)?", match.group(2)):
                if "$" in token or "*" in token or not token.endswith(suffix):
                    continue
                output = PurePosixPath(token).name
                record = {
                    "output": output,
                    "makefile": _relative(makefile, root),
                    "makeVariable": variable,
                    "source": _relative(
                        makefile.parent / f"{Path(output).stem}.dts", root
                    ),
                }
                previous = outputs.get(output)
                if previous is not None and previous != record:
                    if "camera-" in output.lower():
                        raise CatalogError(
                            f"camera output {output} is declared by multiple Makefiles"
                        )
                    # NVIDIA staging Makefiles repeat generic DTBs from the root
                    # Makefile. Prefer the shortest canonical source path.
                    if len(PurePosixPath(record["makefile"]).parts) >= len(
                        PurePosixPath(previous["makefile"]).parts
                    ):
                        continue
                outputs[output] = record
    return outputs


def discover_camera_sources(root: Path) -> dict[str, str]:
    return {
        _relative(path, root): f"{path.stem}.dtbo"
        for path in sorted(root.rglob("*.dts"))
        if "camera-" in path.name.lower()
    }


def infer_platform(output: str) -> str | None:
    lower = output.lower()
    for token, platform in PLATFORM_TOKENS:
        if token in lower:
            return platform
    return None


def infer_camera(output: str) -> str:
    lower = output.lower()
    for camera in ("vlm-gm2", "vls-gm2", "vls3", "tevs"):
        if camera in lower:
            return camera
    return "nvidia-reference"


def infer_variant(output: str) -> str:
    lower = output.lower()
    for token, variant in (
        ("dual-phy-vls-gm2-fsync", "dual-phy-fsync"),
        ("dual-phy-vls-gm2", "dual-phy"),
        ("tunnel-fsync", "tunnel-fsync"),
        ("fsync-external", "fsync-external"),
        ("ext-io", "ext-io"),
        ("tunnel", "tunnel"),
        ("fsync", "fsync"),
        ("8cam", "8cam"),
        ("4cam", "4cam"),
        ("tevs-dual", "dual"),
    ):
        if token in lower:
            return variant
    return "default"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def infer_entry(source: str, declaration: dict[str, str] | None) -> dict[str, Any]:
    output = declaration["output"] if declaration else f"{Path(source).stem}.dtbo"
    platform = infer_platform(output)
    camera = infer_camera(output)
    variant = infer_variant(output)
    semantic_id = platform is not None and camera != "nvidia-reference"
    supported = (
        declaration is not None
        and platform in SUPPORTED_PRODUCT_PLATFORMS
        and camera != "nvidia-reference"
    )
    experimental = (
        declaration is not None
        and platform == "tek-orin"
        and camera != "nvidia-reference"
    )
    if semantic_id:
        logical_id = f"{platform}.{camera}.{variant}"
    else:
        logical_id = f"source.{_slug(Path(output).stem)}"
    entry: dict[str, Any] = {
        "id": logical_id,
        "type": "camera-overlay",
        "output": output,
        "source": source,
        "makefile": declaration["makefile"] if declaration else "",
        "makeVariable": declaration["makeVariable"] if declaration else None,
        "platforms": [platform] if platform else [],
        "camera": camera,
        "variant": variant,
        "lifecycle": (
            "supported" if supported else "experimental" if experimental else "sourceOnly"
        ),
    }
    if not supported:
        entry["reason"] = (
            "Partner platform is not selected by an installer build profile."
            if experimental
            else "Camera source is not declared by a Makefile."
            if declaration is None
            else "NVIDIA reference or unclassified camera source is not distributed by the installer."
        )
    return entry


def fragment_group(entry: dict[str, Any]) -> str:
    platforms = set(entry["platforms"])
    if len(platforms) == 1:
        platform = next(iter(platforms))
        category = "official" if platform in OFFICIAL_PLATFORMS else "partners"
        return f"{category}/{platform}"
    if platforms and platforms <= OFFICIAL_PLATFORMS:
        return "official/shared"
    if platforms and platforms.isdisjoint(OFFICIAL_PLATFORMS):
        return "partners/shared"
    return "shared"


def load_catalog(root: Path) -> dict[str, Any]:
    index_path = root / INDEX_PATH
    index = _read_json(index_path)
    if index.get("schemaVersion") != SUPPORTED_SCHEMA_VERSION:
        raise CatalogError(
            f"unknown device-tree catalog schemaVersion in {index_path}: "
            f"{index.get('schemaVersion')!r}; validator supports 1"
        )
    if index.get("kind") != "camera-device-tree-artifact-index":
        raise CatalogError(f"invalid device-tree catalog index kind in {index_path}")
    fragments = index.get("fragments")
    if not isinstance(fragments, list) or not fragments:
        raise CatalogError(f"catalog index fragments must be a non-empty list: {index_path}")
    if len(fragments) != len(set(fragments)):
        raise CatalogError(f"catalog index contains duplicate fragments: {index_path}")

    expected_paths: set[Path] = set()
    artifacts: list[dict[str, Any]] = []
    for relative in fragments:
        if not isinstance(relative, str):
            raise CatalogError(f"catalog fragment path must be a string: {relative!r}")
        posix = PurePosixPath(relative)
        if (
            posix.is_absolute()
            or ".." in posix.parts
            or tuple(posix.parts[:2]) != ("ci", "camera-device-tree-artifacts")
        ):
            raise CatalogError(f"unsafe catalog fragment path: {relative}")
        fragment_path = root.joinpath(*posix.parts)
        expected_paths.add(fragment_path.resolve())
        fragment = _read_json(fragment_path)
        if fragment.get("schemaVersion") != SUPPORTED_SCHEMA_VERSION:
            raise CatalogError(
                f"unknown device-tree fragment schemaVersion in {fragment_path}: "
                f"{fragment.get('schemaVersion')!r}"
            )
        if fragment.get("kind") != "camera-device-tree-artifact-fragment":
            raise CatalogError(f"invalid device-tree fragment kind in {fragment_path}")
        if not isinstance(fragment.get("group"), str) or not GROUP_PATTERN.fullmatch(
            fragment["group"]
        ):
            raise CatalogError(f"device-tree fragment group is missing: {fragment_path}")
        expected_relative = (FRAGMENT_DIR / f"{fragment['group']}.json").as_posix()
        if relative != expected_relative:
            raise CatalogError(
                f"device-tree fragment path {relative!r} must match group "
                f"{fragment['group']!r}: expected {expected_relative!r}"
            )
        fragment_artifacts = fragment.get("artifacts")
        if not isinstance(fragment_artifacts, list):
            raise CatalogError(f"device-tree fragment artifacts must be a list: {fragment_path}")
        if not fragment_artifacts:
            raise CatalogError(f"device-tree fragment artifacts must not be empty: {fragment_path}")
        for artifact in fragment_artifacts:
            if not isinstance(artifact, dict):
                raise CatalogError(f"device-tree artifact must be an object: {fragment_path}")
            materialized = dict(artifact)
            materialized["catalogFragment"] = relative
            materialized["catalogGroup"] = fragment["group"]
            artifacts.append(materialized)

    actual_paths = {path.resolve() for path in (root / FRAGMENT_DIR).rglob("*.json")}
    missing = expected_paths - actual_paths
    orphaned = actual_paths - expected_paths
    if missing:
        raise CatalogError(
            "catalog index references missing fragments: "
            + ", ".join(sorted(str(path) for path in missing))
        )
    if orphaned:
        raise CatalogError(
            "orphan device-tree catalog fragments are not listed by the index: "
            + ", ".join(sorted(str(path) for path in orphaned))
        )
    return {"index": index, "artifacts": artifacts}


def _validate_shape(artifact: dict[str, Any]) -> None:
    artifact_id = artifact.get("id")
    if not isinstance(artifact_id, str) or not ID_PATTERN.fullmatch(artifact_id):
        raise CatalogError(f"invalid device-tree logical ID: {artifact_id!r}")
    if artifact.get("type") not in {"base-dtb", "camera-overlay"}:
        raise CatalogError(f"device-tree {artifact_id} has invalid type")
    if not isinstance(artifact.get("output"), str) or not OUTPUT_PATTERN.fullmatch(artifact["output"]):
        raise CatalogError(f"device-tree {artifact_id} has invalid output")
    if not isinstance(artifact.get("source"), str) or not SOURCE_PATTERN.fullmatch(artifact["source"]):
        raise CatalogError(f"device-tree {artifact_id} has invalid source")
    if not isinstance(artifact.get("makefile"), str):
        raise CatalogError(f"device-tree {artifact_id} has invalid makefile")
    if artifact.get("makeVariable") not in {"dtb-y", "dtbo-y", None}:
        raise CatalogError(f"device-tree {artifact_id} has invalid makeVariable")
    if not isinstance(artifact.get("platforms"), list) or len(artifact["platforms"]) != len(set(artifact["platforms"])):
        raise CatalogError(f"device-tree {artifact_id} has invalid platforms")
    for key in ("camera", "variant"):
        if not isinstance(artifact.get(key), str):
            raise CatalogError(f"device-tree {artifact_id} has invalid {key}")
    lifecycle = artifact.get("lifecycle")
    if lifecycle not in {"supported", "experimental", "sourceOnly"}:
        raise CatalogError(f"device-tree {artifact_id} has invalid lifecycle")
    if lifecycle != "supported" and not artifact.get("reason"):
        raise CatalogError(f"device-tree {artifact_id} lifecycle {lifecycle} requires reason")
    if lifecycle == "sourceOnly" and artifact.get("makeVariable") is not None:
        # Source-only also covers declared NVIDIA reference outputs; retaining the declaration is intentional.
        pass
    if lifecycle != "sourceOnly" and artifact.get("makeVariable") is None:
        raise CatalogError(f"device-tree {artifact_id} must be declared by a Makefile")


def scaffold(root: Path) -> dict[str, Any]:
    declarations = discover_makefile_outputs(root)
    sources = discover_camera_sources(root)
    try:
        catalog = load_catalog(root)["artifacts"]
    except CatalogError:
        catalog = []
    known_outputs = {item["output"] for item in catalog}
    known_sources = {item["source"] for item in catalog}
    pending: list[dict[str, Any]] = []
    for output, declaration in sorted(declarations.items()):
        if "camera-" not in output.lower() or output in known_outputs:
            continue
        entry = infer_entry(declaration["source"], declaration)
        entry["inferred"] = ["id", "platforms", "camera", "variant", "lifecycle"]
        entry["fragmentGroup"] = fragment_group(entry)
        pending.append(entry)
    for source, output in sorted(sources.items()):
        if source in known_sources or output in declarations:
            continue
        entry = infer_entry(source, None)
        entry["inferred"] = ["id", "platforms", "camera", "variant", "lifecycle"]
        entry["fragmentGroup"] = fragment_group(entry)
        pending.append(entry)
    return {"kind": "camera-device-tree-artifact-scaffold", "artifacts": pending}


def validate_repository(root: Path) -> str:
    catalog = load_catalog(root)
    artifacts = catalog["artifacts"]
    for artifact in artifacts:
        _validate_shape(artifact)

    ids = [item["id"] for item in artifacts]
    outputs = [item["output"] for item in artifacts]
    sources = [item["source"] for item in artifacts]
    if len(ids) != len(set(ids)):
        raise CatalogError("device-tree catalog contains duplicate logical IDs")
    if len(outputs) != len(set(outputs)):
        raise CatalogError("device-tree catalog contains duplicate outputs")
    if len(sources) != len(set(sources)):
        raise CatalogError("device-tree catalog contains duplicate sources")

    declarations = discover_makefile_outputs(root)
    camera_sources = discover_camera_sources(root)
    by_output = {item["output"]: item for item in artifacts}
    by_source = {item["source"]: item for item in artifacts}
    issues: list[str] = []
    for output, declaration in sorted(declarations.items()):
        if "camera-" in output.lower() and output not in by_output:
            issues.append(f"uncatalogued Makefile camera output {output}; run --scaffold")
        if "camera-" in output.lower() and not (root / declaration["source"]).is_file():
            issues.append(
                f"Makefile camera output {output} has no matching DTS {declaration['source']}"
            )
    for source, output in sorted(camera_sources.items()):
        if source not in by_source:
            issues.append(f"uncatalogued camera source {source}; run --scaffold")
    for artifact in artifacts:
        artifact_id = artifact["id"]
        expected_group = fragment_group(artifact)
        if artifact["catalogGroup"] != expected_group:
            issues.append(
                f"device-tree {artifact_id} must be stored in {expected_group!r} catalog "
                f"fragment, not {artifact['catalogGroup']!r}"
            )
        source_path = root / artifact["source"]
        if not source_path.is_file():
            issues.append(f"device-tree {artifact_id} source is missing: {artifact['source']}")
        declaration = declarations.get(artifact["output"])
        if artifact["makeVariable"] is None:
            if declaration is not None:
                issues.append(
                    f"device-tree {artifact_id} is sourceOnly without Makefile metadata, "
                    f"but {artifact['output']} is declared"
                )
        elif declaration is None:
            issues.append(
                f"stale device-tree catalog output {artifact['output']} is not declared by a Makefile"
            )
        else:
            for key in ("source", "makefile", "makeVariable"):
                if artifact[key] != declaration[key]:
                    issues.append(
                        f"device-tree {artifact_id} {key} mismatch: catalog={artifact[key]!r} "
                        f"source={declaration[key]!r}"
                    )
        inferred_platform = infer_platform(artifact["output"])
        if inferred_platform and inferred_platform not in artifact["platforms"]:
            issues.append(
                f"device-tree {artifact_id} filename implies platform {inferred_platform}; "
                f"catalog platforms={artifact['platforms']}"
            )
        inferred_camera = infer_camera(artifact["output"])
        if inferred_camera != "nvidia-reference" and artifact["camera"] != inferred_camera:
            issues.append(
                f"device-tree {artifact_id} filename implies camera {inferred_camera}; "
                f"catalog camera={artifact['camera']!r}"
            )
    if issues:
        raise CatalogError("\n".join(issues))

    normalized = [
        {
            key: value
            for key, value in item.items()
            if key not in {"catalogFragment", "catalogGroup"}
        }
        for item in sorted(artifacts, key=lambda value: value["id"])
    ]
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--scaffold", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.scaffold:
            print(json.dumps(scaffold(root), indent=2))
        else:
            digest = validate_repository(root)
            print(f"Camera device-tree artifact catalog OK: sha256:{digest}")
    except CatalogError as exc:
        print(f"Camera device-tree artifact catalog validation failed:\n{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
