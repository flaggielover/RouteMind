from __future__ import annotations

import argparse
import ntpath
import os
import posixpath
import stat
import sys
from pathlib import Path
from typing import Literal

PathFlavor = Literal["windows", "posix"]


class PathSafetyError(ValueError):
    pass


def _path_module(flavor: PathFlavor):  # type: ignore[no-untyped-def]
    return ntpath if flavor == "windows" else posixpath


def normalize_absolute_path(
    path: str | os.PathLike[str], *, flavor: PathFlavor
) -> str:
    raw = os.fspath(path)
    if not raw or "\x00" in raw:
        raise PathSafetyError("invalid_path")
    if flavor == "windows" and raw.replace("/", "\\").startswith(
        ("\\\\?\\", "\\\\.\\")
    ):
        raise PathSafetyError("device_namespace_not_supported")
    path_module = _path_module(flavor)
    normalized = path_module.normpath(raw)
    if not path_module.isabs(normalized):
        raise PathSafetyError("absolute_path_required")
    if flavor == "windows":
        drive, tail = ntpath.splitdrive(normalized)
        if not drive or not tail.startswith(("\\", "/")):
            raise PathSafetyError("absolute_path_required")
    return normalized


def is_path_within_root(
    root: str | os.PathLike[str],
    candidate: str | os.PathLike[str],
    *,
    flavor: PathFlavor,
) -> bool:
    path_module = _path_module(flavor)
    normalized_root = normalize_absolute_path(root, flavor=flavor)
    normalized_candidate = normalize_absolute_path(candidate, flavor=flavor)
    try:
        common = path_module.commonpath([normalized_root, normalized_candidate])
    except ValueError:
        return False
    return path_module.normcase(common) == path_module.normcase(normalized_root)


def _is_redirect(path: Path) -> bool:
    metadata = path.lstat()
    file_attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    is_junction = bool(getattr(os.path, "isjunction", lambda _: False)(path))
    return path.is_symlink() or is_junction or bool(file_attributes & reparse_flag)


def _assert_no_redirects(path: Path) -> None:
    current = path
    while True:
        if _is_redirect(current):
            raise PathSafetyError("redirect_not_allowed")
        parent = current.parent
        if parent == current:
            return
        current = parent


def assert_external_regular_file(
    root: str | os.PathLike[str], candidate: str | os.PathLike[str]
) -> None:
    normalized_root = Path(os.path.abspath(os.fspath(root)))
    normalized_candidate = Path(os.path.abspath(os.fspath(candidate)))
    flavor: PathFlavor = "windows" if os.name == "nt" else "posix"
    normalize_absolute_path(normalized_root, flavor=flavor)
    normalize_absolute_path(normalized_candidate, flavor=flavor)
    if not normalized_root.is_dir():
        raise PathSafetyError("root_directory_missing")
    if not normalized_candidate.is_file():
        raise PathSafetyError("candidate_file_missing")
    _assert_no_redirects(normalized_candidate)

    resolved_root = Path(os.path.realpath(normalized_root))
    resolved_candidate = Path(os.path.realpath(normalized_candidate))
    if os.path.normcase(str(resolved_candidate)) != os.path.normcase(
        str(normalized_candidate)
    ):
        raise PathSafetyError("redirect_not_allowed")
    if is_path_within_root(resolved_root, resolved_candidate, flavor=flavor):
        raise PathSafetyError("inside_root")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", required=True)
    parser.add_argument("--candidate-env", required=True)
    arguments = parser.parse_args()
    candidate = os.environ.get(arguments.candidate_env, "")
    try:
        assert_external_regular_file(arguments.root, candidate)
    except (OSError, PathSafetyError):
        print("external_path_validation_failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
