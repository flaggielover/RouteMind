from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import path_safety


class WindowsContainmentTests(unittest.TestCase):
    def test_same_drive_repository_child_is_contained(self) -> None:
        self.assertTrue(
            path_safety.is_path_within_root(
                r"F:\Projects\RouteMind",
                r"F:\Projects\RouteMind\secrets\operator.key",
                flavor="windows",
            )
        )

    def test_same_drive_sibling_is_external(self) -> None:
        self.assertFalse(
            path_safety.is_path_within_root(
                r"F:\Projects\RouteMind",
                r"F:\Projects\RouteMind-Secrets\operator.key",
                flavor="windows",
            )
        )

    def test_different_drive_is_external(self) -> None:
        self.assertFalse(
            path_safety.is_path_within_root(
                r"F:\Projects\RouteMind",
                r"C:\Users\operator\.secrets\operator.key",
                flavor="windows",
            )
        )

    def test_parent_traversal_normalizes_back_into_repository(self) -> None:
        self.assertTrue(
            path_safety.is_path_within_root(
                r"F:\Projects\RouteMind",
                r"F:\Projects\RouteMind\outside\..\secrets\operator.key",
                flavor="windows",
            )
        )

    def test_case_and_trailing_separator_preserve_boundary(self) -> None:
        self.assertTrue(
            path_safety.is_path_within_root(
                "f:\\projects\\routemind\\",
                r"F:\PROJECTS\ROUTEMIND\secrets\operator.key",
                flavor="windows",
            )
        )
        self.assertFalse(
            path_safety.is_path_within_root(
                "f:\\projects\\routemind\\",
                r"F:\PROJECTS\ROUTEMIND-other\operator.key",
                flavor="windows",
            )
        )

    def test_unc_boundaries_are_segment_aware(self) -> None:
        self.assertTrue(
            path_safety.is_path_within_root(
                r"\\server\share\RouteMind",
                r"\\SERVER\SHARE\RouteMind\secrets\operator.key",
                flavor="windows",
            )
        )
        self.assertFalse(
            path_safety.is_path_within_root(
                r"\\server\share\RouteMind",
                r"\\server\share\RouteMind-Secrets\operator.key",
                flavor="windows",
            )
        )
        self.assertFalse(
            path_safety.is_path_within_root(
                r"\\server\share\RouteMind",
                r"\\server\other\operator.key",
                flavor="windows",
            )
        )

    def test_device_namespace_is_rejected_fail_closed(self) -> None:
        with self.assertRaises(path_safety.PathSafetyError):
            path_safety.is_path_within_root(
                r"F:\Projects\RouteMind",
                r"\\?\C:\secrets\operator.key",
                flavor="windows",
            )


class ExistingFileSafetyTests(unittest.TestCase):
    def test_repository_child_rejected_and_sibling_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = base / "RouteMind"
            repository.mkdir()
            inside = repository / "operator.key"
            outside = base / "RouteMind-Secrets" / "operator.key"
            inside.write_text("fixture", encoding="ascii")
            outside.parent.mkdir()
            outside.write_text("fixture", encoding="ascii")

            with self.assertRaisesRegex(path_safety.PathSafetyError, "inside_root"):
                path_safety.assert_external_regular_file(repository, inside)
            path_safety.assert_external_regular_file(repository, outside)

    def test_symlink_or_junction_redirect_is_rejected_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = base / "RouteMind"
            target = base / "target"
            redirect = base / "redirect"
            repository.mkdir()
            target.mkdir()
            (target / "operator.key").write_text("fixture", encoding="ascii")
            self._create_directory_redirect(redirect, target)
            try:
                with self.assertRaisesRegex(
                    path_safety.PathSafetyError, "redirect_not_allowed"
                ):
                    path_safety.assert_external_regular_file(
                        repository, redirect / "operator.key"
                    )
            finally:
                redirect.rmdir()

    @staticmethod
    def _create_directory_redirect(link: Path, target: Path) -> None:
        if os.name != "nt":
            link.symlink_to(target, target_is_directory=True)
            return
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError("Unable to create a bounded junction test fixture")


if __name__ == "__main__":
    unittest.main()
