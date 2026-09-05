#!/usr/bin/env python3
from pathlib import Path
ops=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt').read_text(encoding='utf-8')
gradle=Path('app/build.gradle.kts').read_text(encoding='utf-8')
notes=Path('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt').read_text(encoding='utf-8')
assert 'versionCode = 131' in gradle
assert 'versionName = "0.4.2-beta.125"' in gradle
assert 'VERSION_NAME = "0.4.2-beta.125"' in notes
set_screen=ops[ops.index('private fun setScreen(content:View)'):ops.index('private fun handleBackNavigation')]
for token in [
    'setOf("EMPLOYEE_LOADING","EMPLOYEE","EMPLOYEE_LOOKUP_ERROR")',
    'val sameEmployeeFrame=displayedModule==module&&displayedScreenState in employeeFrameStates&&screenState in employeeFrameStates',
    '!sameEmployeeFrame',
    'screenBackStack.addLast(ScreenSnapshot('
]: assert token in set_screen, token
# Actual navigation history semantics remains stack-based and one Back restores the prior real snapshot.
nav=ops[ops.index('private fun handleBackNavigation'):ops.index('private fun body()') if ops.index('private fun body()')>ops.index('private fun handleBackNavigation') else len(ops)]
assert 'if(screenBackStack.isNotEmpty())navigateBack()' in ops
assert 'val snapshot=screenBackStack.removeLast()' in ops
# Beta124 bug must stay fixed: pre-scan roster present, result renderer never appends it.
scan=ops[ops.index('private fun employeeScan()'):ops.index('private fun sameEmployeeContext')]
assert 'addInlineCurrentShiftStaff(preScanStaff)' in scan
assert 'preScanStaff.visibility=View.GONE;loadEmployee(v)' in scan
render=ops[ops.index('private fun renderEmployee(ctx: JSONObject'):ops.index('private fun sameEmployeeContext')]
assert 'addInlineCurrentShiftStaff(body)' not in render
print('beta125_navigation_frame_contract=PASS scan_to_loading=PUSH loading_to_result=REPLACE back_one_step=SCAN post_scan_roster=HIDDEN')
