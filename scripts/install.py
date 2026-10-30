#!/usr/bin/env python3
"""Install eight-honors into one project. Python 3.9+, standard library only.

This file also runs through stdin or exec(), without a local checkout/__file__.
Only the runtime allowlist is installed; existing custom installations are refused.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile


REPOSITORY = "Cyh29hao/new-eight-honors-skill"
ARCHIVE_URL = "https://codeload.github.com/" + REPOSITORY + "/zip/refs/heads/main"
RUNTIME_FILES = (
    "SKILL.md", "LICENSE", "agents/openai.yaml",
    "references/AGENTS.fragment.md", "references/reporting.md",
    "references/quota-and-recovery.md", "scripts/check_codex_quota.py",
    "scripts/codex_quota_workflow.py",
)
MANIFEST = ".eight-honors-install.json"
OWNER = "eight-honors-project-installer"
START = b"<!-- EIGHT-HONORS:START -->"
END = b"<!-- EIGHT-HONORS:END -->"
MAX_DOWNLOAD = 12 * 1024 * 1024
MAX_EXPANDED = 32 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
MAX_RUNTIME = 2 * 1024 * 1024
CACHE_PATH = re.compile(
    r"scripts/__pycache__/(?:check_codex_quota|codex_quota_workflow)"
    r"\.cpython-[0-9]{2,3}(?:\.opt-[0-9]+)?\.pyc\Z"
)
PREFERENCE_PREFIX = "<!-- eight-honors-preferences: "
DEFAULT_PREFERENCES = {
    "quota_mode": "auto", "report_mode": "full", "tone": "direct",
    "five_hour_closeout_percent": 30.0,
}
PREFERENCE_CHOICES = {
    "quota_mode": ("auto", "subscription", "api", "off"),
    "report_mode": ("full", "milestones", "concise"),
    "tone": ("direct", "neutral"),
}


class InstallError(Exception):
    """A safe refusal or an installation failure."""


def _no_links(path):
    """Check lexical ancestors too: resolve() alone would hide symlinks."""
    for part in reversed((path,) + tuple(path.parents)):
        try:
            details = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(details.st_mode) or (
                getattr(details, "st_file_attributes", 0) & 0x400):
            raise InstallError("Symbolic links/reparse points are not supported: " + str(part))


def _absolute(path):
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _read_file(path, limit=MAX_RUNTIME):
    _no_links(path)
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise InstallError("Expected a regular file: " + str(path))
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise InstallError("File exceeds the size limit: " + str(path))
    return data


def _download():
    request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": OWNER})
    deadline = time.monotonic() + 60
    chunks, size = [], 0
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            final = urllib.parse.urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname != "codeload.github.com":
                raise InstallError("Download redirected outside GitHub codeload.")
            length = response.headers.get("Content-Length")
            if length is not None and (not length.isdecimal() or int(length) > MAX_DOWNLOAD):
                raise InstallError("Archive exceeds the download size limit.")
            while True:
                if time.monotonic() > deadline:
                    raise InstallError("Archive download exceeded its 60-second deadline.")
                chunk = response.read(min(65536, MAX_DOWNLOAD + 1 - size))
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_DOWNLOAD:
                    raise InstallError("Archive exceeds the download size limit.")
    except (OSError, urllib.error.URLError) as exc:
        raise InstallError("Could not download the public main branch: " + str(exc)) from exc


def _archive_files(payload):
    """Validate every ZIP entry; read allowed files in memory, never extractall()."""
    if len(payload) > MAX_DOWNLOAD:
        raise InstallError("Archive exceeds the download size limit.")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > 1024:
                raise InstallError("Empty archive or too many archive entries.")
            roots, seen, total = set(), set(), 0
            for entry in entries:
                # zipfile normalizes backslashes on Windows and truncates NULs.
                # Inspect the original name before trusting that normalization.
                name = entry.orig_filename.rstrip("/")
                parts = name.split("/")
                kind = stat.S_IFMT(entry.external_attr >> 16)
                if (entry.orig_filename != entry.filename or not name
                        or "\\" in name or ":" in name or "\x00" in name
                        or any(part in ("", ".", "..") for part in parts)
                        or PurePosixPath(name).is_absolute()):
                    raise InstallError("Unsafe archive path: " + repr(entry.filename))
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise InstallError("Archive contains a link or special file: " + name)
                if name.casefold() in seen:
                    raise InstallError("Duplicate archive path: " + name)
                seen.add(name.casefold())
                roots.add(parts[0])
                total += entry.file_size
                if entry.file_size > MAX_MEMBER or total > MAX_EXPANDED or entry.flag_bits & 1:
                    raise InstallError("Oversized or encrypted archive entry: " + name)
            if len(roots) != 1:
                raise InstallError("Expected one repository directory in the archive.")
            prefix = next(iter(roots)) + "/"
            result = {}
            for name in RUNTIME_FILES:
                try:
                    with archive.open(prefix + name) as stream:
                        result[name] = stream.read(MAX_RUNTIME + 1)
                except KeyError as exc:
                    raise InstallError("Missing runtime file in archive: " + name) from exc
            return result
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise InstallError("Invalid repository archive: " + str(exc)) from exc


def _block_span(data):
    starts, ends = data.count(START), data.count(END)
    if not starts and not ends and b"EIGHT-HONORS:" not in data:
        return None
    if starts != 1 or ends != 1 or data.count(b"EIGHT-HONORS:") != 2:
        raise InstallError("Malformed or multiple EIGHT-HONORS marker blocks; merge manually.")
    first, last = data.index(START), data.index(END)
    for position, marker in ((first, START), (last, END)):
        before = data[:position]
        after = data[position + len(marker):]
        if ((before and not before.endswith((b"\n", b"\r")) and before != b"\xef\xbb\xbf")
                or (after and after[:1] not in (b"\n", b"\r"))):
            raise InstallError("EIGHT-HONORS markers must occupy complete lines.")
    if first >= last:
        raise InstallError("EIGHT-HONORS end marker precedes its start marker.")
    return first, last + len(END)


def _validate_runtime(files):
    if set(files) != set(RUNTIME_FILES) or sum(map(len, files.values())) > MAX_RUNTIME:
        raise InstallError("Runtime files are incomplete or exceed the 2 MiB limit.")
    for name, data in files.items():
        try:
            if not data:
                raise ValueError("empty file")
            data.decode("utf-8-sig")
        except (UnicodeError, ValueError) as exc:
            raise InstallError("Runtime file is empty or not UTF-8: " + name) from exc
    skill = files["SKILL.md"].decode("utf-8-sig").replace("\r\n", "\n")
    if not skill.startswith("---\n") or not re.search(r"(?m)^name: *eight-honors *$", skill):
        raise InstallError("SKILL.md does not identify the eight-honors skill.")
    fragment = files["references/AGENTS.fragment.md"]
    span = _block_span(fragment)
    if span is None:
        raise InstallError("The rule fragment has no managed marker block.")
    return fragment[span[0]:span[1]]


def _merge_rules(original, fragment):
    try:
        original.decode("utf-8-sig")
    except UnicodeError as exc:
        raise InstallError("The existing rules file is not UTF-8; convert it explicitly first.") from exc
    newline = re.search(rb"\r\n|\n|\r", original)
    newline = newline.group() if newline else b"\n"
    block = fragment.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", newline)
    span = _block_span(original)
    if span:
        return original[:span[0]] + block + original[span[1]:]
    separator = b"" if not original or original == b"\xef\xbb\xbf" else (
        newline if original.endswith((b"\n", b"\r")) else newline + newline)
    return original + separator + block + newline


def _preference_overrides(quota_mode=None, report_mode=None, tone=None,
                          five_hour_closeout_percent=None):
    provided = {"quota_mode": quota_mode, "report_mode": report_mode, "tone": tone,
                "five_hour_closeout_percent": five_hour_closeout_percent}
    result = {}
    for key, value in provided.items():
        if value is None:
            continue
        if key in PREFERENCE_CHOICES:
            if value not in PREFERENCE_CHOICES[key]:
                raise InstallError("Invalid %s: choose %s" % (key, ", ".join(PREFERENCE_CHOICES[key])))
        elif (type(value) not in (int, float) or not math.isfinite(value)
              or not 0 <= value <= 100):
            raise InstallError("five_hour_closeout_percent must be a finite number from 0 to 100")
        else:
            value = float(value)
        result[key] = value
    return result


def _saved_preferences(original):
    """Read only this installer's known settings from its managed rule block."""
    span = _block_span(original)
    if span is None:
        return {}
    try:
        block = original[span[0]:span[1]].decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeError as exc:
        raise InstallError("The existing rules file is not UTF-8; convert it explicitly first.") from exc
    count = block.count(PREFERENCE_PREFIX)
    if count == 0:
        return {}
    match = re.search(r"(?m)^" + re.escape(PREFERENCE_PREFIX) + r"(.+) -->$", block)
    if count != 1 or match is None:
        raise InstallError("Malformed or duplicate saved preferences; review the managed rule block.")
    try:
        saved = json.loads(match.group(1))
        if not isinstance(saved, dict) or set(saved) != set(DEFAULT_PREFERENCES):
            raise ValueError("Unknown preference keys")
        validated = _preference_overrides(**saved)
        if set(validated) != set(DEFAULT_PREFERENCES):
            raise ValueError("Missing preference value")
        # The visible setting values are the editing surface. The JSON comment is
        # installer metadata, not a second choice that silently defeats hand edits.
        visible = {}
        for key in PREFERENCE_CHOICES:
            matches = re.findall(r"(?m)^- [^\n]*（`" + re.escape(key) + r"=([^`]+)`）：", block)
            if len(matches) != 1:
                raise ValueError("Missing or duplicate visible preference")
            visible[key] = matches[0]
        reserves = re.findall(r"(?m)^- 计划预留线：五小时(?:剩余|等效余量) ([^%\n]+)%", block)
        if len(reserves) != 1:
            raise ValueError("Missing or duplicate visible reserve")
        visible["five_hour_closeout_percent"] = float(reserves[0])
        return _preference_overrides(**visible)
    except (TypeError, ValueError) as exc:
        raise InstallError("Invalid saved preferences; review the managed rule block.") from exc


