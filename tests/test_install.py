"""Real temporary-project behavior for the project-only installer."""

import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("eight_honors_install", PACKAGE / "scripts" / "install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def snapshot(root):
    """Include directories and exact bytes, not only output messages."""
    return {path.relative_to(root).as_posix(): None if path.is_dir() else path.read_bytes()
            for path in root.rglob("*")}


def archive(extra=(), omit=()):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name in installer.RUNTIME_FILES:
            if name not in omit:
                zipped.writestr("repo-main/" + name, (PACKAGE / name).read_bytes())
        for name, data in extra:
            if isinstance(name, str):
                entry = zipfile.ZipInfo("placeholder")
                entry.filename = entry.orig_filename = name
            else:
                entry = name
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                zipped.writestr(entry, data)
    return stream.getvalue()


class ProjectInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.rules = self.project / "AGENTS.md"
        self.skill = self.project / ".agents" / "skills" / "eight-honors"

    def install(self, **kwargs):
        return installer.install(self.project, PACKAGE, **kwargs)

    def import_runtime(self, optimization=""):
        command = [sys.executable, "-I"]
        if optimization:
            command.append(optimization)
        command.extend(["-c", "import sys;sys.path.insert(0,sys.argv[1]);"
                        "import check_codex_quota,codex_quota_workflow", str(self.skill / "scripts")])
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        cache = self.skill / "scripts" / "__pycache__"
        self.assertTrue(cache.is_dir(), "The subprocess must really generate bytecode")
        return cache

    def test_new_install_has_runtime_only_and_a_single_managed_block(self):
        result = self.install()
        self.assertTrue(result["changed"])
        self.assertIsNone(result["backup_path"])
        self.assertEqual({name for name, data in snapshot(self.skill).items() if data is not None},
                         set(installer.RUNTIME_FILES) | {installer.MANIFEST})
        for name in installer.RUNTIME_FILES:
            self.assertEqual((self.skill / name).read_bytes(), (PACKAGE / name).read_bytes())
        self.assertEqual(self.rules.read_bytes().count(installer.START), 1)
        self.assertFalse((self.project / ".eight-honors-install.lock").exists())
        self.assertFalse(list(self.project.glob(".eight-honors-stage-*")))

    def test_existing_rules_and_backup_keep_exact_original_bytes(self):
        original = "# 私有规则\nKeep existing OMX markers.\n<!-- OMX:TEAM:WORKER:START -->\n".encode("utf-8")
        self.rules.write_bytes(original)
        result = self.install()
        self.assertTrue(self.rules.read_bytes().startswith(original))
        backup = Path(result["backup_path"])
        self.assertEqual((backup / "AGENTS.md").read_bytes(), original)
        self.assertEqual((backup.parent / ".gitignore").read_bytes(), b"*\n")
        if os.name == "nt":
            self.assertTrue(backup.parent.stat().st_file_attributes & 2)
        else:
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)

    def test_repeat_is_byte_identical_and_creates_no_new_backup(self):
        self.rules.write_text("Existing rules\n", encoding="utf-8")
        self.install()
        before = snapshot(self.project)
        self.assertFalse(self.install()["changed"])
        self.assertEqual(snapshot(self.project), before)

    def test_replaces_same_block_without_touching_bytes_on_either_side(self):
        prefix = b"\xef\xbb\xbf# Existing\r\n\r\n"
        suffix = b"\r\n\r\n# Retained suffix\r\n"
        self.rules.write_bytes(prefix + installer.START + b"\r\nOld managed rule\r\n" + installer.END + suffix)
        original = self.rules.read_bytes()
        result = self.install()
        after = self.rules.read_bytes()
        self.assertTrue(after.startswith(prefix))
        self.assertTrue(after.endswith(suffix))
        self.assertEqual(after.count(installer.START), 1)
        self.assertNotIn(b"Old managed rule", after)
        self.assertNotIn(b"\n", after.replace(b"\r\n", b""))
        self.assertEqual((Path(result["backup_path"]) / "AGENTS.md").read_bytes(), original)
        self.assertFalse(self.install()["changed"])

    def test_appending_preserves_utf8_bom_and_crlf(self):
        original = b"\xef\xbb\xbf" + "原有约定\r\n最后一行".encode("utf-8")
        self.rules.write_bytes(original)
        self.install()
        result = self.rules.read_bytes()
        self.assertTrue(result.startswith(original + b"\r\n\r\n"))
        self.assertEqual(result.count(b"\xef\xbb\xbf"), 1)
        self.assertNotIn(b"\n", result.replace(b"\r\n", b""))

    def test_malformed_or_multiple_blocks_refuse_before_writing(self):
        candidates = [installer.START, installer.END + b"\n" + installer.START,
                      installer.START + b"\n" + installer.END + b"\n" + installer.START + b"\n" + installer.END,
                      b"prefix " + installer.START + b"\n" + installer.END,
                      b"<!-- EIGHT-HONORS:START-- >\n"]
        for raw in candidates:
            with self.subTest(raw=raw):
                self.rules.write_bytes(raw)
                before = snapshot(self.project)
                with self.assertRaises(installer.InstallError):
                    self.install()
                self.assertEqual(snapshot(self.project), before)

    def test_existing_custom_install_is_never_overwritten(self):
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("My own skill", encoding="utf-8")
        before = snapshot(self.project)
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(snapshot(self.project), before)

    def test_owned_install_with_local_changes_or_extra_files_is_refused(self):
        self.install()
        target = self.skill / "SKILL.md"
        original = target.read_bytes()
        for change in ("modified", "extra"):
            with self.subTest(change=change):
                if change == "modified":
                    target.write_bytes(original + b"\nLocal customization\n")
                else:
                    target.write_bytes(original)
                    (self.skill / "private.txt").write_text("Keep me", encoding="utf-8")
                before = snapshot(self.project)
                with self.assertRaises(installer.InstallError):
                    self.install()
                self.assertEqual(snapshot(self.project), before)

    def test_real_import_caches_are_preserved_on_unchanged_reinstall(self):
        self.install()
        cache = self.import_runtime()
        self.import_runtime("-O")
        self.import_runtime("-OO")
        self.assertEqual(len(list(cache.glob("*.pyc"))), 6)
        before = snapshot(self.project)
        self.assertFalse(self.install()["changed"])
        self.assertEqual(snapshot(self.project), before)

    def test_real_import_caches_are_backed_up_and_replaced_on_upgrade(self):
        self.install()
        cache = self.import_runtime()
        caches = snapshot(cache)
        source = self.root / "updated-source"
        for name in installer.RUNTIME_FILES:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((PACKAGE / name).read_bytes())
        (source / "SKILL.md").write_bytes((PACKAGE / "SKILL.md").read_bytes() + b"\nNew release.\n")
        result = installer.install(self.project, source)
        self.assertTrue(result["skill_changed"])
        self.assertFalse(cache.exists())
        backup_cache = Path(result["backup_path"]) / "skill" / "scripts" / "__pycache__"
        self.assertEqual(snapshot(backup_cache), caches)
        self.assertFalse(installer.install(self.project, source)["changed"])

    def test_real_import_caches_survive_rules_only_update(self):
        self.install()
        cache = self.import_runtime()
        caches = snapshot(cache)
        self.rules.write_bytes(self.rules.read_bytes().replace(installer.START, installer.START + b"\nOld rule."))
        result = self.install()
        self.assertFalse(result["skill_changed"])
        self.assertTrue(result["rules_changed"])
        self.assertEqual(snapshot(cache), caches)

    def test_unknown_files_in_cache_directory_are_still_refused(self):
        self.install()
        cache = self.import_runtime()
        unknown = ["notes.txt", "other.cpython-312.pyc", "check_codex_quota.pypy-312.pyc",
                   "check_codex_quota.cpython-312.pyc.old", "check_codex_quota.cpython-312.opt-x.pyc",
                   "check_codex_quota.cpython-312.opt-1.pyc.private"]
        for name in unknown:
            with self.subTest(name=name):
                path = cache / name
                path.write_bytes(b"User content must survive")
                before = snapshot(self.project)
                with self.assertRaises(installer.InstallError):
                    self.install()
                self.assertEqual(snapshot(self.project), before)
                path.unlink()

    def test_cache_directory_symlink_or_junction_is_refused(self):
        self.install()
        outside = self.root / "outside-cache"
        outside.mkdir()
        cache = self.skill / "scripts" / "__pycache__"
        try:
            cache.symlink_to(outside, target_is_directory=True)
            remove = cache.unlink
        except (OSError, NotImplementedError):
            if os.name != "nt":
                self.skipTest("OS does not permit creating a cache symlink")
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(cache), str(outside)],
                                    capture_output=True)
            if result.returncode != 0:
                self.skipTest("OS does not permit creating a cache junction")
            remove = cache.rmdir
        try:
            with self.assertRaisesRegex(installer.InstallError, "links/reparse"):
                self.install()
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            remove()

    def test_dry_run_with_or_without_existing_rules_does_zero_writes(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    self.rules.write_text("Keep me\n", encoding="utf-8")
                before = snapshot(self.project)
                self.assertTrue(self.install(dry_run=True)["changed"])
                self.assertEqual(snapshot(self.project), before)

    def test_override_file_causes_explicit_refusal_and_zero_writes(self):
        (self.project / "AGENTS.override.md").write_text("Higher priority", encoding="utf-8")
        before = snapshot(self.project)
        with self.assertRaisesRegex(installer.InstallError, "AGENTS.override.md"):
            self.install()
        self.assertEqual(snapshot(self.project), before)

    def test_invalid_utf8_rules_are_not_silently_reencoded(self):
        self.rules.write_bytes(b"\xff\xfeother encoding")
        before = snapshot(self.project)
        with self.assertRaisesRegex(installer.InstallError, "not UTF-8"):
            self.install()
        self.assertEqual(snapshot(self.project), before)

    def test_rule_replace_failure_rolls_back_new_skill_and_leaves_original_rules(self):
        self.rules.write_bytes(b"Original rules\r\n")
        original_replace = installer.os.replace

        def fail_rules(source, target):
            if Path(target) == self.rules:
                raise OSError("simulated rules replacement failure")
            return original_replace(source, target)

        with patch.object(installer.os, "replace", side_effect=fail_rules), \
                self.assertRaisesRegex(installer.InstallError, "previous rules and skill restored"):
            self.install()
        self.assertEqual(self.rules.read_bytes(), b"Original rules\r\n")
        self.assertFalse(self.skill.exists())
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".eight-honors-install.lock").exists())
        self.assertFalse(list(self.project.glob(".eight-honors-stage-*")))

    def test_readback_failure_after_rules_replacement_restores_original(self):
        self.rules.write_bytes(b"Original rules\n")
        original_read = installer._read_file
        failed = False

        def fail_readback(path, *args, **kwargs):
            nonlocal failed
            data = original_read(path, *args, **kwargs)
            if path == self.rules and installer.START in data and not failed:
                failed = True
                raise OSError("simulated readback failure after rules were replaced")
            return data

        with patch.object(installer, "_read_file", side_effect=fail_readback), \
                self.assertRaisesRegex(installer.InstallError, "previous rules and skill restored"):
            self.install()
        self.assertTrue(failed)
        self.assertEqual(self.rules.read_bytes(), b"Original rules\n")
        self.assertFalse(self.skill.exists())

    def test_failing_first_install_with_no_rules_leaves_no_installed_files(self):
        before = snapshot(self.project)
        original_replace = installer.os.replace

        def fail_rules(source, target):
            if Path(target) == self.rules:
                raise OSError("simulated rules replacement failure")
            return original_replace(source, target)

        with patch.object(installer.os, "replace", side_effect=fail_rules), \
                self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(snapshot(self.project), before)

    def test_upgrade_failure_restores_the_old_owned_skill(self):
        self.install()
        self.import_runtime()
        original_skill = snapshot(self.skill)
        original_rules = self.rules.read_bytes()
        source = self.root / "updated-source"
        for name in installer.RUNTIME_FILES:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((PACKAGE / name).read_bytes())
        with (source / "SKILL.md").open("ab") as stream:
            stream.write(b"\nUpdated release.\n")
        fragment = source / "references" / "AGENTS.fragment.md"
        fragment.write_bytes(fragment.read_bytes().replace(installer.START, installer.START + b"\nNew rule."))
        original_replace = installer.os.replace

        def fail_rules(source_path, target):
            if Path(target) == self.rules:
                raise OSError("simulated rules replacement failure")
            return original_replace(source_path, target)

        with patch.object(installer.os, "replace", side_effect=fail_rules), \
                self.assertRaises(installer.InstallError):
            installer.install(self.project, source)
        self.assertEqual(snapshot(self.skill), original_skill)
        self.assertEqual(self.rules.read_bytes(), original_rules)
        backups = list((self.project / ".eight-honors-backups").glob("*/skill/SKILL.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original_skill["SKILL.md"])

    def test_successful_owned_upgrade_backs_up_old_runtime(self):
        self.install()
        source = self.root / "updated-source"
        for name in installer.RUNTIME_FILES:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((PACKAGE / name).read_bytes())
        (source / "SKILL.md").write_bytes((PACKAGE / "SKILL.md").read_bytes() + b"\nUpdated release.\n")
        result = installer.install(self.project, source)
        self.assertTrue(result["skill_changed"])
        self.assertFalse(result["rules_changed"])
        self.assertEqual((Path(result["backup_path"]) / "skill" / "SKILL.md").read_bytes(),
                         (PACKAGE / "SKILL.md").read_bytes())
        self.assertTrue((self.skill / "SKILL.md").read_bytes().endswith(b"Updated release.\n"))

    def test_existing_lock_is_preserved(self):
        lock = self.project / ".eight-honors-install.lock"
        lock.write_text("Existing writer", encoding="utf-8")
        before = snapshot(self.project)
        with self.assertRaisesRegex(installer.InstallError, "lock exists"):
            self.install()
        self.assertEqual(snapshot(self.project), before)

    def test_claude_uses_its_project_paths(self):
        result = self.install(agent="claude")
        self.assertTrue((self.project / "CLAUDE.md").is_file())
        self.assertTrue((self.project / ".claude" / "skills" / "eight-honors" / "SKILL.md").is_file())
        self.assertFalse(self.rules.exists())
        self.assertFalse((self.project / ".agents").exists())
        self.assertTrue(result["changed"])

    def test_runs_as_downloaded_code_without_file_using_current_project(self):
        command = [sys.executable, "-B", "-c",
                   "import sys;exec(compile(sys.stdin.read(),'<downloaded-installer>','exec'))",
                   "--source", str(PACKAGE), "--dry-run"]
        before = snapshot(self.project)
        result = subprocess.run(command, input=(PACKAGE / "scripts" / "install.py").read_text(encoding="utf-8"),
                                cwd=self.project, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run", result.stdout)
        self.assertEqual(snapshot(self.project), before)

    def test_cli_file_invocation_installs_into_explicit_project(self):
        result = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts" / "install.py"),
                                 "--project", str(self.project), "--source", str(PACKAGE)],
                                cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.rules), result.stdout)
        self.assertTrue(self.rules.is_file())

    def test_local_symlink_source_and_destination_are_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        linked = self.project / ".agents"
        def link_directory(path, target):
            try:
                path.symlink_to(target, target_is_directory=True)
                return path.unlink
            except (OSError, NotImplementedError):
                if os.name == "nt":
                    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(target)],
                                            capture_output=True)
                    if result.returncode == 0:
                        return path.rmdir
                self.skipTest("OS does not permit creating symlinks or junctions")

        remove = link_directory(linked, outside)
        with self.assertRaisesRegex(installer.InstallError, "links/reparse"):
            self.install()
        self.assertEqual(list(outside.iterdir()), [])
        remove()
        linked_source = self.root / "linked-source"
        remove_source = link_directory(linked_source, PACKAGE)
        try:
            with self.assertRaisesRegex(installer.InstallError, "links/reparse"):
                installer.install(self.project, linked_source)
        finally:
            remove_source()


