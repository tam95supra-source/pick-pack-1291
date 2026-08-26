#!/usr/bin/env python3
import hashlib
import html
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PKG = 'vn.pickpack1291.app.beta.publicbeta'
ACT = 'vn.pickpack1291.app.beta.OperationsActivity'
LAUNCHER = 'vn.pickpack1291.app.beta.FullBetaActivity'
APK = os.environ['APK']
EXPECTED_SHA = os.environ['EXPECTED_SHA']
EXPECTED_SIZE = int(os.environ['EXPECTED_SIZE'])
OUT = Path('/tmp/beta77-visual')
SIZES = ((320, 568), (360, 640), (480, 800))


def run(args, check=True, text=True, timeout=24):
    return subprocess.run(args, check=check, text=text, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def adb(*args, check=True, text=True, timeout=24):
    return run(['adb', *args], check, text, timeout)


def rec(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(str(data), encoding='utf-8')


def prefs(values):
    rows = '\n'.join(f'<string name="{html.escape(key)}">{html.escape(str(value))}</string>' for key, value in values.items())
    return "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n" + rows + '\n</map>'


def verify():
    payload = Path(APK).read_bytes()
    assert len(payload) == EXPECTED_SIZE
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SHA
    rec('candidate.txt', f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\ncandidate_run=32953924512\nartifact_id=9601304499\nandroid_build_or_sign=false\n')


def app_owner():
    adb('shell', 'am', 'force-stop', PKG, check=False)
    result = adb('shell', 'stat', '-c', '%u:%g', f'/data/user/0/{PKG}', check=False).stdout.strip()
    if ':' not in result:
        adb('shell', 'am', 'start', '-W', '-n', f'{PKG}/{LAUNCHER}', check=False)
        time.sleep(.8)
        adb('shell', 'am', 'force-stop', PKG, check=False)
        result = adb('shell', 'stat', '-c', '%u:%g', f'/data/user/0/{PKG}', check=False).stdout.strip()
    assert ':' in result, result
    return result.split(':', 1)


def active_session(mnv, business_date, session_id, pda):
    return {
        'session_id': session_id,
        'mnv': mnv,
        'business_date': business_date,
        'shift': 'Ca 2',
        'state': 'ACTIVE',
        'pda_serial': pda,
        'pda_enter_status': 'Nguyên vẹn',
        'enter_at': f'{business_date}T03:10:00Z',
        'version': 4,
        'main_position_v64': 'Pick',
        'positions_v64': [
            {'position_key': 'PICK', 'position_label': 'Pick', 'state': 'ACTIVE'},
        ],
        'resource_assignments_v64': [
            {'assignment_id': f'{session_id}-pda', 'resource_type': 'PDA', 'resource_id': pda, 'state': 'ACTIVE'},
        ],
    }


def make_db(path, fixture):
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    cur = db.cursor()
    cur.execute('PRAGMA user_version=3')
    cur.execute('CREATE TABLE day_snapshot(business_date TEXT PRIMARY KEY NOT NULL,day_revision INTEGER NOT NULL,snapshot_json TEXT NOT NULL,saved_at INTEGER NOT NULL)')
    cur.execute('CREATE INDEX idx_day_snapshot_saved ON day_snapshot(saved_at)')
    cur.execute('CREATE TABLE sync_meta(meta_key TEXT PRIMARY KEY NOT NULL,meta_value TEXT NOT NULL)')
    cur.execute('CREATE TABLE mutation_outbox(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,exclusive INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,next_attempt_at INTEGER NOT NULL,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,last_error TEXT)')
    cur.execute('CREATE INDEX idx_mutation_outbox_due ON mutation_outbox(status,next_attempt_at,queued_at)')
    cur.execute('CREATE TABLE local_history(event_id TEXT PRIMARY KEY NOT NULL,body_json TEXT NOT NULL,status TEXT NOT NULL,last_error TEXT,queued_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)')
    cur.execute('CREATE INDEX idx_local_history_queued ON local_history(queued_at DESC)')
    today = datetime.now(ZoneInfo('Asia/Bangkok')).date()
    if fixture == 'current':
        dates = [(today, [active_session('30011', today.isoformat(), 'beta77-current-active', 'NLS-MT90-0012345')])]
    elif fixture == 'old':
        old = today - timedelta(days=1)
        dates = [(old, [active_session('30012', old.isoformat(), 'beta77-overnight-active', 'NLS-MT90-0054321')])]
    else:
        dates = []
    now_ms = int(time.time() * 1000)
    for business_date, sessions in dates:
        snapshot = {'ok': True, 'business_date': business_date.isoformat(), 'day_revision': 77, 'sessions': sessions, 'events': [], 'labor': []}
        cur.execute('INSERT INTO day_snapshot VALUES(?,?,?,?)', (business_date.isoformat(), 77, json.dumps(snapshot, ensure_ascii=False), now_ms))
    cur.execute('INSERT INTO sync_meta VALUES(?,?)', ('business_date', today.isoformat()))
    db.commit()
    db.close()


def seed(fixture):
    user_id, group_id = app_owner()
    OUT.mkdir(parents=True, exist_ok=True)
    auth = OUT / 'auth.xml'
    auth.write_text(prefs({
        'token': 'beta77-visual-offline-token',
        'login_id': 'tamnv2',
        'display_name': 'Nguyễn Văn Tâm',
        'role': 'SUPERADMIN',
        'position': 'superadmin',
        'email': 'tam95.supra@gmail.com',
    }), encoding='utf-8')
    master = {
        'ok': True,
        'master_revision': 77,
        'staff': [
            {'mnv': '30011', 'full_name': 'Nguyễn Văn A', 'main_position': 'Pick', 'supplier': 'NLV', 'department': '', 'site': '1291', 'warehouse': 'HY1'},
            {'mnv': '30012', 'full_name': 'Nguyễn Văn B', 'main_position': 'Pick', 'supplier': 'IH', 'department': 'Pick Pack', 'site': '1291', 'warehouse': 'HY1'},
        ],
        'pdas': [
            {'serial': 'NLS-MT90-0012345', 'last5': '12345', 'status': 'Nguyên vẹn'},
            {'serial': 'NLS-MT90-0054321', 'last5': '54321', 'status': 'Nguyên vẹn'},
        ],
        'pda_statuses': ['Nguyên vẹn', 'Màn hình xước nhẹ', 'Lỗi quét mã'],
        'user_picks': ['HY1.OUT.01', 'HY1.OUT.02'],
        'pack_bundles': [{'table': 'D1', 'user_pack': 'PACK01'}],
    }
    master_path = OUT / 'pp1291_master_cache.xml'
    master_path.write_text(prefs({'snapshot': json.dumps(master, ensure_ascii=False, separators=(',', ':'))}), encoding='utf-8')
    db_path = OUT / 'pp_operational_45d.db'
    make_db(db_path, fixture)
    prefs_dir = f'/data/user/0/{PKG}/shared_prefs'
    db_dir = f'/data/user/0/{PKG}/databases'
    adb('shell', 'mkdir', '-p', prefs_dir, db_dir)
    adb('shell', 'rm', '-f', f'{db_dir}/pp_operational_45d.db', f'{db_dir}/pp_operational_45d.db-wal', f'{db_dir}/pp_operational_45d.db-shm', f'{prefs_dir}/pp1291_master_cache.xml', check=False)
    files = [
        (auth, f'{prefs_dir}/pick_pack_auth_session_v2.xml'),
        (master_path, f'{prefs_dir}/pp1291_master_cache.xml'),
        (db_path, f'{db_dir}/pp_operational_45d.db'),
    ]
    for local, destination in files:
        temp = f'/data/local/tmp/{local.name}'
        adb('push', str(local), temp)
        adb('shell', 'cp', temp, destination)
        adb('shell', 'chown', f'{user_id}:{group_id}', destination)
        adb('shell', 'chmod', '600', destination)


def shot(name, expected_size):
    data = adb('exec-out', 'screencap', '-p', text=False).stdout
    rec(name, data)
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    got = (int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big'))
    assert got == expected_size, (got, expected_size)
    return data


def assert_activity(tag):
    state = adb('shell', 'dumpsys', 'activity', 'activities', check=False).stdout
    rec(f'{tag}-activity.txt', state[-12000:])
    assert PKG in state and 'OperationsActivity' in state


def ime_visible(tag):
    state = adb('shell', 'dumpsys', 'input_method', check=False).stdout
    rec(f'{tag}-ime-state.txt', state)
    return 'mInputShown=true' in state or 'mIsInputViewShown=true' in state


def hide_ime(tag):
    if ime_visible(tag):
        adb('shell', 'input', 'keyevent', '4')
        time.sleep(.5)


def launch(tag, fixture, module='BUSINESS'):
    adb('shell', 'am', 'force-stop', PKG, check=False)
    seed(fixture)
    result = adb(
        'shell', 'am', 'start', '-W', '-n', f'{PKG}/{ACT}',
        '--es', 'module', module,
        '--es', 'login', 'tamnv2',
        '--es', 'name', 'OWNER',
        '--es', 'role', 'SUPERADMIN',
        '--es', 'position', 'superadmin',
        '--es', 'email', 'tam95.supra@gmail.com',
        check=False,
    ).stdout
    rec(f'{tag}-operations-start.txt', result)
    assert 'Permission Denial' not in result and 'Error type' not in result
    time.sleep(1.2)
    assert_activity(tag)


def capture_employee(tag, size):
    width, height = size
    launch(tag + '-employee', 'current')
    home = shot(f'{tag}-business-current-active.png', size)
    adb('shell', 'input', 'tap', str(width // 4), '238')
    time.sleep(1.0)
    adb('shell', 'input', 'tap', str(width // 2), '169')
    adb('shell', 'input', 'text', '30011')
    adb('shell', 'input', 'keyevent', '66')
    time.sleep(2.2)
    hide_ime(tag + '-employee-active')
    top = shot(f'{tag}-employee-active-top.png', size)
    assert hashlib.sha256(top).digest() != hashlib.sha256(home).digest(), f'{tag}: active employee screen did not open'
    for index in range(1, 4):
        adb('shell', 'input', 'swipe', str(width // 2), str(height - 150), str(width // 2), '155', '420')
        time.sleep(.55)
        shot(f'{tag}-employee-active-scroll-{index}.png', size)
    assert_activity(tag + '-employee-active-final')


def capture_old_session(tag, size):
    width, _ = size
    launch(tag + '-old-session', 'old')
    home = shot(f'{tag}-old-session-warning.png', size)
    adb('shell', 'input', 'tap', str(width // 2), '170')
    time.sleep(.8)
    dialog = shot(f'{tag}-old-session-dialog.png', size)
    assert hashlib.sha256(dialog).digest() != hashlib.sha256(home).digest(), f'{tag}: old-session dialog did not open'
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.4)


def capture_pda_release(tag, size):
    launch(tag + '-pda-release', 'current', 'PDA_EXCHANGE')
    time.sleep(7.0)
    hide_ime(tag + '-pda-release')
    shot(f'{tag}-pda-release-early-return.png', size)
    assert_activity(tag + '-pda-release-final')


def capture_drop(tag, size):
    width, _ = size
    launch(tag + '-drop', 'empty')
    home = shot(f'{tag}-business-drop-card.png', size)
    adb('shell', 'input', 'tap', str(width // 4), '300')
    time.sleep(5.8)
    assert_activity(tag + '-drop-screen')
    top = shot(f'{tag}-drop-top.png', size)
    assert hashlib.sha256(top).digest() != hashlib.sha256(home).digest(), f'{tag}: drop screen did not open'
    adb('shell', 'input', 'tap', str(width // 2), '198')
    time.sleep(1.1)
    if not ime_visible(tag):
        adb('shell', 'input', 'tap', str(width // 2), '198')
        time.sleep(1.1)
    assert ime_visible(tag), f'{tag}: Scan QR focus did not open IME'
    shot(f'{tag}-drop-keyboard.png', size)
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.6)
    shot(f'{tag}-drop-bottom.png', size)
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.8)
    assert_activity(tag + '-drop-back')
    shot(f'{tag}-drop-back.png', size)


def capture_size(width, height):
    tag = f'{width}x{height}'
    adb('shell', 'wm', 'size', tag)
    adb('shell', 'wm', 'density', '160')
    time.sleep(.7)
    capture_employee(tag, (width, height))
    capture_old_session(tag, (width, height))
    capture_pda_release(tag, (width, height))
    capture_drop(tag, (width, height))


def main():
    verify()
    adb('wait-for-device')
    adb('shell', 'svc', 'wifi', 'disable', check=False)
    adb('shell', 'svc', 'data', 'disable', check=False)
    for key in ('window_animation_scale', 'transition_animation_scale', 'animator_duration_scale'):
        adb('shell', 'settings', 'put', 'global', key, '0', check=False)
    for width, height in SIZES:
        capture_size(width, height)
    rec('matrix.json', json.dumps({
        'status': 'FULL_MATRIX_CAPTURED',
        'candidate_run': 32953924512,
        'artifact_id': 9601304499,
        'sizes': ['320x568', '360x640', '480x800'],
        'density': 160,
        'scenarios': ['drop_receive', 'employee_active_same_day', 'employee_null_dash', 'overnight_active_warning', 'pda_release_early_return'],
        'android_build_or_sign': False,
        'requires_human_inspection': True,
    }, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('BETA77_EXACT_VISUAL_FULL_MATRIX_CAPTURED')


if __name__ == '__main__':
    main()
