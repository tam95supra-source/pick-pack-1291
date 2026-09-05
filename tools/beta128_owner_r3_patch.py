#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "release/beta128-owner-r3-drop-realtime-20260905"
CMD_ID = "CMD-20260905-003"
OWNER_TEXT = """1. Mục bắn hàng rớt

- Thu hẹp cột Vi trí và cột SỐ kiện và cột Chọn một chút để đảm bảo cột thời gian được dãn ra, text thời gian không bị che phải chuyển thành ba chấm
- Nếu đã có text ở trong ô nhập thì không cần tiêu đề ô Scan QR, DO, Số kiện nữa.
- Làm nổi bật các ô lên cho người dùng dễ nhìn.

2. ms của ô Mạng nếu anh muốn cứ tầm 5s cập nhật ms một lần có ảnh hưởng tới plan free các dịch vụ cũng như pin PDA không?
3. Vào QR vào ra, vào công nhật, vào điểm danh. Cách danh sách nhân sự, thông tin chi tiết bị nhấp nháy nhanh, kiểu reload lại trạng, rất khó chịu, vẫn không hề đúng realtime UI update mượt mà như dạng facebook, gmail."""


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"BETA128_R3_PATCH_FAIL:{label}:count={count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, repl: str, label: str, flags: int = 0) -> str:
    out, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"BETA128_R3_PATCH_FAIL:{label}:count={count}")
    return out


def patch_drop() -> None:
    p = "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt"
    s = read(p)
    s = replace_once(
        s,
        'fun input(hintText:String,numeric:Boolean=false)=EditText(activity).apply{hint=hintText;textSize=13f;setTextColor(ink);setHintTextColor(Color.rgb(148,163,184));setPadding(dp(11),dp(8),dp(11),dp(8));minHeight=dp(46);background=bg();setSingleLine(true);if(numeric){inputType=InputType.TYPE_CLASS_NUMBER;keyListener=DigitsKeyListener.getInstance("0123456789")}else inputType=InputType.TYPE_CLASS_TEXT}',
        'fun input(hintText:String,numeric:Boolean=false)=EditText(activity).apply{hint=hintText;textSize=13f;setTextColor(ink);setHintTextColor(Color.rgb(100,116,139));setPadding(dp(11),dp(8),dp(11),dp(8));minHeight=dp(48);background=GradientDrawable().apply{setColor(Color.rgb(247,253,252));cornerRadius=dp(12).toFloat();setStroke(dp(2),teal)};setSingleLine(true);if(numeric){inputType=InputType.TYPE_CLASS_NUMBER;keyListener=DigitsKeyListener.getInstance("0123456789")}else inputType=InputType.TYPE_CLASS_TEXT}',
        "drop-prominent-inputs",
    )
    s = replace_once(
        s,
        'body.addView(field("Scan QR",qr));body.addView(gap(8))\n        val doPackage=row()\n        doPackage.addView(field("DO",order),LinearLayout.LayoutParams(0,-2,1f).apply{marginEnd=dp(4)})\n        doPackage.addView(field("Số kiện",packages),LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(4)})',
        'body.addView(qr,LinearLayout.LayoutParams(-1,dp(48)));body.addView(gap(8))\n        val doPackage=row()\n        doPackage.addView(order,LinearLayout.LayoutParams(0,dp(48),1.25f).apply{marginEnd=dp(4)})\n        doPackage.addView(packages,LinearLayout.LayoutParams(0,dp(48),.75f).apply{marginStart=dp(4)})',
        "drop-remove-redundant-input-labels",
    )
    s = replace_once(
        s,
        'if(canDelete)header.addView(tableCell("Chọn",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.58f))\n                header.addView(tableCell("Thời gian",true),LinearLayout.LayoutParams(0,dp(38),1.22f))\n                header.addView(tableCell("Vị trí",true),LinearLayout.LayoutParams(0,dp(38),.82f))\n                header.addView(tableCell("DO",true),LinearLayout.LayoutParams(0,dp(38),1.08f))\n                header.addView(tableCell("Số kiện",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.78f))',
        'if(canDelete)header.addView(tableCell("Chọn",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.50f))\n                header.addView(tableCell("Thời gian",true),LinearLayout.LayoutParams(0,dp(38),1.52f))\n                header.addView(tableCell("Vị trí",true),LinearLayout.LayoutParams(0,dp(38),.70f))\n                header.addView(tableCell("DO",true),LinearLayout.LayoutParams(0,dp(38),1.08f))\n                header.addView(tableCell("Số kiện",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.68f))',
        "drop-header-column-weights",
    )
    s = replace_once(s, 'addView(check,FrameLayout.LayoutParams(dp(38),dp(38),Gravity.CENTER))', 'addView(check,FrameLayout.LayoutParams(dp(34),dp(34),Gravity.CENTER))', "drop-checkbox-compact")
    s = replace_once(
        s,
        'line.addView(holder,LinearLayout.LayoutParams(0,dp(46),.58f))\n                    }\n                    line.addView(tableCell(fmtDropTime(x.optString("created_at"))),LinearLayout.LayoutParams(0,dp(46),1.22f))\n                    line.addView(tableCell(x.optString("location").ifBlank{"-"}),LinearLayout.LayoutParams(0,dp(46),.82f))\n                    line.addView(tableCell(x.optString("do_number").ifBlank{"-"}),LinearLayout.LayoutParams(0,dp(46),1.08f))\n                    line.addView(tableCell(x.optInt("package_count").toString(),false,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(46),.78f))',
        'line.addView(holder,LinearLayout.LayoutParams(0,dp(46),.50f))\n                    }\n                    val timeCell=tableCell(fmtDropTime(x.optString("created_at"))).apply{ellipsize=null;maxLines=1;textSize=8.0f}\n                    line.addView(timeCell,LinearLayout.LayoutParams(0,dp(46),1.52f))\n                    line.addView(tableCell(x.optString("location").ifBlank{"-"}),LinearLayout.LayoutParams(0,dp(46),.70f))\n                    line.addView(tableCell(x.optString("do_number").ifBlank{"-"}),LinearLayout.LayoutParams(0,dp(46),1.08f))\n                    line.addView(tableCell(x.optInt("package_count").toString(),false,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(46),.68f))',
        "drop-row-column-weights",
    )
    write(p, s)