def _personalized_fragment(fragment, preferences):
    """Keep runtime sources generic; project choices belong in project guidance."""
    text = fragment.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    quota = preferences["quota_mode"]
    threshold = "%g" % preferences["five_hour_closeout_percent"]
    quota_text = {
        "auto": "自动核对当前连接方式；确认是 ChatGPT 计划才用真实计划额度。API/中转或来源未明时按阶段保存、交接。",
        "subscription": "使用 ChatGPT 计划；核实当前连接和额度来源后按真实余额收尾。",
        "api": "使用 API/中转；跳过 ChatGPT 计划百分比判断，按阶段保存成果和下一步；有服务商真实预算时按其口径执行。",
        "off": "仅做阶段保存与交接，不自动查询计划额度；按本次时间、预算和停止要求收尾。",
    }[quota]
    report_text = {
        "full": "每份工作报告先写正常正文，末尾附完整八条；纯问答和闲聊省略附录。",
        "milestones": "日常进度简报写发现、问题和下一步；阶段结束、最终交付与中断收尾再附完整八条。",
        "concise": "以简洁正常正文交代结果、依据、缺口和下一步；仅在用户要求或确有解释需要时展开八条。",
    }[preferences["report_mode"]]
    tone_text = {
        "direct": "直接自然地表达，先给判断、方案和可执行建议；少说“不”及防御式免责，事实、风险与权限边界照实说明。",
        "neutral": "使用中性、清楚、尊重人的措辞，先说明结果与可行路径，再交代影响决定的依据和限制。",
    }[preferences["tone"]]
    settings = json.dumps(preferences, ensure_ascii=False, sort_keys=True, allow_nan=False)
    section = ("\n\n### 本项目选择\n\n"
               "此处选择优先于本块和 skill 的默认偏好；用户最新指令优先。\n\n"
               + PREFERENCE_PREFIX + settings + " -->\n\n"
               + "- 连接与额度（`quota_mode=" + quota + "`）：" + quota_text + "\n"
               + "- 汇报方式（`report_mode=" + preferences["report_mode"] + "`）：" + report_text + "\n"
               + "- 表达方式（`tone=" + preferences["tone"] + "`）：" + tone_text + "\n"
               + "- 计划预留线：五小时等效余量 " + threshold + "%（按min(五小时剩余%, 周剩余%×6)判断，仅适用于真实计划额度）。\n"
               + "- 调用配套额度工具时使用 `--quota-mode " + quota
               + " --five-hour-closeout-percent " + threshold
               + "`；checker 与 admit 保持相同参数。\n")
    return (text[:text.index(END.decode("ascii"))].rstrip() + section
            + END.decode("ascii")).encode("utf-8")


