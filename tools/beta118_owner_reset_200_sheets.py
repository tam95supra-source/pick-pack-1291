#!/usr/bin/env python3
import argparse,json,pathlib,urllib.parse,urllib.request

SHEETS={
 'RA - VÀO TRONG CA':('A:V',(19,)),
 'CÔNG NHẬT':('A:W',(19,20)),
 'LỊCH SỬ NGHIỆP VỤ':('A:M',(10,)),
 'THÔNG TIN USER CỦA NLĐ':('A:K',(10,)),
 '__M1_SERVICE_REPLICA':('A:T',(0,)),
}

def req(url,token,method='GET',body=None):
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    r=urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=60) as x:return json.loads(x.read().decode() or '{}')

def main():
    p=argparse.ArgumentParser();p.add_argument('--token',required=True);p.add_argument('--spreadsheet',required=True);p.add_argument('--event-ids',required=True);p.add_argument('--out',required=True);p.add_argument('--delete',action='store_true');a=p.parse_args()
    ids={x.strip() for x in pathlib.Path(a.event_ids).read_text().splitlines() if x.strip()};assert ids
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    base='https://sheets.googleapis.com/v4/spreadsheets/'+urllib.parse.quote(a.spreadsheet,safe='')
    meta=req(base+'?fields=sheets.properties(sheetId,title)',a.token)
    props={str(x.get('properties',{}).get('title','')):x.get('properties',{}) for x in meta.get('sheets',[])}
    backup={};delete_requests=[]
    for title,(rng,cols) in SHEETS.items():
        if title not in props: continue
        a1="'%s'!%s"%(title.replace("'","''"),rng)
        url=base+'/values/'+urllib.parse.quote(a1,safe='')+'?valueRenderOption=FORMATTED_VALUE'
        vals=req(url,a.token).get('values',[])
        matches=[]
        for i,row in enumerate(vals[1:],start=2):
            if any((c<len(row) and str(row[c]).strip() in ids) for c in cols):matches.append((i,row))
        backup[title]={'count':len(matches),'rows':matches}
        sid=int(props[title]['sheetId'])
        for rownum,_ in sorted(matches,reverse=True):
            delete_requests.append({'deleteDimension':{'range':{'sheetId':sid,'dimension':'ROWS','startIndex':rownum-1,'endIndex':rownum}}})
    (out/'sheet-target-rows.json').write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')
    if a.delete and delete_requests:
        req(base+':batchUpdate',a.token,'POST',{'requests':delete_requests})
    if a.delete:
        leftovers={}
        for title,(rng,cols) in SHEETS.items():
            if title not in props: continue
            a1="'%s'!%s"%(title.replace("'","''"),rng)
            vals=req(base+'/values/'+urllib.parse.quote(a1,safe='')+'?valueRenderOption=FORMATTED_VALUE',a.token).get('values',[])
            bad=[]
            for i,row in enumerate(vals[1:],start=2):
                if any((c<len(row) and str(row[c]).strip() in ids) for c in cols):bad.append(i)
            leftovers[title]=bad
        (out/'sheet-cleanup-readback.json').write_text(json.dumps(leftovers,ensure_ascii=False,indent=2),encoding='utf-8')
        if any(leftovers.values()):raise SystemExit('SHEET_TARGET_EVENT_ROWS_REMAIN:'+repr(leftovers))
    print(json.dumps({'status':'PASS','target_event_ids':len(ids),'sheet_matches':{k:v['count'] for k,v in backup.items()},'deleted':bool(a.delete)},ensure_ascii=False))
if __name__=='__main__':main()