def patch_attendance() -> None:
    p = "app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt"
    s = read(p)
    s = replace_once(
        s,
        '    @Volatile private var homeWarningRefresh:(()->Unit)?=null\n\n    fun onRealtime(changedDates:Set<String>){\n        // Foreground websocket already performs the relevant fast refresh. Projection completion\n        // must not fire a second Service-backed warning reload.\n        if(activeDate.isNotBlank()&&activeDate in changedDates)activeRefresh?.invoke()\n    }\n    fun onRealtimeFast(date:String){\n        if(date.isBlank())return\n        if(activeDate==date)activeRefresh?.invoke()\n        homeWarningRefresh?.invoke()\n    }\n    fun leave(){activeDate="";activeRefresh=null}',
        '    @Volatile private var homeWarningRefresh:(()->Unit)?=null\n    @Volatile private var lastFastRefreshDate=""\n    @Volatile private var lastFastRefreshAt=0L\n\n    fun onRealtime(changedDates:Set<String>){\n        if(activeDate.isBlank()||activeDate !in changedDates)return\n        val now=android.os.SystemClock.elapsedRealtime()\n        if(lastFastRefreshDate==activeDate&&now-lastFastRefreshAt<1_500L)return\n        activeRefresh?.invoke()\n    }\n    fun onRealtimeFast(date:String){\n        if(date.isBlank())return\n        if(activeDate==date){\n            lastFastRefreshDate=date\n            lastFastRefreshAt=android.os.SystemClock.elapsedRealtime()\n            activeRefresh?.invoke()\n        }\n        homeWarningRefresh?.invoke()\n    }\n    fun leave(){activeDate="";activeRefresh=null;lastFastRefreshDate="";lastFastRefreshAt=0L}',
        "attendance-fast-final-dedupe",
    )
    s = replace_once(s, '        var renderGeneration=0L\n', '        var renderGeneration=0L\n        var lastRenderSignature=""\n', "attendance-render-signature-var")
    s = replace_once(
        s,
        '        fun render(){\n            val generation=++renderGeneration\n            val source=payload\n            contentBox.removeAllViews()',
        '        fun render(){\n            val source=payload\n            val signature=buildString{append(selected.toString()).append(\'\\u001f\').append(search.text?.toString().orEmpty()).append(\'\\u001f\').append(shiftFilter.selectedItem?.toString().orEmpty()).append(\'\\u001f\').append(supplierFilter.selectedItem?.toString().orEmpty()).append(\'\\u001f\').append(positionFilter.selectedItem?.toString().orEmpty()).append(\'\\u001f\').append(source?.toString().orEmpty())}\n            if(signature==lastRenderSignature)return\n            lastRenderSignature=signature\n            val generation=++renderGeneration\n            contentBox.removeAllViews()',
        "attendance-noop-render-dedupe",
    )
    s = replace_once(s, '            contentBox.post{addChunk(0)}', '            addChunk(0)', "attendance-first-chunk-synchronous")
    # Scheduled time-boundary refresh must bypass the no-op signature because status semantics can change with clock time.
    s = replace_once(
        s,
        '                val nowDay=today()\n                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}',
        '                val nowDay=today()\n                lastRenderSignature=""\n                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}',
        "attendance-boundary-force-render",
    )
    write(p, s)


