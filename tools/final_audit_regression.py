#!/usr/bin/env python3
import json, os, pathlib, re, subprocess, sys, urllib.request, urllib.error

ROOT=pathlib.Path(__file__).resolve().parents[1]
E=json.loads((ROOT/"ops/beta-stable-audit-evidence.json").read_text())

def fail(msg): raise RuntimeError(msg)
def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: fail("COMMAND_FAILED:"+cmd[0]+":"+p.stderr[-300:])
    return p.stdout

def gh(path):
    tok=os.environ.get("GITHUB_TOKEN","").strip()
    repo=os.environ.get("GITHUB_REPOSITORY","").strip()
    if not tok or not repo: fail("GITHUB_ACTIONS_READ_CONTEXT_MISSING")
    q=urllib.request.Request("https://api.github.com/repos/"+repo+path,headers={
      "Authorization":"Bearer "+tok,"Accept":"application/vnd.github+json","User-Agent":"pp1291-final-audit-regression/1"})
    try:
      with urllib.request.urlopen(q,timeout=40) as r:return json.loads(r.read().decode())
    except urllib.error.HTTPError as ex:
      fail("GITHUB_READ_FAILED:"+path+":"+str(ex.code))

def verify_run(run_id):
    j=gh("/actions/runs/"+str(run_id))
    if j.get("status")!="completed" or j.get("conclusion")!="success": fail("RUN_NOT_SUCCESS:"+str(run_id))
    return j

def verify_artifact(run_id,artifact_id,digest=None):
    j=gh("/actions/runs/"+str(run_id)+"/artifacts?per_page=100")
    rows=j.get("artifacts") or []
    m=[x for x in rows if int(x.get("id") or 0)==int(artifact_id)]
    if len(m)!=1 or m[0].get("expired") is True: fail("ARTIFACT_NOT_CURRENT:"+str(artifact_id))
    if digest and str(m[0].get("digest") or "")!=digest: fail("ARTIFACT_DIGEST_DRIFT:"+str(artifact_id))
    return m[0]

