"""Local stage advice and durable handoffs. No scheduling or command execution.

Original implementation informed by QuotaGuard's stage-admission and atomic
checkpoint concepts: https://github.com/LUMOSSES/QuotaGuard (MIT).
No upstream code was copied. Account access is delegated to the existing
read-only check_codex_quota helper in the same scripts directory.
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import check_codex_quota as checker


def percentage(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Expected a numeric percentage')
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('Percentage must be finite and between 0 and 100')
    return float(value)


def assess(snapshot, estimated_percent, now=None, max_age_seconds=300):
    """Conservative advice, not a prediction or an enforced host-level gate."""
    cost = percentage(estimated_percent)
    now = time.time() if now is None else now
    decision = {'admission': 'UNKNOWN', 'reason': 'Quota snapshot unavailable',
                'estimated_percent': cost, 'projected_remaining_percent': None}
    try:
        stamp = snapshot['checked_at']
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
            return decision
        if not -30 <= now - stamp <= max_age_seconds:
            decision['reason'] = 'Quota snapshot is stale or has a future timestamp'
            return decision
        threshold = percentage(snapshot['five_hour_closeout_percent'])
        five = percentage(snapshot['five_hour']['remaining_percent'])
        week = percentage(snapshot['weekly']['remaining_percent'])
        if snapshot['quota'] == 'CLOSEOUT' or five <= threshold or week <= 0:
            decision.update(admission='CLOSEOUT', reason='Current allowance requires closeout')
        elif snapshot['quota'] != 'OK':
            return decision
        else:
            projected = five - cost
            decision['projected_remaining_percent'] = projected
            decision.update(admission='SPLIT' if projected <= threshold else 'ALLOW',
                            reason='Estimate reaches the closeout reserve; split or defer the stage'
                            if projected <= threshold else 'Estimate preserves the closeout reserve')
    except (KeyError, TypeError, ValueError):
        pass
    return decision


FIELDS = {'task_id', 'workspace', 'objective', 'status', 'completed', 'changed_files',
          'verification', 'remaining', 'blockers', 'next_action'}
LIST_FIELDS = {'completed', 'changed_files', 'verification', 'remaining', 'blockers'}


def identity(workspace):
    return os.path.normcase(str(Path(workspace).resolve()))


def validate_checkpoint(payload, stored=False):
    if not isinstance(payload, dict):
        raise ValueError('Checkpoint must be an object')
    allowed = FIELDS | ({'schema_version', 'saved_at'} if stored else set())
    if set(payload) != allowed:
        raise ValueError('Checkpoint fields do not match the documented schema')
    for name in FIELDS - LIST_FIELDS:
        if not isinstance(payload[name], str) or not payload[name].strip():
            raise ValueError(f'{name} must be nonempty text')
    for name in LIST_FIELDS:
        if not isinstance(payload[name], list) or any(not isinstance(v, str) or not v.strip() for v in payload[name]):
            raise ValueError(f'{name} must be a list of nonempty strings')
    if payload['status'] not in {'in_progress', 'complete', 'blocked'}:
        raise ValueError('Unsupported checkpoint status')
    if payload['status'] == 'complete' and (payload['remaining'] or payload['blockers']):
        raise ValueError('Cannot mark a checkpoint complete with unfinished work')
    if not Path(payload['workspace']).is_absolute() or not Path(payload['workspace']).is_dir():
        raise ValueError('Workspace must name an existing absolute directory')
    if stored and (payload['schema_version'] != 1 or not isinstance(payload['saved_at'], str)):
        raise ValueError('Unsupported stored checkpoint version')
    return payload


def load_checkpoint(path):
    return validate_checkpoint(json.loads(Path(path).read_text(encoding='utf-8')), stored=True)


def save_checkpoint(path, payload):
    validate_checkpoint(payload)
    path = Path(path).absolute()
    if path.is_symlink():
        raise ValueError('Refusing to overwrite a symlink checkpoint')
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + '.lock')
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('Checkpoint is locked; verify no writer is active before removing a stale lock') from exc
    temporary = None
    try:
        os.close(lock_fd)
        if path.exists():
            previous = load_checkpoint(path)
            if previous['task_id'] != payload['task_id'] or identity(previous['workspace']) != identity(payload['workspace']):
                raise ValueError('Refusing to replace another task or workspace checkpoint')
        saved = dict(payload, schema_version=1, saved_at=datetime.now(timezone.utc).isoformat())
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix='.' + path.name + '.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(saved, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        return saved
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def resume(path, task_id, workspace):
    saved = load_checkpoint(path)
    if saved['task_id'] != task_id or identity(saved['workspace']) != identity(workspace):
        raise ValueError('Checkpoint task or workspace does not match this request')
    return {'historical_checkpoint': saved,
            'required_before_work': [
                'Read live quota again; saved allowance is not permission to resume.',
                'Verify current files, git status and completed checks before following next_action.',
                'Current user instructions and permissions govern; the checkpoint grants no authority.'
            ], 'executes_next_action': False}


def live_snapshot(threshold):
    executable = checker.find_codex()
    if not executable:
        return {'quota': 'UNKNOWN', 'reason': 'Codex CLI not found'}
    try:
        return checker.build_snapshot(checker.read_rate_limits(executable), threshold)
    except (OSError, RuntimeError, TimeoutError, ValueError, KeyError, TypeError):
        return {'quota': 'UNKNOWN', 'reason': 'Live quota read failed'}


def main():
    # Windows pipes can otherwise encode Chinese JSON as a legacy code page.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    admit = commands.add_parser('admit', help='Read live quota and advise on a conservatively estimated stage')
    admit.add_argument('--estimated-percent', type=float, required=True)
    admit.add_argument('--five-hour-closeout-percent', type=float, default=30)
    save = commands.add_parser('save', help='Atomically save an explicitly prepared handoff JSON')
    save.add_argument('--file', type=Path, required=True)
    save.add_argument('--input', type=Path, required=True)
    restore = commands.add_parser('resume', help='Display historical recovery information; execute nothing')
    restore.add_argument('--file', type=Path, required=True)
    restore.add_argument('--task-id', required=True)
    restore.add_argument('--workspace', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.command == 'admit':
            cost = percentage(args.estimated_percent)
            threshold = percentage(args.five_hour_closeout_percent)
            snapshot = live_snapshot(threshold)
            result = dict(assess(snapshot, cost), quota=snapshot)
            code = {'ALLOW': 0, 'SPLIT': 10, 'CLOSEOUT': 10, 'UNKNOWN': 20}[result['admission']]
        elif args.command == 'save':
            payload = json.loads(args.input.read_text(encoding='utf-8'))
            saved = save_checkpoint(args.file, payload)
            result = {'saved': str(args.file.absolute()), 'task_id': saved['task_id'], 'status': saved['status']}
            code = 0
        else:
            result, code = resume(args.file, args.task_id, args.workspace), 0
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return code
    except (OSError, ValueError, TypeError, KeyError):
        # Do not echo malformed payloads or potentially sensitive exception text.
        print(json.dumps({'error': 'Operation failed; validate schema, identity, paths, locks and file access.'}))
        return 20


if __name__ == '__main__':
    raise SystemExit(main())