def patch_operations() -> None:
    p = "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt"
    s = read(p)
    s = replace_once(
        s,
        '        var laborFilterSignature=""\n        var laborRenderGeneration=0L',
        '        var laborFilterSignature=""\n        var laborRenderGeneration=0L\n        var laborRenderSignature=""\n        var laborWarningSignature=""',
        "labor-signature-vars",
    )
    s = replace_once(
        s,
        '            val visible=rows.filter{x->(shift=="Tất cả ca"||x.optString("shift")==shift)&&(sup=="Tất cả NCC"||x.optString("supplier")==sup)&&(pos=="Tất cả vị trí"||rowPosition(x)==pos)}\n            val generation=++laborRenderGeneration\n            openBox.removeAllViews()',
        '            val visible=rows.filter{x->(shift=="Tất cả ca"||x.optString("shift")==shift)&&(sup=="Tất cả NCC"||x.optString("supplier")==sup)&&(pos=="Tất cả vị trí"||rowPosition(x)==pos)}\n            val renderSignature=buildString{append(selectedLaborDate).append(\'\\u001f\').append(shift).append(\'\\u001f\').append(sup).append(\'\\u001f\').append(pos);rows.forEach{append(\'\\u001e\').append(it.toString())}}\n            if(renderSignature==laborRenderSignature)return\n            laborRenderSignature=renderSignature\n            val generation=++laborRenderGeneration\n            openBox.removeAllViews()',
        "labor-noop-render-dedupe",
    )
    s = replace_once(s, '            openBox.post{addChunk(0)}', '            addChunk(0)', "labor-first-chunk-synchronous")
    s = replace_once(
        s,
        '        fun reviewFixed(rows:List<JSONObject>){\n            fixedWarningHost.removeAllViews()\n            if(selectedLaborDate!=currentDate)return',
        '        fun reviewFixed(rows:List<JSONObject>){\n            val warningSignature=buildString{append(selectedLaborDate).append(\'\\u001f\').append(operationalStore.revision(currentDate)).append(\'\\u001f\').append((reviewPrefs.getStringSet("ack_$currentDate",emptySet())?:emptySet()).sorted().joinToString(","));rows.forEach{append(\'\\u001e\').append(it.toString())}}\n            if(warningSignature==laborWarningSignature)return\n            laborWarningSignature=warningSignature\n            fixedWarningHost.removeAllViews()\n            if(selectedLaborDate!=currentDate)return',
        "labor-warning-noop-dedupe",
    )
    s = replace_once(
        s,
        '        val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()}\n        fun renderTimeline(){\n            host.suppressLayout(true)\n            try{host.removeAllViews();addSessionTimeline(host,mnv,ses)}finally{host.suppressLayout(false)}\n        }\n        employeeTimelineRealtimeRefresh={dates->\n            if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&(date.isBlank()||date in dates))renderTimeline()\n        }\n        renderTimeline()',
        '        val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()}\n        var renderedTimelineRevision:Long?=null\n        fun renderTimeline(){\n            val revision=date.takeIf{it.isNotBlank()}?.let{operationalStore.revision(it)}\n            if(renderedTimelineRevision!=null&&revision==renderedTimelineRevision)return\n            renderedTimelineRevision=revision\n            host.suppressLayout(true)\n            try{host.removeAllViews();addSessionTimeline(host,mnv,ses)}finally{host.suppressLayout(false)}\n        }\n        employeeTimelineRealtimeRefresh={dates->\n            if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&(date.isBlank()||date in dates))renderTimeline()\n        }\n        renderTimeline()',
        "qr-timeline-revision-dedupe",
    )
    write(p, s)