def _manifest(files):
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    return (json.dumps({"format": 1, "owner": OWNER, "files": hashes},
                       indent=2, sort_keys=True) + "\n").encode("utf-8")


def _managed_files(files):
    # Generated bytecode is disposable, not a source change requiring an update.
    if files is None:
        return None
    return {name: files[name] for name in RUNTIME_FILES + (MANIFEST,)}


def _existing_skill(destination):
    _no_links(destination)
    if not destination.exists():
        return None
    if not destination.is_dir():
        raise InstallError("Skill destination is not a directory: " + str(destination))
    expected = set(RUNTIME_FILES) | {MANIFEST}
    allowed_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents
                    if str(parent) != "."}
    allowed_dirs.add("scripts/__pycache__")
    actual, caches = set(), set()
    for directory, dirs, files in os.walk(destination, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            _no_links(path)
            relative = path.relative_to(destination).as_posix()
            if path.is_dir():
                if relative not in allowed_dirs:
                    raise InstallError("Existing skill has an unknown directory: " + relative)
            else:
                if CACHE_PATH.fullmatch(relative):
                    caches.add(relative)
                else:
                    actual.add(relative)
    if actual != expected:
        raise InstallError("Existing skill is unowned or has extra/missing files; preserve it and review manually: "
                           + str(destination))
    existing = {name: _read_file(destination / name) for name in expected | caches}
    try:
        manifest = json.loads(existing[MANIFEST].decode("utf-8"))
        valid = (manifest.get("format") == 1 and manifest.get("owner") == OWNER
                 and manifest.get("files") == json.loads(_manifest(
                     {name: existing[name] for name in RUNTIME_FILES}).decode("utf-8"))["files"])
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        raise InstallError("Existing skill is custom or locally modified; refusing to overwrite: "
                           + str(destination))
    return existing


def _plan(project, files, agent, preference_overrides=None):
    _no_links(project)
    if not project.is_dir():
        raise InstallError("Project must be an existing directory: " + str(project))
    if agent == "codex" and os.path.lexists(project / "AGENTS.override.md"):
        raise InstallError("AGENTS.override.md exists and would override AGENTS.md; merge it manually first.")
    rules = project / ("AGENTS.md" if agent == "codex" else "CLAUDE.md")
    skill = project / (".agents" if agent == "codex" else ".claude") / "skills" / "eight-honors"
    _no_links(rules)
    original = _read_file(rules) if rules.exists() else None
    overrides = dict(preference_overrides or {})
    preferences = dict(DEFAULT_PREFERENCES, **_saved_preferences(original or b""))
    preferences.update(overrides)
    prior = _existing_skill(skill)
    desired = dict(files, **{MANIFEST: _manifest(files)})
    merged = _merge_rules(original or b"", _personalized_fragment(_validate_runtime(files), preferences))
    for parent in skill.parents:
        if parent == project:
            break
        if parent.exists() and not parent.is_dir():
            raise InstallError("Expected a directory: " + str(parent))
    return {"rules": rules, "skill": skill, "original": original, "prior": prior,
            "merged": merged, "desired": desired,
            "preferences": preferences, "preference_overrides": overrides,
            "rules_changed": original != merged, "skill_changed": _managed_files(prior) != desired}


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_rules(path, data, mode=None):
    descriptor, name = tempfile.mkstemp(prefix="." + path.name + "-", dir=str(path.parent))
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _remove_owned_tree(path, project):
    _no_links(path)
    if project not in path.parents:
        raise InstallError("Refusing to remove a directory outside the selected project: " + str(path))
    shutil.rmtree(path)


def _backup(project, plan):
    root = project / ".eight-honors-backups"
    _no_links(root)
    root.mkdir(mode=0o700, exist_ok=True)
    ignore = root / ".gitignore"
    _no_links(ignore)
    if not ignore.exists():
        _write(ignore, b"*\n")
    elif _read_file(ignore) != b"*\n":
        raise InstallError("Existing backup directory has an unknown .gitignore: " + str(root))
    if os.name != "nt":
        os.chmod(root, 0o700)
    if os.name == "nt":
        import ctypes
        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(root))
        if attributes == -1 or not ctypes.windll.kernel32.SetFileAttributesW(str(root), attributes | 2):
            raise InstallError("Could not mark the backup directory hidden: " + str(root))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    backup = root / stamp
    backup.mkdir(mode=0o700)
    try:
        if plan["original"] is not None and plan["rules_changed"]:
            _write(backup / plan["rules"].name, plan["original"])
        if plan["prior"] is not None and plan["skill_changed"]:
            for name, data in plan["prior"].items():
                _write(backup / "skill" / name, data)
    except OSError as exc:
        raise InstallError("Could not finish backup; partial backup retained at: " + str(backup)) from exc
    return backup


