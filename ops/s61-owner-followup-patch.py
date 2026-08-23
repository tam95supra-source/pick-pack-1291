from pathlib import Path

p=Path('service/src/session_hotfix.ts')
s=p.read_text()
old='''  const hasPick=Boolean(pda||pick),hasPack=Boolean(table&&pack);let choice=text(b.work_choice,20).toUpperCase();if(!["PICK","PACK","KHONG"].includes(choice))choice=s.work_choice;if(hasPick&&hasPack){if(choice!=="PICK"&&choice!=="PACK")choice=s.work_choice==="PACK"?"PACK":"PICK";}else if(hasPick)choice="PICK";else if(hasPack)choice="PACK";else choice="KHONG";'''
new='''  const hasPick=Boolean(pda||pick),hasPack=Boolean(table&&pack),preserveWorkChoice=Boolean(b.preserve_work_choice),requestedChoice=text(b.work_choice,20).toUpperCase();let choice=requestedChoice;if(!["PICK","PACK","KHONG"].includes(choice))choice=s.work_choice;if(!preserveWorkChoice){if(hasPick&&hasPack){if(choice!=="PICK"&&choice!=="PACK")choice=s.work_choice==="PACK"?"PACK":"PICK";}else if(hasPick)choice="PICK";else if(hasPack)choice="PACK";else choice="KHONG";}'''
if old not in s: raise SystemExit('choice anchor missing')
s=s.replace(old,new,1)
p.write_text(s)

p=Path('service/src/resource_admin.ts')
s=p.read_text()
old='''    env.DB.prepare("SELECT resource_type,resource_id,status_label,available,metadata_json FROM resources ORDER BY resource_type,resource_id"),'''
new='''    env.DB.prepare("SELECT r.resource_type,r.resource_id,r.status_label,r.available,r.metadata_json,l.session_id AS leased_session_id,l.mnv AS leased_by_mnv FROM resources r LEFT JOIN resource_leases l ON l.resource_type=r.resource_type AND l.resource_id=r.resource_id ORDER BY r.resource_type,r.resource_id"),'''
if old not in s: raise SystemExit('resource list anchor missing')
s=s.replace(old,new,1)
p.write_text(s)