def bump_beta() -> tuple[str, int]:
    p = "app/build.gradle.kts"
    s = read(p)
    m_name = re.search(r'versionName = "(0\.4\.2-beta\.(\d+))"', s)
    m_code = re.search(r'versionCode = (\d+)\n\s*versionName = "0\.4\.2-beta\.\d+"', s)
    if not m_name or not m_code:
        raise SystemExit("BETA128_R3_PATCH_FAIL:version-parse")
    old_name = m_name.group(1)
    old_beta = int(m_name.group(2))
    old_code = int(m_code.group(1))
    new_name = f"0.4.2-beta.{old_beta + 1}"
    new_code = old_code + 1
    s = replace_once(s, f'versionCode = {old_code}\n            versionName = "{old_name}"', f'versionCode = {new_code}\n            versionName = "{new_name}"', "beta-version-bump")
    s += f'\n// Beta{old_beta + 1}: owner R3 drop-table/input refinement and no-op realtime render dedupe for labor, meal attendance and QR session timeline; Stable unchanged.\n'
    write(p, s)

    rp = "app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt"
    r = read(rp)
    r = replace_regex_once(r, r'const val VERSION_NAME = "[^"]+"', f'const val VERSION_NAME = "{new_name}"', "release-notes-version")
    r = replace_regex_once(
        r,
        r'    private val current = listOf\(.*?\n    \)',
        '    private val current = listOf(\n'
        '        "Nhận hàng Rớt: ưu tiên cột thời gian, thu gọn Chọn/Vị trí/Số kiện và giữ thời gian hiển thị đầy đủ.",\n'
        '        "Bỏ tiêu đề lặp cho Scan QR, DO, Số kiện và làm ô nhập nổi bật, dễ nhận biết hơn.",\n'
        '        "Công nhật và Điểm danh bỏ render trùng local/Service gây nhấp nháy; phần đầu danh sách được cập nhật ngay trong cùng khung hình.",\n'
        '        "QR vào/ra chỉ dựng lại timeline khi revision ngày thực sự thay đổi; Service reconcile nền không làm chớp chi tiết đang xem."\n'
        '    )',
        "release-notes-items",
        flags=re.S,
    )
    write(rp, r)
    return new_name, new_code


def reopen_registry_block(text: str, invariant_id: str) -> str:
    pattern = rf'(?ms)(^  - id: {re.escape(invariant_id)}\n)(.*?)(?=^  - id: |^impact_map:)'
    match = re.search(pattern, text)
    if not match:
        raise SystemExit(f"BETA128_R3_PATCH_FAIL:registry-block:{invariant_id}")
    block = match.group(1) + match.group(2)
    block = replace_regex_once(block, r'(?m)^    status: ACTIVE_PASS$', '    status: LOCKED_REQUIREMENT_PENDING_FIX', f"registry-status-{invariant_id}")
    block = re.sub(r'(?m)^    active_pass: true$', '    active_pass: false', block)
    if "owner_reopened_20260905" not in block:
        block += '    owner_reopened_20260905: "OWNER reports visible reload-like flicker; implementation must be fixed and re-verified before PASS."\n'
    return text[:match.start()] + block + text[match.end():]