def _commit(project, plan):
    lock = project / ".eight-honors-install.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallError("Another install or stale lock exists; inspect it before retrying: " + str(lock)) from exc
    os.close(descriptor)
    stage, backup, created = None, None, []
    moved_old = installed = rules_written = False
    mode = None
    try:
        # Recheck after locking, before any backup or project mutation.
        fresh = _plan(project, {name: plan["desired"][name] for name in RUNTIME_FILES},
                      "codex" if plan["rules"].name == "AGENTS.md" else "claude",
                      plan["preference_overrides"])
        if fresh != plan:
            raise InstallError("Project changed while preparing installation; retry after reviewing it.")
        if plan["original"] is not None:
            mode = stat.S_IMODE(plan["rules"].stat().st_mode)
        stage = Path(tempfile.mkdtemp(prefix=".eight-honors-stage-", dir=str(project)))
        if plan["skill_changed"]:
            for name, data in plan["desired"].items():
                _write(stage / "new" / name, data)
        if ((plan["original"] is not None and plan["rules_changed"])
                or (plan["prior"] is not None and plan["skill_changed"])):
            backup = _backup(project, plan)
        if plan["skill_changed"]:
            for parent in reversed(plan["skill"].parents):
                if parent == project or project not in parent.parents:
                    continue
                if not parent.exists():
                    parent.mkdir()
                    created.append(parent)
            if plan["prior"] is not None:
                os.replace(plan["skill"], stage / "old")
                moved_old = True
            os.replace(stage / "new", plan["skill"])
            installed = True
        if plan["rules_changed"]:
            _atomic_rules(plan["rules"], plan["merged"], mode)
            rules_written = True
        if (_read_file(plan["rules"]) != plan["merged"]
                or _managed_files(_existing_skill(plan["skill"])) != plan["desired"]):
            raise InstallError("Installed files failed readback verification.")
    except Exception as exc:
        try:
            if rules_written:
                if plan["original"] is None:
                    plan["rules"].unlink()
                else:
                    _atomic_rules(plan["rules"], plan["original"], mode)
            if installed:
                _remove_owned_tree(plan["skill"], project)
            if moved_old:
                os.replace(stage / "old", plan["skill"])
            for directory in reversed(created):
                directory.rmdir()
        except Exception as rollback:
            retained = str(stage)
            stage = None  # Never erase the preserved old installation after rollback failure.
            raise InstallError("Install failed: %s; rollback failed: %s. Recovery files: %s; backup: %s"
                               % (exc, rollback, retained, backup)) from exc
        raise InstallError("Install failed; previous rules and skill restored: %s. Backup: %s"
                           % (exc, backup or "none needed")) from exc
    finally:
        if stage is not None:
            _remove_owned_tree(stage, project)
        lock.unlink()
    return backup


