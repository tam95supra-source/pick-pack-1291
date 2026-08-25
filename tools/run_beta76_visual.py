#!/usr/bin/env python3
import hashlib, html, os, subprocess, time
from pathlib import Path

PKG = 'vn.pickpack1291.app.beta.publicbeta'
ACT = 'vn.pickpack1291.app.beta.OperationsActivity'
LAUNCHER = 'vn.pickpack1291.app.beta.FullBetaActivity'
APK = os.environ['APK']
EXPECTED_SHA = os.environ['EXPECTED_SHA']
EXPECTED_SIZE = int(os.environ['EXPECTED_SIZE'])
OUT = Path('/tmp/beta76-visual')
SIZES = ((320, 568, 160), (360, 640, 180), (480, 800, 240))


def run(args, check=True, text=True, timeout=20):
    return subprocess.run(
        args,
        check=check,
        text=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def adb(*args, check=True, text=True, timeout=20):
    return run(['adb', *args], check, text, timeout)


def rec(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(str(data), encoding='utf-8')


def prefs(values):
    rows = '\n'.join(
        f'<string name="{html.escape(key)}">{html.escape(str(value))}</string>'
        for key, value in values.items()
    )
    return "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n" + rows + '\n</map>'


def verify():
    payload = Path(APK).read_bytes()
    assert len(payload) == EXPECTED_SIZE
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SHA
    rec('candidate.txt', f'sha256={EXPECTED_SHA}\nsize={EXPECTED_SIZE}\npackage={PKG}\n')


def uid():
    adb('shell', 'am', 'force-stop', PKG, check=False)
    result = adb('shell', 'stat', '-c', '%u:%g', f'/data/user/0/{PKG}', check=False).stdout.strip()
    if ':' not in result:
        adb('shell', 'am', 'start', '-W', '-n', f'{PKG}/{LAUNCHER}', check=False)
        time.sleep(.8)
        adb('shell', 'am', 'force-stop', PKG, check=False)
        result = adb('shell', 'stat', '-c', '%u:%g', f'/data/user/0/{PKG}', check=False).stdout.strip()
    assert ':' in result
    return result.split(':', 1)


def seed():
    user_id, group_id = uid()
    OUT.mkdir(parents=True, exist_ok=True)
    auth = OUT / 'auth.xml'
    auth.write_text(
        prefs({
            'token': 'beta76-visual-offline-token',
            'login_id': 'tamnv2',
            'display_name': 'Nguyễn Văn Tâm',
            'role': 'SUPERADMIN',
            'position': 'superadmin',
            'email': 'tam95.supra@gmail.com',
        }),
        encoding='utf-8',
    )
    destination = f'/data/user/0/{PKG}/shared_prefs/pick_pack_auth_session_v2.xml'
    adb('push', str(auth), '/data/local/tmp/auth.xml')
    adb('shell', 'mkdir', '-p', f'/data/user/0/{PKG}/shared_prefs')
    adb('shell', 'cp', '/data/local/tmp/auth.xml', destination)
    adb('shell', 'chown', f'{user_id}:{group_id}', destination)
    adb('shell', 'chmod', '600', destination)


def shot(name, expected_size):
    data = adb('exec-out', 'screencap', '-p', text=False).stdout
    rec(name, data)
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert (int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')) == expected_size


def ime_visible():
    state = adb('shell', 'dumpsys', 'input_method', check=False).stdout
    rec('ime-state.txt', state)
    return 'mInputShown=true' in state or 'mIsInputViewShown=true' in state


def launch():
    adb('shell', 'am', 'force-stop', PKG, check=False)
    seed()
    adb('shell', 'am', 'start', '-W', '-n', f'{PKG}/{LAUNCHER}', check=False)
    time.sleep(.9)
    result = adb(
        'shell', 'am', 'start', '-W', '-n', f'{PKG}/{ACT}',
        '--es', 'module', 'BUSINESS',
        '--es', 'login', 'tamnv2',
        '--es', 'name', 'OWNER',
        '--es', 'role', 'SUPERADMIN',
        '--es', 'position', 'superadmin',
        '--es', 'email', 'tam95.supra@gmail.com',
        check=False,
    ).stdout
    rec('operations-start.txt', result)
    assert 'Permission Denial' not in result and 'Error type' not in result
    time.sleep(1)


def one_size(width, height, density):
    tag = f'{width}x{height}'
    scale = width / 320.0
    adb('shell', 'wm', 'size', f'{width}x{height}')
    adb('shell', 'wm', 'density', str(density))
    time.sleep(.8)
    launch()

    shot(f'{tag}-business.png', (width, height))
    adb('shell', 'input', 'tap', str(round(90 * scale)), str(round(300 * scale)))
    time.sleep(5.8)
    shot(f'{tag}-drop-top.png', (width, height))

    adb('shell', 'input', 'tap', str(round(160 * scale)), str(round(198 * scale)))
    time.sleep(1.2)
    if not ime_visible():
        adb('shell', 'input', 'tap', str(round(160 * scale)), str(round(198 * scale)))
        time.sleep(1.2)
    assert ime_visible(), f'{tag}: Scan QR focus did not open IME'
    shot(f'{tag}-keyboard.png', (width, height))

    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.6)
    shot(f'{tag}-drop-bottom.png', (width, height))
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.6)
    shot(f'{tag}-navigation-back.png', (width, height))


def main():
    verify()
    adb('wait-for-device')
    adb('shell', 'svc', 'wifi', 'disable', check=False)
    adb('shell', 'svc', 'data', 'disable', check=False)
    adb('shell', 'settings', 'put', 'global', 'window_animation_scale', '0', check=False)
    adb('shell', 'settings', 'put', 'global', 'transition_animation_scale', '0', check=False)
    adb('shell', 'settings', 'put', 'global', 'animator_duration_scale', '0', check=False)
    for width, height, density in SIZES:
        one_size(width, height, density)
    rec(
        'matrix.json',
        '{"status":"FULL_MATRIX_CAPTURED","sizes":["320x568","360x640","480x800"],'
        '"candidate_run":32875201581,"artifact_id":9573716441,'
        '"requires_human_inspection":true}\n',
    )
    print('BETA76_VISUAL_FULL_MATRIX_CAPTURED')


if __name__ == '__main__':
    main()