def main():
    b=E["accepted_beta"]; iso=E["isolation"]; dr=E["backup_dr"]; st=E["stable_safety"]; apk=E["stable_private_apk"]
    if E.get("project")!="APK PICK PACK 1291":fail("PROJECT_IDENTITY_DRIFT")
    if not re.fullmatch(r"[0-9a-f]{40}",b["source_sha"]):fail("BETA_SOURCE_INVALID")
    p=subprocess.run(["git","diff","--quiet",b["source_sha"],"HEAD","--","app","service","google-apps-script"],cwd=ROOT)
    if p.returncode!=0:fail("ACCEPTED_BETA_PRODUCT_SOURCE_DRIFT")

    lock=json.loads((ROOT/"ops/promotion-lock-dry-run.json").read_text())
    owner=json.loads((ROOT/"ops/beta104-owner-acceptance.json").read_text())
    contract=json.loads((ROOT/"config/environment_contracts.json").read_text())
    release=json.loads((ROOT/"ops/beta104-release-lock.json").read_text())
    limits=json.loads((ROOT/"config/provider_free_limits.json").read_text())
    if owner.get("status")!="OWNER_ACCEPTED" or any(str((owner.get("checklist") or {}).get(str(i)))!="OK" for i in range(1,7)):fail("BETA104_OWNER_ACCEPTANCE_INVALID")
    if release.get("source_sha")!=b["source_sha"] or release.get("apk_sha256")!=b["apk_sha256"] or int(release.get("apk_size") or 0)!=b["apk_size"] or release.get("signer_sha256")!=b["signer_sha256"]:fail("BETA_RELEASE_LOCK_IDENTITY_DRIFT")
    bl=lock["beta_acceptance_lock"];sl=lock["stable_promotion_lock"]
    if bl.get("status")!="OWNER_ACCEPTED" or bl.get("source_sha")!=b["source_sha"]:fail("BETA_ACCEPTANCE_LOCK_DRIFT")
    if sl.get("status")!="DRY_RUN_READY" or sl.get("owner_promotion_authorization") is not None:fail("STABLE_PROMOTION_AUTHORITY_DRIFT")
    if any(bool(sl["stable"].get(k)) for k in ("manifest_active","ota_active","public_domain_active")):fail("STABLE_PUBLIC_FLAG_DRIFT")
    if any(bool(v) for v in sl.get("isolation",{}).values()):fail("BETA_STATE_COPY_ENABLED")
    sc=contract["environments"]["STABLE"]
    if sc.get("stable_publish_allowed") is not False:fail("STABLE_PUBLISH_CONTRACT_OPEN")
    if st!={"lifecycle":"READY_NOT_LIVE","root_public":False,"manifest_active":False,"ota_active":False,"promotion_authorized":False,"beta_state_copy":False}:fail("STABLE_SAFETY_EVIDENCE_INVALID")
    if limits.get("schema_version")!=1 or limits.get("render",{}).get("required_service_plan")!="free" or limits.get("turso",{}).get("required_plan_price_usd")!=0 or limits.get("deno",{}).get("required_plan_price_usd")!=0:fail("FREE_PROVIDER_AUTHORITY_DRIFT")

    for rid in [b["candidate_run"],b["release_run"],apk["run"],iso["promotion_run"],iso["final_ci_run"],dr["turso"]["run"],dr["deno"]["run"],dr["render"]["run"]]:
        verify_run(rid)
    verify_artifact(b["candidate_run"],b["candidate_artifact"])
    verify_artifact(b["candidate_run"],b["visual_artifact"])
    verify_artifact(b["release_run"],b["final_artifact"])
    verify_artifact(apk["run"],apk["artifact"],apk["artifact_digest"])
    verify_artifact(iso["promotion_run"],iso["promotion_artifact"],iso["promotion_artifact_digest"])
    verify_artifact(dr["turso"]["run"],dr["turso"]["artifact"])
    verify_artifact(dr["deno"]["run"],dr["deno"]["artifact"])
    verify_artifact(dr["render"]["run"],dr["render"]["artifact"])

    if apk.get("side_by_side_install")!="PASS" or apk.get("public_release") is not False:fail("STABLE_PRIVATE_APK_EVIDENCE_INVALID")
    if any(iso.get(k) is not False for k in ("stable_public","stable_manifest","stable_ota")):fail("STABLE_PROMOTION_RECEIPT_PUBLIC_DRIFT")
    if iso.get("owner_promotion_authorization") is not None:fail("OWNER_PROMOTION_AUTHORIZATION_MUST_BE_NULL")

    run(["python3","tools/verify_promotion_lock.py"])
    run(["node","tools/beta_stable_isolation_contract.mjs"])
    run(["node","tools/resilience_static_gate.mjs"])

    cloud=(ROOT/"services/cloud-dr/test/contract.test.mjs").read_text()
    for marker in ["cross-environment requests fail closed","Beta primary-only, Stable strict","DR quota guard is fail-closed and bounded"]:
        if marker not in cloud:fail("CLOUD_DR_REGRESSION_ASSERTION_MISSING:"+marker)
    promo=(ROOT/".github/workflows/promotion-dry-run.yml").read_text()
    for marker in ["Fresh promotion runtime dry-run","Fresh reversible auth isolation","Fresh reversible data isolation","stable_publish:false"]:
        if marker not in promo:fail("PROMOTION_REGRESSION_ASSERTION_MISSING:"+marker)
    fast=(ROOT/".github/workflows/app-fast-check.yml").read_text()
    if "provider_capacity_inventory.sh" not in fast or "cloud_dr_provider_preflight.sh" not in fast:fail("FINAL_CI_QUOTA_GUARD_MISSING")

    out={"status":"PASS","phase":"FINAL_IMPACTED_REGRESSION","accepted_beta_source_sha":b["source_sha"],
         "promotion_run":iso["promotion_run"],"final_ci_run":iso["final_ci_run"],
         "stable_ready_not_live":True,"stable_public":False,"stable_manifest":False,"stable_ota":False,
         "product_source_unchanged":True,"no_test_weakening_detected":True,"provider_gates_inherited_not_rerun":True}
    pathlib.Path("/tmp/final-impacted-regression.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except Exception as e:
      pathlib.Path("/tmp/final-impacted-regression.json").write_text(json.dumps({"status":"FAIL","error":str(e)[:1000]},indent=2)+"\n")
      print("FINAL_AUDIT_REGRESSION_ERROR:"+str(e)[:1400],file=sys.stderr);sys.exit(1)
