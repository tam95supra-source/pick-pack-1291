#!/usr/bin/env python3
import argparse, json, struct, tempfile
from pathlib import Path

PNG_SIG=b'\x89PNG\r\n\x1a\n'

class VerifyError(Exception): pass

def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e:
        raise VerifyError(f'JSON_INVALID:{path}:{e}')

def png_size(path: Path):
    b=path.read_bytes()[:24]
    if len(b)<24 or b[:8]!=PNG_SIG or b[12:16]!=b'IHDR':
        raise VerifyError(f'PNG_INVALID:{path}')
    return struct.unpack('>II',b[16:24])

def parse_viewport(tag):
    try:
        w,h=tag.lower().split('x',1)
        w=int(w);h=int(h)
        if w<=0 or h<=0: raise ValueError
        return w,h
    except Exception:
        raise VerifyError(f'VIEWPORT_INVALID:{tag}')

def verify(receipt_path, evidence_dir, request_path):
    receipt=load_json(receipt_path)
    request=load_json(request_path)
    root=Path(evidence_dir)
    if receipt.get('status')!='PASS': raise VerifyError('RECEIPT_STATUS_NOT_PASS')
    if receipt.get('human_inspection_required') is not True: raise VerifyError('HUMAN_INSPECTION_NOT_REQUIRED')
    if request.get('human_visual_pass') is not True: raise VerifyError('HUMAN_VISUAL_NOT_PASS')
    required=request.get('human_visual_sizes')
    visual=receipt.get('visual_sizes')
    if not isinstance(required,list) or not required or any(not isinstance(x,str) or not x for x in required):
        raise VerifyError('REQUEST_VISUAL_SIZES_INVALID')
    if not isinstance(visual,list) or sorted(visual)!=sorted(required):
        raise VerifyError(f'VIEWPORT_SET_MISMATCH:receipt={visual}:request={required}')
    count=receipt.get('screenshot_count')
    if not isinstance(count,int) or isinstance(count,bool) or count<=0:
        raise VerifyError('RECEIPT_SCREENSHOT_COUNT_INVALID')
    pngs=[]
    for tag in required:
        d=root/tag
        files=sorted(d.glob('*.png')) if d.is_dir() else []
        if not files: raise VerifyError(f'VIEWPORT_EVIDENCE_MISSING:{tag}')
        expected_size=parse_viewport(tag)
        for p in files:
            actual=png_size(p)
            if actual!=expected_size:
                raise VerifyError(f'PNG_SIZE_MISMATCH:{p.name}:{actual}!={expected_size}')
        pngs.extend(files)
    actual_count=len(pngs)
    if actual_count!=count:
        raise VerifyError(f'SCREENSHOT_COUNT_MISMATCH:receipt={count}:actual={actual_count}')
    summary=root/'visual-summary.txt'
    if not summary.is_file(): raise VerifyError('VISUAL_SUMMARY_MISSING')
    kv={}
    for line in summary.read_text(encoding='utf-8').splitlines():
        if '=' in line:
            k,v=line.split('=',1);kv[k.strip()]=v.strip()
    try: summary_count=int(kv.get('screenshots',''))
    except Exception: raise VerifyError('VISUAL_SUMMARY_COUNT_INVALID')
    if summary_count!=count: raise VerifyError(f'VISUAL_SUMMARY_COUNT_MISMATCH:summary={summary_count}:receipt={count}')
    summary_sizes=[x for x in kv.get('sizes','').split(',') if x]
    if sorted(summary_sizes)!=sorted(required):
        raise VerifyError(f'VISUAL_SUMMARY_SIZES_MISMATCH:summary={summary_sizes}:request={required}')
    return {'status':'PASS','screenshot_count':count,'visual_sizes':sorted(required),'actual_png_count':actual_count}

def fake_png(path,w,h):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(PNG_SIG+b'\x00\x00\x00\x0dIHDR'+struct.pack('>II',w,h)+b'\x08\x02\x00\x00\x00')

def fixture(root,count,per_sizes,receipt_sizes=None,request_sizes=None,human=True,summary_count=None,summary_sizes=None):
    req_sizes=request_sizes or ['320x568','360x640','480x800']
    rec_sizes=receipt_sizes or list(req_sizes)
    request={'human_visual_pass':human,'human_visual_sizes':req_sizes}
    receipt={'status':'PASS','human_inspection_required':True,'screenshot_count':count,'visual_sizes':rec_sizes}
    (root/'request.json').write_text(json.dumps(request),encoding='utf-8')
    (root/'receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
    for tag,n in per_sizes.items():
        w,h=parse_viewport(tag)
        for i in range(n): fake_png(root/tag/f'{tag}-{i:02d}.png',w,h)
    sc=count if summary_count is None else summary_count
    ss=req_sizes if summary_sizes is None else summary_sizes
    (root/'visual-summary.txt').write_text('screenshots='+str(sc)+'\nsizes='+','.join(ss)+'\nhuman_inspection_required=true\n',encoding='utf-8')
    return root/'receipt.json',root,root/'request.json'

def expect_fail(name,fn):
    try: fn()
    except VerifyError: return
    raise AssertionError(name+' expected failure')

def self_test():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td)
        a=base/'legacy26';a.mkdir();args=fixture(a,26,{'320x568':14,'360x640':6,'480x800':6});verify(*args)
        b=base/'beta101';b.mkdir();args=fixture(b,35,{'320x568':17,'360x640':9,'480x800':9});verify(*args)
        c=base/'count-mismatch';c.mkdir();args=fixture(c,35,{'320x568':16,'360x640':9,'480x800':9});expect_fail('count mismatch',lambda:verify(*args))
        d=base/'missing-view';d.mkdir();args=fixture(d,26,{'320x568':14,'360x640':12});expect_fail('missing viewport',lambda:verify(*args))
        e=base/'viewport-mismatch';e.mkdir();args=fixture(e,26,{'320x568':14,'360x640':6,'480x800':6},receipt_sizes=['320x568','360x640']);expect_fail('viewport mismatch',lambda:verify(*args))
        f=base/'summary-mismatch';f.mkdir();args=fixture(f,35,{'320x568':17,'360x640':9,'480x800':9},summary_count=34);expect_fail('summary mismatch',lambda:verify(*args))
        g=base/'human-fail';g.mkdir();args=fixture(g,35,{'320x568':17,'360x640':9,'480x800':9},human=False);expect_fail('human gate',lambda:verify(*args))
    print('VERIFY_BETA_VISUAL_RECEIPT_SELF_TEST_PASS')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--receipt')
    p.add_argument('--evidence-dir')
    p.add_argument('--request')
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    try:
        if a.self_test:
            self_test();return 0
        if not (a.receipt and a.evidence_dir and a.request): p.error('--receipt --evidence-dir --request required')
        print(json.dumps(verify(a.receipt,a.evidence_dir,a.request),sort_keys=True))
        return 0
    except VerifyError as e:
        print('VERIFY_BETA_VISUAL_RECEIPT_FAIL:'+str(e),file=__import__('sys').stderr)
        return 1
if __name__=='__main__': raise SystemExit(main())