def install(project=None, source=None, agent="codex", dry_run=False, *,
            quota_mode=None, report_mode=None, tone=None, five_hour_closeout_percent=None):
    if agent not in ("codex", "claude"):
        raise InstallError("Unsupported agent: " + str(agent))
    overrides = _preference_overrides(quota_mode, report_mode, tone, five_hour_closeout_percent)
    project = _absolute(project or Path.cwd())
    if source is None:
        files = _archive_files(_download())
    else:
        source = _absolute(source)
        files = {name: _read_file(source / name) for name in RUNTIME_FILES}
    plan = _plan(project, files, agent, overrides)
    changed = plan["rules_changed"] or plan["skill_changed"]
    backup = _commit(project, plan) if changed and not dry_run else None
    return {"changed": changed, "dry_run": dry_run, "skill_path": str(plan["skill"]),
            "rules_path": str(plan["rules"]), "backup_path": str(backup) if backup else None,
            "skill_changed": plan["skill_changed"], "rules_changed": plan["rules_changed"],
            "preferences": plan["preferences"]}


def _choose(title, choices, default):
    options = "；".join("%d=%s" % (index, label)
                       for index, (_, label) in enumerate(choices, 1))
    while True:
        try:
            answer = input(title + "（" + options + "；直接回车=" + default + "）：").strip()
        except EOFError as exc:
            raise InstallError("Preference selection ended before installation; use explicit preference flags or finish --configure.") from exc
        if not answer:
            return default
        if answer.isdecimal() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1][0]
        if answer in {value for value, _ in choices}:
            return answer
        print("请选择上列序号或名称。")


