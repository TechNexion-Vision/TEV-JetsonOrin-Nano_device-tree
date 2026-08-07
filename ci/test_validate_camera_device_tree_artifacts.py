import json
import tempfile
import unittest
from pathlib import Path

from ci import validate_camera_device_tree_artifacts as validator


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def artifact(output: str, *, platforms: list[str] | None = None) -> dict[str, object]:
    stem = Path(output).stem
    return {
        "id": "j401.vls-gm2.default",
        "type": "camera-overlay",
        "output": output,
        "source": f"overlay/{stem}.dts",
        "makefile": "overlay/Makefile",
        "makeVariable": "dtbo-y",
        "platforms": platforms if platforms is not None else ["j401"],
        "camera": "vls-gm2",
        "variant": "default",
        "lifecycle": "supported",
    }


def create_fixture(root: Path) -> None:
    output = "tegra234-p3767-camera-j401-vls-gm2-overlay.dtbo"
    (root / "overlay").mkdir(parents=True)
    (root / "overlay/Makefile").write_text(f"dtbo-y += {output}\n", encoding="utf-8")
    (root / f"overlay/{Path(output).stem}.dts").write_text("/dts-v1/;\n", encoding="utf-8")
    write_json(
        root / validator.INDEX_PATH,
        {
            "schemaVersion": 1,
            "kind": "camera-device-tree-artifact-index",
            "fragments": ["ci/camera-device-tree-artifacts/partners/j401.json"],
        },
    )
    write_json(
        root / "ci/camera-device-tree-artifacts/partners/j401.json",
        {
            "schemaVersion": 1,
            "kind": "camera-device-tree-artifact-fragment",
            "group": "partners/j401",
            "artifacts": [artifact(output)],
        },
    )


