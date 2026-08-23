from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text()
fixes={
    '    private fun employeeScan()    private fun employeeScan() {':'    private fun employeeScan() {',
    '    private fun sessionWorkEditor(    private fun sessionWorkEditor(ctx:JSONObject,mode:String){':'    private fun sessionWorkEditor(ctx:JSONObject,mode:String){',
    '    private fun editableTime(    private fun editableTime(iso:String):String=':'    private fun editableTime(iso:String):String=',
}
for old,new in fixes.items():
    if old not in s:
        raise SystemExit(f'generated boundary anchor missing: {old[:60]}')
    s=s.replace(old,new,1)
p.write_text(s)
