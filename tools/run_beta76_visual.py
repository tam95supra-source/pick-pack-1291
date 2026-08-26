#!/usr/bin/env python3
import hashlib, html, os, re, subprocess, time, xml.etree.ElementTree as ET
from pathlib import Path

PKG = 'vn.pickpack1291.app.beta.publicbeta'
ACT = 'vn.pickpack1291.app.beta.OperationsActivity'
LAUNCHER = 'vn.pickpack1291.app.beta.FullBetaActivity'
APK = os.environ['APK']
EXPECTED_SHA = os.environ['EXPECTED_SHA']
EXPECTED_SIZE = int(os.environ['EXPECTED_SIZE'])
OUT = Path('/tmp/beta77-visual')
SIZES = ((320, 568, 160), (360, 640, 180), (480, 800, 240))


def run(args, check=True, text=True, timeout=20):
    return subprocess.run(args, check=check, text=text, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def adb(*args, check=True, text=True, timeout=20):
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
    auth.write_text(prefs({
        'token': 'beta77-visual-offline-token',
        'login_id': 'tamnv2',
        'display_name': 'Nguyễn Văn Tâm',
        'role': 'SUPERADMIN',
        'position': 'superadmin',
        'email': 'tam95.supra@gmail.com',
    }), encoding='utf-8')
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


def dump_ui(tag):
    path = '/data/local/tmp/beta77-window.xml'
    diagnostics = []
    last_raw = ''
    for attempt in range(1, 4):
        adb('wait-for-device', check=False, timeout=30)
        adb('shell', 'rm', '-f', path, check=False, timeout=10)
        result = adb(
            'shell', 'uiautomator', 'runtest',
            '/data/local/tmp/beta77-visual-dumper.jar',
            '-c', 'vn.pickpack1291.visual.VisualHierarchyDumper#testDump',
            check=False, timeout=30,
        )
        raw = adb('shell', 'cat', path, check=False, timeout=10).stdout
        last_raw = raw
        diagnostics.append(
            f'attempt={attempt} dumper={result.stdout.strip()} bytes={len(raw.encode("utf-8"))}'
        )
        if '<hierarchy' in raw:
            try:
                ET.fromstring(raw)
            except ET.ParseError as exc:
                diagnostics.append(f'attempt={attempt} parse_error={exc}')
            else:
                rec(f'{tag}-ui.xml', raw)
                rec(f'{tag}-ui-dump.txt', '\n'.join(diagnostics) + '\n')
                return raw
        time.sleep(attempt)
    rec(f'{tag}-ui.xml', last_raw)
    rec(f'{tag}-ui-dump.txt', '\n'.join(diagnostics) + '\n')
    raise AssertionError(f'{tag}: non-idle UI hierarchy unavailable after 3 bounded attempts')


def visible_texts(tag):
    root = ET.fromstring(dump_ui(tag))
    out = []
    for node in root.iter('node'):
        text = (node.attrib.get('text') or '').strip()
        desc = (node.attrib.get('content-desc') or '').strip()
        if text: out.append(text)
        if desc and desc != text: out.append(desc)
    rec(f'{tag}-texts.txt', '\n'.join(out))
    return out


def tap_text(tag, needle):
    root = ET.fromstring(dump_ui(tag))
    needle_fold = needle.casefold()
    matches = []
    for node in root.iter('node'):
        text = (node.attrib.get('text') or '').strip()
        desc = (node.attrib.get('content-desc') or '').strip()
        hay = f'{text} {desc}'.casefold()
        if needle_fold not in hay:
            continue
        m = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
        if not m:
            continue
        x1,y1,x2,y2 = map(int,m.groups())
        matches.append((x2-x1)*(y2-y1), (x1+x2)//2, (y1+y2)//2, text, desc)
    assert matches, f'{tag}: text not found: {needle}'
    _, x, y, text, desc = sorted(matches, reverse=True)[0]
    rec(f'{tag}-tap.txt', f'needle={needle}\nx={x}\ny={y}\ntext={text}\ndesc={desc}\n')
    adb('shell', 'input', 'tap', str(x), str(y))


def ime_visible():
    state = adb('shell', 'dumpsys', 'input_method', check=False).stdout
    return 'mInputShown=true' in state or 'mIsInputViewShown=true' in state


def launch():
    adb('shell', 'am', 'force-stop', PKG, check=False)
    seed()
    adb('shell', 'am', 'start', '-W', '-n', f'{PKG}/{LAUNCHER}', check=False)
    time.sleep(.9)
    result = adb('shell', 'am', 'start', '-W', '-n', f'{PKG}/{ACT}', '--es', 'module', 'BUSINESS', '--es', 'login', 'tamnv2', '--es', 'name', 'OWNER', '--es', 'role', 'SUPERADMIN', '--es', 'position', 'superadmin', '--es', 'email', 'tam95.supra@gmail.com', check=False).stdout
    rec('operations-start.txt', result)
    assert 'Permission Denial' not in result and 'Error type' not in result
    time.sleep(1.2)


def assert_home(tag):
    texts = visible_texts(tag + '-home')
    joined = '\n'.join(texts)
    assert 'Quét QR nhân sự' in joined
    assert 'Nhận hàng Rớt' in joined
    assert 'Đổi / trả PDA' in joined


def capture_employee(tag, size):
    launch()
    assert_home(tag + '-employee')
    shot(f'{tag}-business-employee-card.png', size)
    tap_text(tag + '-employee-card', 'Quét QR nhân sự')
    time.sleep(1.2)
    texts = visible_texts(tag + '-employee-screen')
    assert any(('nhân sự' in x.casefold() or 'mã nhân viên' in x.casefold() or 'quét' in x.casefold()) for x in texts), f'{tag}: wrong employee screen'
    shot(f'{tag}-employee-scan.png', size)
    # Back must return inside the app to the previous BUSINESS screen, not exit the app.
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.7)
    assert_home(tag + '-employee-back')
    shot(f'{tag}-employee-back.png', size)


def capture_drop(tag, size):
    launch()
    assert_home(tag + '-drop')
    shot(f'{tag}-business-drop-card.png', size)
    tap_text(tag + '-drop-card', 'Nhận hàng Rớt')
    time.sleep(2.2)
    texts = visible_texts(tag + '-drop-screen')
    joined = '\n'.join(texts)
    assert 'Nhận hàng rớt' in joined or 'Nhận hàng Rớt' in joined
    assert ('Chưa có vị trí' in joined or 'Chọn vị trí' in joined or 'Vị trí' in joined)
    assert 'Thêm thông tin' in joined
    assert 'Xoá toàn bộ' in joined or 'Xóa toàn bộ' in joined
    shot(f'{tag}-drop-top.png', size)

    # Focus the QR field by UI text when possible; fallback to first editable node center.
    try:
        tap_text(tag + '-drop-qr', 'QR')
    except AssertionError:
        root = ET.fromstring(dump_ui(tag + '-drop-editable'))
        target = None
        for node in root.iter('node'):
            if node.attrib.get('class','').endswith('EditText'):
                m = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds',''))
                if m:
                    x1,y1,x2,y2 = map(int,m.groups()); target=((x1+x2)//2,(y1+y2)//2); break
        assert target, f'{tag}: QR editable field not found'
        adb('shell','input','tap',str(target[0]),str(target[1]))
    time.sleep(1.0)
    assert ime_visible(), f'{tag}: QR focus did not open IME'
    shot(f'{tag}-drop-keyboard.png', size)
    # Even with keyboard visible the action screen must still be a real populated form, not blank.
    texts = visible_texts(tag + '-drop-keyboard')
    assert any('thêm thông tin' in x.casefold() for x in texts), f'{tag}: action hidden by keyboard'

    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.5)
    shot(f'{tag}-drop-bottom.png', size)
    adb('shell', 'input', 'keyevent', '4')
    time.sleep(.7)
    assert_home(tag + '-drop-back')
    shot(f'{tag}-drop-back.png', size)


def one_size(width, height, density):
    tag = f'{width}x{height}'
    adb('shell', 'wm', 'size', f'{width}x{height}')
    adb('shell', 'wm', 'density', str(density))
    time.sleep(.8)
    capture_employee(tag, (width, height))
    capture_drop(tag, (width, height))


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
    rec('matrix.json', '{"status":"FULL_MATRIX_CAPTURED","sizes":["320x568","360x640","480x800"],"cards":["Quét QR nhân sự","Nhận hàng Rớt"],"requires_human_inspection":true}\n')
    print('BETA77_VISUAL_FULL_MATRIX_CAPTURED')


if __name__ == '__main__':
    main()