class DeviceTreeCatalogTests(unittest.TestCase):
    def test_official_and_partner_fragment_groups_are_taxonomy_scoped(self) -> None:
        self.assertEqual(
            validator.fragment_group({"platforms": ["orin-nano"]}),
            "official/orin-nano",
        )
        self.assertEqual(
            validator.fragment_group({"platforms": ["agx-orin"]}),
            "official/agx-orin",
        )
        self.assertEqual(
            validator.fragment_group({"platforms": ["j401"]}),
            "partners/j401",
        )
        self.assertEqual(
            validator.fragment_group({"platforms": ["x6-orin"]}),
            "partners/x6-orin",
        )
        self.assertEqual(
            validator.fragment_group({"platforms": ["tek-orin"]}),
            "partners/tek-orin",
        )
        self.assertEqual(validator.fragment_group({"platforms": []}), "shared")

    def test_current_branch_makefiles_dts_and_catalog_are_three_way_consistent(self) -> None:
        digest = validator.validate_repository(REPO_ROOT)

        self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_source_only_partner_overlays_use_overlay_file_names(self) -> None:
        partner_dir = REPO_ROOT / "ci/camera-device-tree-artifacts/partners"
        source_only_overlays = [
            artifact
            for fragment in partner_dir.glob("*.json")
            for artifact in json.loads(fragment.read_text(encoding="utf-8"))["artifacts"]
            if artifact["type"] == "camera-overlay" and artifact["lifecycle"] == "sourceOnly"
        ]

        self.assertGreater(len(source_only_overlays), 0)
        for artifact in source_only_overlays:
            with self.subTest(artifact=artifact["id"]):
                self.assertTrue(artifact["source"].endswith("-overlay.dts"))
                self.assertTrue(artifact["output"].endswith("-overlay.dtbo"))
                self.assertTrue((REPO_ROOT / artifact["source"]).is_file())

    def test_new_j401_source_without_makefile_or_catalog_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            source = root / "overlay/tegra234-p3767-camera-j401-vls-gm2-tunnel-overlay.dts"
            source.write_text("/dts-v1/;\n", encoding="utf-8")

            with self.assertRaisesRegex(validator.CatalogError, "uncatalogued camera source.*j401"):
                validator.validate_repository(root)

            pending = validator.scaffold(root)["artifacts"]
            self.assertEqual(pending[0]["id"], "j401.vls-gm2.tunnel")
            self.assertIsNone(pending[0]["makeVariable"])
            self.assertEqual(pending[0]["lifecycle"], "sourceOnly")

    def test_new_j401_makefile_output_without_catalog_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            output = "tegra234-p3767-camera-j401-vls-gm2-fsync-overlay.dtbo"
            with (root / "overlay/Makefile").open("a", encoding="utf-8") as handle:
                handle.write(f"dtbo-y += {output}\n")
            (root / f"overlay/{Path(output).stem}.dts").write_text("/dts-v1/;\n", encoding="utf-8")

            with self.assertRaisesRegex(validator.CatalogError, "uncatalogued Makefile camera output"):
                validator.validate_repository(root)

    def test_makefile_output_without_matching_dts_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            source = next((root / "overlay").glob("*.dts"))
            source.unlink()

            with self.assertRaisesRegex(validator.CatalogError, "has no matching DTS"):
                validator.validate_repository(root)

    def test_filename_platform_token_must_match_catalog_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            index_path = root / validator.INDEX_PATH
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["fragments"] = ["ci/camera-device-tree-artifacts/partners/x6-orin.json"]
            write_json(index_path, index)
            source = root / "ci/camera-device-tree-artifacts/partners/j401.json"
            fragment = json.loads(source.read_text(encoding="utf-8"))
            fragment["group"] = "partners/x6-orin"
            fragment["artifacts"][0]["platforms"] = ["x6-orin"]
            destination = root / "ci/camera-device-tree-artifacts/partners/x6-orin.json"
            write_json(destination, fragment)
            source.unlink()

            with self.assertRaisesRegex(validator.CatalogError, "implies platform j401"):
                validator.validate_repository(root)

    def test_catalog_fragment_group_must_match_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            index_path = root / validator.INDEX_PATH
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["fragments"] = ["ci/camera-device-tree-artifacts/partners/x6-orin.json"]
            write_json(index_path, index)
            source = root / "ci/camera-device-tree-artifacts/partners/j401.json"
            fragment = json.loads(source.read_text(encoding="utf-8"))
            fragment["group"] = "partners/x6-orin"
            destination = root / "ci/camera-device-tree-artifacts/partners/x6-orin.json"
            write_json(destination, fragment)
            source.unlink()

            with self.assertRaisesRegex(validator.CatalogError, "must be stored in 'partners/j401'"):
                validator.validate_repository(root)

    def test_fragment_path_must_match_declared_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            index_path = root / validator.INDEX_PATH
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["fragments"] = ["ci/camera-device-tree-artifacts/partners/misplaced.json"]
            write_json(index_path, index)
            source = root / "ci/camera-device-tree-artifacts/partners/j401.json"
            destination = root / "ci/camera-device-tree-artifacts/partners/misplaced.json"
            source.replace(destination)

            with self.assertRaisesRegex(validator.CatalogError, "fragment path.*group"):
                validator.validate_repository(root)

    def test_orphan_fragment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            write_json(root / "ci/camera-device-tree-artifacts/partners/orphan.json", {})

            with self.assertRaisesRegex(validator.CatalogError, "orphan device-tree catalog"):
                validator.validate_repository(root)

    def test_empty_fragment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            fragment_path = root / "ci/camera-device-tree-artifacts/partners/j401.json"
            fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
            fragment["artifacts"] = []
            write_json(fragment_path, fragment)

            with self.assertRaisesRegex(validator.CatalogError, "artifacts must not be empty"):
                validator.validate_repository(root)

    def test_unknown_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            create_fixture(root)
            index_path = root / validator.INDEX_PATH
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["schemaVersion"] = 2
            write_json(index_path, index)

            with self.assertRaisesRegex(validator.CatalogError, "unknown.*schemaVersion"):
                validator.validate_repository(root)


if __name__ == "__main__":
    unittest.main()