def _configure(args):
    project = _absolute(args.project or Path.cwd())
    rules = project / ("AGENTS.md" if args.agent == "codex" else "CLAUDE.md")
    saved = _saved_preferences(_read_file(rules)) if rules.exists() else {}
    preferences = dict(DEFAULT_PREFERENCES, **saved)
    preferences.update(_preference_overrides(args.quota_mode, args.report_mode, args.tone,
                                           args.five_hour_closeout_percent))
    print("选择本项目的工作偏好；现有设置会保留，回车接受括号内默认。")
    preferences["quota_mode"] = _choose("连接方式", [
        ("auto", "自动识别"), ("subscription", "ChatGPT计划"),
        ("api", "API/中转"), ("off", "仅阶段交接")], preferences["quota_mode"])
    preferences["report_mode"] = _choose("汇报方式", [
        ("full", "每份工作报告附八条（作者默认）"),
        ("milestones", "阶段结束与交付附八条"), ("concise", "简洁正文")], preferences["report_mode"])
    preferences["tone"] = _choose("表达方式", [
        ("direct", "直接表达、少说不"), ("neutral", "中性表达")], preferences["tone"])
    return preferences


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Existing project directory (default: current directory)")
    parser.add_argument("--source", help="Local repository root; no network access")
    parser.add_argument("--agent", choices=("codex", "claude"), default="codex")
    parser.add_argument("--dry-run", action="store_true", help="Preview with zero filesystem writes")
    parser.add_argument("--configure", action="store_true", help="Choose connection, reporting and tone in three short prompts")
    parser.add_argument("--quota-mode", choices=PREFERENCE_CHOICES["quota_mode"])
    parser.add_argument("--report-mode", choices=PREFERENCE_CHOICES["report_mode"])
    parser.add_argument("--tone", choices=PREFERENCE_CHOICES["tone"])
    parser.add_argument("--five-hour-closeout-percent", type=float,
                        help="Plan allowance reserve, 0 through 100 (default: 30; existing choice retained)")
    args = parser.parse_args(argv)
    try:
        choices = (_configure(args) if args.configure else
                   _preference_overrides(args.quota_mode, args.report_mode, args.tone,
                                         args.five_hour_closeout_percent))
        result = install(args.project, args.source, args.agent, args.dry_run, **choices)
        prefix = "Would update" if result["dry_run"] else "Updated"
        if not result["changed"]:
            print("Already installed; runtime files and managed rules are unchanged.")
        else:
            if result["skill_changed"]:
                print(prefix + " skill: " + result["skill_path"])
            if result["rules_changed"]:
                print(prefix + " managed rules: " + result["rules_path"])
        if result["dry_run"]:
            print("Dry run: no files, directories, locks, or backups written.")
        elif result["backup_path"]:
            print("Backup (prior private content; do not publish): " + result["backup_path"])
        print("Project preferences: " + json.dumps(result["preferences"], ensure_ascii=False, sort_keys=True))
        if not result["dry_run"]:
            print("Open a new agent session and verify which rules and skill it actually reads.")
        return 0
    except (InstallError, OSError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
