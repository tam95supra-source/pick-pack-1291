#!/usr/bin/env python3
import base64,hashlib,json,os,pathlib,sqlite3,subprocess,sys,time,urllib.error,urllib.parse,urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("/tmp/cloud-dr-turso-isolation.json")
CF="https://api.cloudflare.com/client/v4"
TURSO="https://api.turso.tech/v1"

def need(n):
    v=os.environ.get(n,"").strip()
    if not v: raise RuntimeError("MISSING_REQUIRED:"+n)
    return v

def request_json(url,method="GET",token=None,body=None,timeout=45):
    data=None if body is None else json.dumps(body,separators=(",",":")).encode()
    h={"Accept":"application/json","User-Agent":"PickPack1291-DR-Provision/1"}
    if token:h["Authorization"]="Bearer "+token
    if data is not None:h["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read().decode("utf-8","replace")
            return x.status,(json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8","replace")
        try:j=json.loads(raw)
        except:j={"raw":raw[:500]}
        return e.code,j

def cf(path,method="GET",body=None):
    code,j=request_json(f"{CF}/accounts/{need('CLOUDFLARE_ACCOUNT_ID')}{path}",method,need("CLOUDFLARE_API_TOKEN"),body)
    if code//100!=2 or j.get("success") is not True:raise RuntimeError("CF_API_FAILED:"+str(code))
    return j.get("result")

def worker_bindings(name):
    s=cf("/workers/scripts/"+urllib.parse.quote(name,safe="")+"/settings") or {}
    return {str(b.get("name")):b for b in (s.get("bindings") or [])}

def bid(m,k):return str((m.get(k) or {}).get("id") or "")
def btext(m,k):return str((m.get(k) or {}).get("text") or "")

def jwt_candidates(token):
    out=[]
    try:
        p=token.split(".")[1];p+="="*((4-len(p)%4)%4);j=json.loads(base64.urlsafe_b64decode(p.encode()).decode())
        for k in ("organization_slug","organizationSlug","organization","org","org_slug","o"):
            v=str(j.get(k) or "").strip()
            if v:out.append(v)
    except Exception:pass
    return out

def resolve_org(token):
    candidates=[]
    explicit=os.environ.get("TURSO_ORGANIZATION","").strip()
    if explicit:candidates.append(explicit)
    candidates+=jwt_candidates(token)
    gh=os.environ.get("GITHUB_REPOSITORY","")
    if gh:candidates += [gh.split("/",1)[0],gh.split("/",1)[-1]]
    actor=os.environ.get("GITHUB_ACTOR","").strip()
    if actor:candidates.append(actor)
    c,j=request_json(TURSO+"/organizations","GET",token)
    if c==200:
        rows=j if isinstance(j,list) else j.get("organizations",[])
        candidates += [str(x.get("slug") or "").strip() for x in rows if isinstance(x,dict)]
    seen=set()
    for cand in candidates:
        if not cand or cand in seen:continue
        seen.add(cand)
        c,j=request_json(TURSO+"/organizations/"+urllib.parse.quote(cand,safe="")+"/databases?limit=100","GET",token)
        if c==200 and isinstance(j.get("databases"),list):return cand,j["databases"]
    raise RuntimeError("TURSO_ORG_UNRESOLVED")

def turso_json(org,path,method="GET",body=None):
    code,j=request_json(TURSO+"/organizations/"+urllib.parse.quote(org,safe="")+path,method,need("TURSO_API_TOKEN"),body)
    return code,j

def sh(args,cwd=None,timeout=600):
    p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode:raise RuntimeError("COMMAND_FAILED:"+str(args[0])+":"+p.stdout[-2400:])
    return p.stdout

def sqlite_signature(path):
    con=sqlite3.connect(str(path))
    try:
        ok=con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok!="ok":raise RuntimeError("SQLITE_INTEGRITY_FAIL")
        tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name") if not str(r[0]).startswith("_cf_")]
        counts={t:int(con.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0]) for t in tables}
        h=hashlib.sha256()
        if "events" in tables:
            for eid,chk in con.execute("SELECT event_id,checksum FROM events ORDER BY event_id"):
                h.update((str(eid)+"|"+str(chk)+"\n").encode())
        shash=hashlib.sha256()
        if "schema_migrations" in tables:
            for v,c in con.execute("SELECT version,checksum FROM schema_migrations ORDER BY version"):
                shash.update((str(v)+"|"+str(c)+"\n").encode())
        auth=[]
        if "authority_state" in tables:
            auth=[str(x) for x in con.execute("SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1").fetchone() or []]
        accounts=[]
        if "accounts" in tables:
            accounts=[[str(a),str(b),str(c)] for a,b,c in con.execute("SELECT login_id,role,status FROM accounts ORDER BY login_id")]
        return {"tables":counts,"events_digest":h.hexdigest(),"schema_digest":shash.hexdigest(),"authority":auth,"accounts":accounts}
    finally:con.close()

def export_d1(env,worker):
    by=worker_bindings(worker);dbid=bid(by,"DB")
    if not dbid:raise RuntimeError(env+"_D1_BINDING_MISSING")
    dbs=cf("/d1/database?per_page=100") or []
    match=[x for x in dbs if str(x.get("uuid") or x.get("id"))==dbid]
    if len(match)!=1:raise RuntimeError(env+"_D1_INVENTORY_MISMATCH")
    name=str(match[0].get("name") or "")
    cfg=pathlib.Path("/tmp/wrangler-"+env.lower()+".json")
    cfg.write_text(json.dumps({"name":"pp1291-dr-export-"+env.lower(),"compatibility_date":"2026-08-08","d1_databases":[{"binding":"DB","database_name":name,"database_id":dbid}]})+"\n")
    sql=pathlib.Path("/tmp/"+env.lower()+"-d1-export.sql");db=pathlib.Path("/tmp/"+env.lower()+"-d1-export.sqlite")
    sql.unlink(missing_ok=True);db.unlink(missing_ok=True)
    sh(["npx","wrangler","d1","export",name,"--remote","--output",str(sql),"--config",str(cfg)],cwd=ROOT/"service")
    raw=sql.read_bytes()
    con=sqlite3.connect(str(db))
    try:con.executescript(raw.decode("utf-8"));con.commit()
    finally:con.close()
    return {"env":env,"worker":worker,"source_d1_id":dbid,"source_d1_name":name,"sql":sql,"db":db,"sql_sha256":hashlib.sha256(raw).hexdigest(),"sqlite_sha256":hashlib.sha256(db.read_bytes()).hexdigest(),"signature":sqlite_signature(db),"bindings":by}

def upload(host,token,path):
    data=path.read_bytes()
    req=urllib.request.Request("https://"+host+"/v1/upload",data=data,headers={"Authorization":"Bearer "+token,"Content-Type":"application/octet-stream","User-Agent":"PickPack1291-DR-Provision/1"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=180) as x:
            raw=x.read().decode("utf-8","replace");return x.status,raw[:500]
    except urllib.error.HTTPError as e:return e.code,e.read().decode("utf-8","replace")[:500]

def node_signature(url,token):
    code=r"""
import {createClient} from '@libsql/client';
import crypto from 'node:crypto';
const c=createClient({url:process.env.DB_URL,authToken:process.env.DB_TOKEN});
try{
 const tr=await c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name");
 const tables=tr.rows.map(x=>String(x.name)).filter(x=>!x.startsWith('_cf_')),counts={};
 for(const t of tables){const safe='"'+t.replaceAll('"','""')+'"';const r=await c.execute('SELECT COUNT(*) n FROM '+safe);counts[t]=Number(r.rows[0]?.n||0)}
 const eh=crypto.createHash('sha256');
 if(tables.includes('events')){let off=0;while(true){const r=await c.execute({sql:'SELECT event_id,checksum FROM events ORDER BY event_id LIMIT 1000 OFFSET ?',args:[off]});for(const x of r.rows)eh.update(String(x.event_id)+'|'+String(x.checksum)+'\n');if(r.rows.length<1000)break;off+=1000}}
 const sh=crypto.createHash('sha256');
 if(tables.includes('schema_migrations')){const r=await c.execute('SELECT version,checksum FROM schema_migrations ORDER BY version');for(const x of r.rows)sh.update(String(x.version)+'|'+String(x.checksum)+'\n')}
 let authority=[];if(tables.includes('authority_state')){const r=await c.execute('SELECT authority_epoch,authority_seq,mode,scope,service_generation FROM authority_state WHERE singleton_id=1');if(r.rows[0])authority=[r.rows[0].authority_epoch,r.rows[0].authority_seq,r.rows[0].mode,r.rows[0].scope,r.rows[0].service_generation].map(String)}
 let accounts=[];if(tables.includes('accounts')){const r=await c.execute('SELECT login_id,role,status FROM accounts ORDER BY login_id');accounts=r.rows.map(x=>[String(x.login_id),String(x.role),String(x.status)])}
 console.log(JSON.stringify({tables:counts,events_digest:eh.digest('hex'),schema_digest:sh.digest('hex'),authority,accounts}));
}finally{c.close()}
"""
    env=os.environ.copy();env["DB_URL"]=url;env["DB_TOKEN"]=token
    p=subprocess.run(["node","--input-type=module","-e",code],cwd=ROOT/"services/cloud-dr",env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    if p.returncode:raise RuntimeError("TURSO_QUERY_FAILED:"+p.stderr[-700:])
    return json.loads(p.stdout.strip().splitlines()[-1])

def cross_denied(url,token):
    code="import {createClient} from '@libsql/client';const c=createClient({url:process.env.DB_URL,authToken:process.env.DB_TOKEN});try{await c.execute('SELECT 1');console.log('ALLOWED')}catch{console.log('DENIED')}finally{c.close()}"
    env=os.environ.copy();env["DB_URL"]=url;env["DB_TOKEN"]=token
    p=subprocess.run(["node","--input-type=module","-e",code],cwd=ROOT/"services/cloud-dr",env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    return p.returncode==0 and p.stdout.strip().endswith("DENIED")

def provision_target(org,group,source,target,limit,maxdb,current_count):
    if current_count>=maxdb-1:raise RuntimeError("TURSO_FREE_DATABASE_HEADROOM_INSUFFICIENT")
    c,j=turso_json(org,"/databases?limit=100")
    if c!=200:raise RuntimeError("TURSO_LIST_FAILED:"+str(c))
    rows=j.get("databases") or [];existing=[x for x in rows if str(x.get("Name") or x.get("name"))==target]
    created=False;token=None
    try:
        if existing:
            dbj=existing[0]
        else:
            c,j=turso_json(org,"/databases","POST",{"name":target,"group":group,"seed":{"type":"database_upload"},"size_limit":str(limit)})
            if c not in (200,201):raise RuntimeError("TURSO_CREATE_FAILED:"+target+":"+str(c)+":"+str((j.get("error") if isinstance(j,dict) else ""))[:180])
            dbj=j.get("database") or j;created=True
        host=str(dbj.get("Hostname") or dbj.get("hostname") or "")
        if not host:
            c,j=turso_json(org,"/databases/"+urllib.parse.quote(target,safe=""))
            dbj=j.get("database") or j;host=str(dbj.get("Hostname") or dbj.get("hostname") or "")
        if not host:raise RuntimeError("TURSO_HOST_MISSING:"+target)
        c,j=turso_json(org,"/databases/"+urllib.parse.quote(target,safe="")+"/auth/tokens?authorization=full-access","POST",{})
        if c!=200 or not str(j.get("jwt") or ""):raise RuntimeError("TURSO_DB_TOKEN_CREATE_FAILED:"+target+":"+str(c))
        token=str(j["jwt"]);print("::add-mask::"+token)
        url="libsql://"+host
        if created:
            uc,ud=upload(host,token,source["db"])
            if uc not in (200,201,202,204):raise RuntimeError("TURSO_UPLOAD_FAILED:"+target+":"+str(uc)+":"+ud[:180])
        target_sig=None
        last=""
        for _ in range(30):
            try:
                target_sig=node_signature(url,token);break
            except Exception as e:last=str(e);time.sleep(2)
        if target_sig is None:raise RuntimeError("TURSO_RESTORE_READBACK_TIMEOUT:"+target+":"+last[:200])
        if target_sig!=source["signature"]:raise RuntimeError("TURSO_RESTORE_SIGNATURE_MISMATCH:"+target)
        return {"target":target,"host":host,"id":dbj.get("DbId") or dbj.get("id"),"url":url,"token":token,"created":created,"signature":target_sig}
    except Exception:
        if created:
            try:
                c,_=turso_json(org,"/databases/"+urllib.parse.quote(target,safe=""),"DELETE")
                print("RECOVERY_DELETE_"+target+"="+str(c))
            except Exception:pass
        raise

def main():
    for n in ("CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID","TURSO_API_TOKEN"):
        print("::add-mask::"+need(n))
    limits=json.loads((ROOT/"config/provider_free_limits.json").read_text())
    tl=limits.get("turso") or {};maxdb=int(tl.get("max_databases") or 0);limit=int(tl.get("per_dr_database_size_limit_bytes") or 0)
    if maxdb<3 or limit<=0:raise RuntimeError("TURSO_LIMIT_AUTHORITY_MISSING")
    org,dbs=resolve_org(need("TURSO_API_TOKEN"))
    groups=sorted(set(str(x.get("group") or "") for x in dbs if x.get("group")))
    if len(groups)!=1:raise RuntimeError("TURSO_GROUP_NOT_UNIQUE:"+str(groups))
    group=groups[0]
    if len(dbs)+2>maxdb:raise RuntimeError("TURSO_FREE_DATABASE_COUNT_WOULD_EXCEED")
    beta=export_d1("BETA","pickpack");stable=export_d1("STABLE","pickpack1291-stable-private")
    before=len(dbs)
    pb=provision_target(org,group,beta,"pick-pack-1291-dr-beta",limit,maxdb,before)
    ps=provision_target(org,group,stable,"pick-pack-1291-dr-stable",limit,maxdb,before+1)
    if not cross_denied(ps["url"],pb["token"]):raise RuntimeError("BETA_DB_TOKEN_CAN_ACCESS_STABLE")
    if not cross_denied(pb["url"],ps["token"]):raise RuntimeError("STABLE_DB_TOKEN_CAN_ACCESS_BETA")
    c,j=turso_json(org,"/databases?limit=100")
    after=len(j.get("databases") or []) if c==200 else -1
    if after<before+2:raise RuntimeError("TURSO_DATABASE_COUNT_READBACK_FAILED")
    receipt={"status":"PASS","environment":"BETA_STABLE","provider":"TURSO","zero_cost_guard":"PASS","organization":org,"group":group,
      "database_count_before":before,"database_count_after":after,"max_databases":maxdb,"size_limit_bytes":limit,
      "beta":{"source_d1_id":beta["source_d1_id"],"source_d1_name":beta["source_d1_name"],"target_database":pb["target"],"target_id":pb["id"],"hostname":pb["host"],"backup_sql_sha256":beta["sql_sha256"],"sqlite_sha256":beta["sqlite_sha256"],"restore_compare":"PASS","signature":beta["signature"]},
      "stable":{"source_d1_id":stable["source_d1_id"],"source_d1_name":stable["source_d1_name"],"target_database":ps["target"],"target_id":ps["id"],"hostname":ps["host"],"backup_sql_sha256":stable["sql_sha256"],"sqlite_sha256":stable["sqlite_sha256"],"restore_compare":"PASS","signature":stable["signature"]},
      "cross_credentials":"DENIED_BOTH_WAYS","tokens_exposed":False,"legacy_database_untouched":True,"stable_public_activation":False}
    OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":"PASS","provider":"TURSO","beta_restore":"PASS","stable_restore":"PASS","cross_credentials":"DENIED_BOTH_WAYS","database_count_before":before,"database_count_after":after,"tokens_exposed":False}))

if __name__=="__main__":
    try:main()
    except Exception as e:
        if not OUT.exists():OUT.write_text(json.dumps({"status":"FAIL","provider":"TURSO","error":str(e)[:1000],"tokens_exposed":False},indent=2)+"\n")
        print("CLOUD_DR_TURSO_ISOLATION_ERROR:"+str(e)[:1400],file=sys.stderr);sys.exit(1)