class ArchiveTests(unittest.TestCase):
    def test_archive_runtime_is_read_without_extracting_files(self):
        files = installer._archive_files(archive())
        self.assertEqual(set(files), set(installer.RUNTIME_FILES))
        self.assertEqual(files["SKILL.md"], (PACKAGE / "SKILL.md").read_bytes())

    def test_traversal_absolute_windows_paths_and_duplicate_entries_are_refused(self):
        names = ["repo-main/../escape", "/absolute", "C:/escape", "repo-main\\escape",
                 "repo-main/./escape", "repo-main//escape", "repo-main/SKILL.md",
                 "repo-main/skill.md"]
        for name in names:
            with self.subTest(name=name), self.assertRaises(installer.InstallError):
                installer._archive_files(archive([(name, b"bad")]))

    def test_zip_symlinks_and_special_files_are_refused(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO):
            link = zipfile.ZipInfo("repo-main/link")
            link.create_system = 3
            link.external_attr = (kind | 0o777) << 16
            with self.subTest(kind=kind), self.assertRaisesRegex(installer.InstallError, "link or special"):
                installer._archive_files(archive([(link, b"../../outside")]))

    def test_missing_files_multiple_roots_and_oversized_data_are_refused(self):
        candidates = [archive(omit=("SKILL.md",)), archive([("second-root/file", b"x")]), b"not a zip"]
        for payload in candidates:
            with self.subTest(length=len(payload)), self.assertRaises(installer.InstallError):
                installer._archive_files(payload)
        with patch.object(installer, "MAX_DOWNLOAD", 1), self.assertRaises(installer.InstallError):
            installer._archive_files(archive())
        with patch.object(installer, "MAX_EXPANDED", 1), self.assertRaises(installer.InstallError):
            installer._archive_files(archive())

    def test_remote_dry_run_uses_same_archive_validation_and_zero_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            before = snapshot(project)
            with patch.object(installer, "_download", return_value=archive()):
                self.assertTrue(installer.install(project, dry_run=True)["changed"])
            self.assertEqual(snapshot(project), before)

    def test_downloader_rejects_oversized_stream_or_untrusted_redirect(self):
        class Response(io.BytesIO):
            headers = {}

            def geturl(self):
                return "https://codeload.github.com/owner/repo/zip/main"

        with patch.object(installer, "MAX_DOWNLOAD", 16), \
                patch.object(installer.urllib.request, "urlopen", return_value=Response(b"x" * 17)), \
                self.assertRaisesRegex(installer.InstallError, "size limit"):
            installer._download()
        response = Response(b"archive")
        response.geturl = lambda: "https://untrusted.example/archive.zip"
        with patch.object(installer.urllib.request, "urlopen", return_value=response), \
                self.assertRaisesRegex(installer.InstallError, "outside GitHub"):
            installer._download()


if __name__ == "__main__":
    unittest.main()
