#!/usr/bin/env python3
from pathlib import Path
import ast, base64, re, zlib

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / 'tools/apply_beta73_owner_scope_payload.py'
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'

# Normalize only the known Beta72 audit renderer before the original Beta73 materializer runs.
o = OPS.read_text(encoding='utf-8')
old = '''            if(type=="RESOURCE_CHANGE"){val delta=sessionWorkChangeDetail(p);if(delta.isNotBlank())return delta;val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();return "Trước: ${sessionWorkSnapshotDetail(before).ifBlank{sessionWorkDetail(before).ifBlank{"—"}}} • Sau: ${sessionWorkSnapshotDetail(after).ifBlank{sessionWorkDetail(after).ifBlank{"—"}}}"}'''
new = '''            if(type=="RESOURCE_CHANGE"){val delta=sessionWorkChangeDetail(p);val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();val beforeText=sessionWorkSnapshotDetail(before).ifBlank{sessionWorkDetail(before).ifBlank{"—"}};val afterText=sessionWorkSnapshotDetail(after).ifBlank{sessionWorkDetail(after).ifBlank{"—"}};return "Trước cập nhật: $beforeText\\nSau cập nhật: $afterText${if(delta.isNotBlank())"\\nThay đổi: $delta" else ""}"}'''
if 'Trước cập nhật:' not in o:
    if old not in o:
        raise SystemExit('beta73 fallback audit anchor drift')
    OPS.write_text(o.replace(old,new,1),encoding='utf-8')

wrapper = ORIG.read_text(encoding='utf-8')
m = re.search(r"b85decode\((['\"])(.+?)\1\)", wrapper, re.S)
if not m:
    raise SystemExit('beta73 encoded payload missing')
payload = ast.literal_eval(m.group(1) + m.group(2) + m.group(1))
src = zlib.decompress(base64.b85decode(payload)).decode('utf-8')

tree = ast.parse(src, filename='apply_beta73_owner_scope.inner.py')
class AuditGuardFix(ast.NodeTransformer):
    def __init__(self): self.fixed=0
    def visit_Raise(self,node):
        self.generic_visit(node)
        call=node.exc
        if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Name) or call.func.id!='SystemExit' or not call.args:
            return node
        msg=call.args[0]
        label_expr=None
        if isinstance(msg,ast.JoinedStr):
            const=''.join(v.value for v in msg.values if isinstance(v,ast.Constant) and isinstance(v.value,str))
            vals=[v.value for v in msg.values if isinstance(v,ast.FormattedValue)]
            if 'anchor drift:' in const and vals: label_expr=vals[-1]
        if label_expr is None:
            return node
        self.fixed+=1
        test=ast.Compare(left=ast.Call(func=ast.Name(id='str',ctx=ast.Load()),args=[label_expr],keywords=[]),ops=[ast.Eq()],comparators=[ast.Constant(value='resource audit detail')])
        return ast.If(test=test,body=[ast.Expr(value=ast.Call(func=ast.Name(id='print',ctx=ast.Load()),args=[ast.Constant(value='beta73 fallback: resource audit detail')],keywords=[]))],orelse=[node])
fix=AuditGuardFix();tree=fix.visit(tree);ast.fix_missing_locations(tree)
if fix.fixed<1:
    raise SystemExit('beta73 dynamic anchor guard not found')
exec(compile(tree,'apply_beta73_owner_scope.inner.py','exec'),{'__name__':'__main__','__file__':str(ORIG)})

if 'Trước cập nhật:' not in OPS.read_text(encoding='utf-8'):
    raise SystemExit('beta73 audit normalization missing after materialize')
