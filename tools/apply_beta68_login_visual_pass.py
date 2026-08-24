#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'

full = FULL.read_text()
start = full.find('    private fun login() {')
end = full.find('    private fun openMainShell()', start)
if start < 0 or end < 0:
    raise SystemExit('FullBetaActivity.login range missing')

login = full[start:end]

# Current OWNER requirement: keep the restrained/simple Beta68 login produced by
# apply_beta68_owner_five_fixes.py. Do not restore the superseded demo background.
if 'login_vietnam_bg' in login:
    raise SystemExit('SUPERSEDED_DEMO_BACKGROUND_PRESENT')
if 'login_supra_logo' not in login:
    raise SystemExit('LOGIN_LOGO_MISSING')
if 'Quên mật khẩu?' not in login or 'Hiện mật khẩu' not in login:
    raise SystemExit('LOGIN_REQUIRED_ACTIONS_MISSING')

# Runtime regression fix only: do not autofocus the username field when opening
# the login screen, otherwise Android opens the soft keyboard and hides the form.
old = 'setScreen(root);root.requestApplyInsets();user.requestFocus()'
new = 'setScreen(root);root.requestApplyInsets();root.isFocusableInTouchMode=true;root.requestFocus()'
if old in full:
    full = full.replace(old, new, 1)
elif new not in full:
    raise SystemExit('LOGIN_FOCUS_ANCHOR_MISSING')

# Keep keyboard hidden until the user explicitly taps an input field.
soft_input = 'window.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN or android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)'
anchor = 'window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR'
if soft_input not in full[start:end]:
    if anchor not in full[start:end]:
        raise SystemExit('SOFT_INPUT_ANCHOR_MISSING')
    full = full[:start] + full[start:end].replace(anchor, anchor + '\n        ' + soft_input, 1) + full[end:]

FULL.write_text(full)
print('BETA68_SIMPLE_LOGIN_RUNTIME_FIX_APPLIED')