def update_invariants() -> None:
    ids = ["LABOR-BULK-REALTIME-007", "ATTENDANCE-LOCAL-FIRST-003", "QR-INLINE-SHIFT-NAV-003", "UI-REALTIME-100MS-006"]
    q = "qa/stable_invariants.yml"
    s = read(q)
    for inv in ids:
        s = reopen_registry_block(s, inv)
    if "  - id: DROP-LAYOUT-INPUT-004\n" not in s:
        marker = "impact_map:\n"
        if marker not in s:
            raise SystemExit("BETA128_R3_PATCH_FAIL:impact-map-marker")
        block = (
            '  - id: DROP-LAYOUT-INPUT-004\n'
            '    status: LOCKED_REQUIREMENT_PENDING_FIX\n'
            '    scope: drop-receive-ui\n'
            '    rule: "Nhận hàng Rớt ưu tiên hiển thị đầy đủ thời gian bằng cách thu gọn Chọn/Vị trí/Số kiện; Scan QR/DO/Số kiện không lặp tiêu đề khi hint đã đủ nghĩa; ô nhập phải nổi bật và dễ nhận biết."\n'
            '    regression_minimum: [time_full_visible, compact_select_location_package_columns, no_redundant_input_labels, prominent_inputs]\n'
            '    owner_command: "CMD-20260905-003"\n'
            '    active_pass: false\n\n'
        )
        s = s.replace(marker, block + marker, 1)
    app_line = re.search(r'(?m)^  "app/\*\*": \[(.*)\]$', s)
    if app_line and "DROP-LAYOUT-INPUT-004" not in app_line.group(1):
        replacement = app_line.group(0)[:-1] + ", DROP-LAYOUT-INPUT-004]"
        s = s[:app_line.start()] + replacement + s[app_line.end():]
    write(q, s)

    d = "docs/STABLE_INVARIANTS.md"
    md = read(d)
    for inv in ids:
        pattern = rf'(?ms)^### {re.escape(inv)}(?: — [^\n]+)?\n.*?(?=^### |\Z)'
        m = re.search(pattern, md)
        if not m:
            raise SystemExit(f"BETA128_R3_PATCH_FAIL:docs-invariant:{inv}")
        block = m.group(0)
        block = re.sub(
            rf'(?m)^### {re.escape(inv)}(?: — [^\n]+)?$',
            f'### {inv} — LOCKED_REQUIREMENT_PENDING_FIX',
            block,
            count=1,
        )
        if "OWNER failure 2026-09-05 R3" not in block:
            block = block.rstrip() + '\n- OWNER failure 2026-09-05 R3: UI vẫn có nhấp nháy/reload-like; cần sửa và re-verify trước khi ACTIVE_PASS lại.\n\n'
        md = md[:m.start()] + block + md[m.end():]
    if "### DROP-LAYOUT-INPUT-004" not in md:
        md += (
            '\n### DROP-LAYOUT-INPUT-004 — LOCKED_REQUIREMENT_PENDING_FIX\n'
            '- Scope: Nhận hàng Rớt / UI nhập liệu + bảng\n'
            '- Rule: Thu gọn Chọn/Vị trí/Số kiện để ưu tiên cột Thời gian hiển thị đầy đủ; không lặp tiêu đề Scan QR/DO/Số kiện khi hint đã đủ nghĩa; ô nhập phải nổi bật, dễ nhìn.\n'
            '- Regression: 320x568 / 360x640 / 480x800; thời gian không ellipsis; không label lặp; input border/fill rõ; CRUD/pagination cũ không regress.\n'
            '- Authority: OWNER command CMD-20260905-003.\n'
        )
    write(d, md)


def update_scope(new_name: str, new_code: int) -> None:
    path = ROOT / "ops/OWNER_SCOPE_CURRENT.json"
    scope = json.loads(path.read_text(encoding="utf-8"))
    if int(scope.get("revision", 0)) != 2:
        raise SystemExit(f"BETA128_R3_PATCH_FAIL:unexpected-scope-revision:{scope.get('revision')}")
    scope["scope_id"] = "OWNER_20260905_R3_DROP_REALTIME_BETA128"
    scope["revision"] = 3
    scope["scope_status"] = "LOCKED_REQUIREMENT_PENDING_FIX"
    scope["migration_source"] = "OWNER CMD-20260905-003 over Beta127 accepted baseline"
    by_id = {x.get("requirement_id"): x for x in scope.get("requirements", [])}
    for rid in ("R2-07", "R2-09", "R2-10", "R2-11"):
        req = by_id.get(rid)
        if req is None:
            raise SystemExit(f"BETA128_R3_PATCH_FAIL:missing-requirement:{rid}")
        req["state"] = "LOCKED_REQUIREMENT_PENDING_FIX"
        req.pop("owner_result", None)
        if CMD_ID not in req["source_command_ids"]:
            req["source_command_ids"].append(CMD_ID)
    if "R3-12" not in by_id:
        scope["requirements"].append({
            "requirement_id": "R3-12",
            "checklist_number": 12,
            "title": "Nhận hàng Rớt – bố cục nhập và bảng",
            "acceptance": [
                "Thu hẹp cột Chọn, Vị trí và Số kiện để cột Thời gian rộng hơn; thời gian hiển thị đầy đủ, không bị che hoặc biến thành ba chấm.",
                "Scan QR, DO và Số kiện không có tiêu đề lặp phía trên khi nội dung/hint trong ô đã đủ nhận biết trường.",
                "Các ô nhập Scan QR, DO và Số kiện nổi bật, dễ nhìn nhưng không thay đổi logic nhập/quét hiện hành."
            ],
            "invariant_id": "DROP-LAYOUT-INPUT-004",
            "state": "LOCKED_REQUIREMENT_PENDING_FIX",
            "source_command_ids": [CMD_ID]
        })
    governance = scope.setdefault("governance", {})
    governance["status"] = "LOCKED_REQUIREMENT_PENDING_FIX"
    governance["technical_evidence"] = {}
    scope["release_binding"] = {
        "mode": "CANDIDATE_TARGET",
        "base_live_version_name": "0.4.2-beta.127",
        "target_version_name": new_name,
        "target_version_code": new_code,
    }
    path.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run([
        "python3", "tools/owner_scope_admin.py", "append-command",
        "--raw-text", OWNER_TEXT,
        "--event-type", "OWNER_REQUIREMENT_CHANGE",
        "--related", "R2-07,R2-09,R2-10,R2-11,R3-12",
        "--recorded-at", "2026-09-05T23:07:00+07:00",
        "--command-id", CMD_ID,
    ], cwd=ROOT, check=True)


