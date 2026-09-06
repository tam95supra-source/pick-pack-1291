#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def ensure_once(path:str,old:str,target:str,label:str):
    p=ROOT/path;s=p.read_text(encoding='utf-8')
    if target in s:
        if s.count(target)!=1:
            raise SystemExit(f'R5_BETA129_TARGET_NOT_UNIQUE:{label}:{s.count(target)}')
        return False
    if old not in s:
        raise SystemExit(f'R5_BETA129_ANCHOR_MISSING:{label}:{old[:80]}')
    if s.count(old)!=1:
        raise SystemExit(f'R5_BETA129_ANCHOR_NOT_UNIQUE:{label}:{s.count(old)}')
    p.write_text(s.replace(old,target,1),encoding='utf-8')
    return True

# Android source change => Beta129. Stable block is never modified.
ensure_once(
    'app/build.gradle.kts',
    '            versionCode = 134\n            versionName = "0.4.2-beta.128"',
    '            versionCode = 135\n            versionName = "0.4.2-beta.129"',
    'beta-version',
)
ensure_once(
    'app/build.gradle.kts',
    '// Beta127: closes OWNER R2 visual false-pass gaps: exact local-data delete wording, visible manpower report title, labor-detail ordering/empty state, and behavioral regression gates. Stable unchanged.',
    '// Beta129: R5 quota/realtime architecture: O(1) revision status, indexed delta, one Android orchestrator, delta-only web reconcile, coalesced wake, terminal outboxes, batched Sheets replication and dynamic quota circuit. Stable unchanged.\n// Beta127: closes OWNER R2 visual false-pass gaps: exact local-data delete wording, visible manpower report title, labor-detail ordering/empty state, and behavioral regression gates. Stable unchanged.',
    'beta129-comment',
)

notes=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt'
s=notes.read_text(encoding='utf-8')
notes_old='''    const val VERSION_NAME = "0.4.2-beta.128"\n    private val current = listOf(\n        "Nhận hàng Rớt: ưu tiên cột thời gian, thu gọn Chọn/Vị trí/Số kiện và giữ thời gian hiển thị đầy đủ.",\n        "Bỏ tiêu đề lặp cho Scan QR, DO, Số kiện và làm ô nhập nổi bật, dễ nhận biết hơn.",\n        "Công nhật và Điểm danh bỏ render trùng local/Service gây nhấp nháy; phần đầu danh sách được cập nhật ngay trong cùng khung hình.",\n        "QR vào/ra chỉ dựng lại timeline khi revision ngày thực sự thay đổi; Service reconcile nền không làm chớp chi tiết đang xem."\n    )'''
notes_target='''    const val VERSION_NAME = "0.4.2-beta.129"\n    private val current = listOf(\n        "Realtime: cập nhật theo phần thay đổi, không tải lại toàn bộ màn hình khi dữ liệu nền đồng bộ.",\n        "Đồng bộ: dùng revision và delta có chỉ mục, gom yêu cầu trùng và chỉ một bộ điều phối nền trên PDA.",\n        "Quota: gom thông báo, batch đồng bộ Google Sheets và giới hạn tác vụ phụ theo ngân sách động để giữ trong mức miễn phí.",\n        "An toàn dữ liệu: mutation/outbox canonical, ACK fence và cơ chế retry/khôi phục vẫn được giữ nguyên."\n    )'''
if notes_target not in s:
    if notes_old not in s: raise SystemExit('R5_BETA129_RELEASE_NOTES_ANCHOR_MISSING')
    notes.write_text(s.replace(notes_old,notes_target,1),encoding='utf-8')
elif s.count(notes_target)!=1:
    raise SystemExit(f'R5_BETA129_RELEASE_NOTES_TARGET_NOT_UNIQUE:{s.count(notes_target)}')

# Compile R5 performance instrumentation into the separately-signed verification harness.
build=ROOT/'tools/build_beta83_verify_harness.sh';s=build.read_text(encoding='utf-8')
copy_old='cp tools/Beta83UiChecksInstrumentation.java "$W/src/vn/pickpack1291/verify/"'
copy_target=copy_old+'\ncp tools/R5PerfInstrumentation.java "$W/src/vn/pickpack1291/verify/"'
if copy_target not in s:
    if s.count(copy_old)!=1: raise SystemExit('R5_HARNESS_COPY_ANCHOR_MISSING')
    s=s.replace(copy_old,copy_target,1)
manifest_old='  <instrumentation android:name=".Beta83UiChecksInstrumentation" android:targetPackage="vn.pickpack1291.app.beta.publicbeta" android:functionalTest="true" android:handleProfiling="false"/>'
manifest_target=manifest_old+'\n  <instrumentation android:name=".R5PerfInstrumentation" android:targetPackage="vn.pickpack1291.app.beta.publicbeta" android:functionalTest="true" android:handleProfiling="false"/>'
if manifest_target not in s:
    if s.count(manifest_old)!=1: raise SystemExit('R5_HARNESS_MANIFEST_ANCHOR_MISSING')
    s=s.replace(manifest_old,manifest_target,1)
build.write_text(s,encoding='utf-8')

# Run exact-candidate performance once, offline, before visual/functional matrix.
matrix=ROOT/'tools/beta83_verify_matrix.sh';s=matrix.read_text(encoding='utf-8')
matrix_old='''adb install -r "$APK" >"$OUT/install-candidate.txt";adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-harness.txt"\nfor spec in '320 568 160' '360 640 180' '480 800 240'; do'''
matrix_target='''adb install -r "$APK" >"$OUT/install-candidate.txt";adb install -r "$VERIFY_HARNESS_APK" >"$OUT/install-harness.txt"\nif [[ "$VISUAL_ONLY" != "true" ]]; then\n  adb shell wm size 360x640 >/dev/null;adb shell wm density 180 >/dev/null\n  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true;adb shell pm clear "$PKG" >/dev/null\n  adb shell svc wifi disable >/dev/null 2>&1 || true;adb shell svc data disable >/dev/null 2>&1 || true\n  set +e\n  timeout 120s adb shell am instrument -w -r vn.pickpack1291.verify/.R5PerfInstrumentation >"$OUT/r5-local-ui-instrument.txt" 2>&1\n  PRC=$?\n  set -e\n  test "$PRC" = 0;grep -Fq 'INSTRUMENTATION_CODE: 0' "$OUT/r5-local-ui-instrument.txt";grep -Fq 'R5_LOCAL_UI_P95_PASS' "$OUT/r5-local-ui-instrument.txt"\n  P50=$(sed -n 's/.*r5_local_ui_p50_ms=\\([0-9][0-9]*\\).*/\\1/p' "$OUT/r5-local-ui-instrument.txt" | tail -n1)\n  P95=$(sed -n 's/.*r5_local_ui_p95_ms=\\([0-9][0-9]*\\).*/\\1/p' "$OUT/r5-local-ui-instrument.txt" | tail -n1)\n  P99=$(sed -n 's/.*r5_local_ui_p99_ms=\\([0-9][0-9]*\\).*/\\1/p' "$OUT/r5-local-ui-instrument.txt" | tail -n1)\n  MAX=$(sed -n 's/.*r5_local_ui_max_ms=\\([0-9][0-9]*\\).*/\\1/p' "$OUT/r5-local-ui-instrument.txt" | tail -n1)\n  test -n "$P50" -a -n "$P95" -a -n "$P99" -a -n "$MAX";test "$P95" -le 100\n  jq -nc --argjson p50 "$P50" --argjson p95 "$P95" --argjson p99 "$P99" --argjson max "$MAX" '{status:"PASS",samples:50,p50_ms:$p50,p95_ms:$p95,p99_ms:$p99,max_ms:$max,target_p95_ms:100,measurement:"applyDayDelta_plus_employeeTimelineRealtimeRefresh_to_accessibility_visible",network:"OFFLINE"}' > "$OUT/r5-local-ui-perf.json"\nfi\nfor spec in '320 568 160' '360 640 180' '480 800 240'; do'''
if 'R5_LOCAL_UI_P95_PASS' not in s:
    if matrix_old not in s: raise SystemExit('R5_MATRIX_PERF_ANCHOR_MISSING')
    s=s.replace(matrix_old,matrix_target,1)
elif s.count('R5_LOCAL_UI_P95_PASS')!=1:
    raise SystemExit(f'R5_MATRIX_PERF_TARGET_NOT_UNIQUE:{s.count("R5_LOCAL_UI_P95_PASS")}')
matrix.write_text(s,encoding='utf-8')

# Final target verification. This makes reruns safe and prevents accidental Beta130 bump.
b=(ROOT/'app/build.gradle.kts').read_text(encoding='utf-8')
notes_now=notes.read_text(encoding='utf-8')
build_now=build.read_text(encoding='utf-8')
matrix_now=matrix.read_text(encoding='utf-8')
assert 'versionCode = 135\n            versionName = "0.4.2-beta.129"' in b
assert 'Beta129: R5 quota/realtime architecture' in b
assert notes_target in notes_now
assert 'cp tools/R5PerfInstrumentation.java' in build_now
assert '.R5PerfInstrumentation' in build_now
assert 'R5_LOCAL_UI_P95_PASS' in matrix_now
print('R5_BETA129_PREPARE_PASS')