def update_continuity() -> None:
    c = read("CURRENT_STATE.md")
    c = replace_regex_once(c, r'(?m)^- updated_at: .+$', '- updated_at: 2026-09-05T16:07:00Z', "current-updated")
    c = replace_regex_once(c, r'(?m)^- status: .+$', '- status: BETA128_OWNER_R3_IN_PROGRESS', "current-status")
    c = replace_regex_once(c, r'(?m)^- continuity_branch: .+$', f'- continuity_branch: {BRANCH}', "current-branch")
    c = replace_regex_once(c, r'(?m)^- owner_acceptance: .+$', '- owner_acceptance: BETA127_PREVIOUS_COMPLETE; R3_CURRENT_PENDING', "current-acceptance")
    c = replace_regex_once(c, r'(?m)^- owner_scope_continuity_policy: .+$', '- owner_scope_continuity_policy: OWNER_SCOPE_CONTINUITY_001 / LOCKED_REQUIREMENT_PENDING_FIX', "current-governance")
    c = replace_regex_once(c, r'(?m)^- next_action: .+$', '- next_action: VERIFY_BETA128_OWNER_R3_SOURCE_AND_RUN_REQUIRED_GATES', "current-next")
    write("CURRENT_STATE.md", c)

    h = read("docs/handovers/HANDOVER_CURRENT.md")
    h = replace_regex_once(h, r'(?m)^- time_utc: .+$', '- time_utc: 2026-09-05T16:07:00Z', "handover-time")
    h = replace_regex_once(h, r'(?m)^- branch: .+$', f'- branch: {BRANCH}', "handover-branch")
    h = replace_regex_once(h, r'Policy `OWNER_SCOPE_CONTINUITY_001` đang ở `[^`]+`\.', 'Policy `OWNER_SCOPE_CONTINUITY_001` đang ở `LOCKED_REQUIREMENT_PENDING_FIX`.', "handover-governance")
    h = replace_regex_once(h, r'(?ms)(## NEXT_ACTION\n).*?\Z', r'\1VERIFY_BETA128_OWNER_R3_SOURCE_AND_RUN_REQUIRED_GATES\n', "handover-next")
    write("docs/handovers/HANDOVER_CURRENT.md", h)


def main() -> None:
    patch_drop()
    patch_attendance()
    patch_operations()
    new_name, new_code = bump_beta()
    update_invariants()
    update_scope(new_name, new_code)
    update_continuity()
    # Continuity edits after owner_scope_admin preserve its freshly written canonical pointers.
    subprocess.run(["python3", "tools/owner_scope_guard_v2.py", "--base-ref", "beta/current"], cwd=ROOT, check=True)
    print(json.dumps({"status": "BETA128_R3_PATCH_APPLIED", "version": new_name, "version_code": new_code}, ensure_ascii=False))


if __name__ == "__main__":
    main()
