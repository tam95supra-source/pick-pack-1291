#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'service/src/entry_product.ts'
HOT=ROOT/'service/src/session_hotfix.ts'
PROJ=ROOT/'service/src/beta47_projection.ts'


def once(text,old,new,label):
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f'missing anchor: {label}')
    return text.replace(old,new,1)

# Route the new multi-position/multi-resource contract without changing Beta64 legacy routes.
e=ENTRY.read_text()
e=once(e,
'import { attendanceEnterDelete, attendanceExitDelete, attendanceTimeCorrect, sessionExitGuarded, sessionWorkUpdate } from "./session_hotfix";\n',
'import { attendanceEnterDelete, attendanceExitDelete, attendanceTimeCorrect, sessionExitGuarded, sessionWorkUpdate } from "./session_hotfix";\nimport { sessionEnterV64, sessionExitV64, sessionResourceMutateV64, sessionResourceSnapshotV64 } from "./session_resources_v64";\n',
'entry import')
anchor='''    if(u.pathname==="/v1/session/work"&&method==="POST"){\n      const response=await sessionWorkUpdate(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;\n    }\n'''
insert='''    if(u.pathname==="/v1/session/enter-v2"&&method==="POST"){\n      const response=await sessionEnterV64(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;\n    }\n    if(u.pathname==="/v1/session/resources/snapshot"&&method==="POST")return sessionResourceSnapshotV64(request,env);\n    if(u.pathname==="/v1/session/resources/mutate"&&method==="POST"){\n      const response=await sessionResourceMutateV64(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;\n    }\n    if(u.pathname==="/v1/session/exit-v2"&&method==="POST"){\n      const response=await sessionExitV64(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;\n    }\n'''+anchor
e=once(e,anchor,insert,'entry routes')
ENTRY.write_text(e)

# Entire-session delete is allowed after explicit app re-authentication even when the
# session has resources. Preserve a detailed immutable snapshot in the delete event;
# FK cascade may remove operational assignments afterwards, but the event remains.
h=HOT.read_text()
old='''  if(text(s.work_choice).toUpperCase()!=="KHONG"||text(s.pda_serial)||text(s.user_pick)||text(s.pack_table)||text(s.user_pack))return apiError("SESSION_HAS_WORK_RESOURCES","CONFLICT",409);\n  const open='''
new='''  const deletedResources=(await env.DB.prepare("SELECT assignment_id,resource_type,resource_id,position_key,state,acquired_at,released_at,release_reason,release_disposition FROM session_resource_assignments WHERE session_id=?1 ORDER BY acquired_at,assignment_id").bind(s.session_id).all()).results??[];\n  const deletedPositions=(await env.DB.prepare("SELECT position_assignment_id,position_key,position_label,state,started_at,ended_at,reason FROM session_positions WHERE session_id=?1 ORDER BY started_at,position_assignment_id").bind(s.session_id).all()).results??[];\n  const open='''
h=once(h,old,new,'delete resource guard')
h=once(h,
'state:s.state}},idem,newVersion,a)',
'state:s.state},resource_assignments:deletedResources,positions:deletedPositions},idem,newVersion,a)',
'delete audit snapshot')
HOT.write_text(h)

# Google operational projection: S64 assignments are the authoritative source for
# resource ownership. Never infer S64 VOID/AVAILABLE resources from before/after event text.
p=PROJ.read_text()
p=once(p,
'''type ConsumptionRow={business_date:string;resource_type:string;resource_id:string;mnv:string;first_event_id:string};\n''',
'''type ConsumptionRow={business_date:string;resource_type:string;resource_id:string;mnv:string;first_event_id:string};\ntype AssignmentProjectionRow={session_id:string;business_date:string;mnv:string;resource_type:string;resource_id:string;state:string};\n''',
'projection assignment type')
p=once(p,
'''  const [sessionsR,eventsR,consR]=await env.DB.batch([\n''',
'''  const [sessionsR,eventsR,consR,assignmentsR]=await env.DB.batch([\n''',
'projection batch tuple')
p=once(p,
'''    env.DB.prepare(`SELECT business_date,resource_type,resource_id,mnv,first_event_id FROM resource_daily_consumption WHERE business_date IN (SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 7) ORDER BY business_date,mnv,resource_type,resource_id`),\n  ]);\n  const sessions=(sessionsR?.results??[]) as unknown as SessionRow[],events=(eventsR?.results??[]) as unknown as EventRow[],cons=(consR?.results??[]) as unknown as ConsumptionRow[];\n''',
'''    env.DB.prepare(`SELECT business_date,resource_type,resource_id,mnv,first_event_id FROM resource_daily_consumption WHERE business_date IN (SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 7) ORDER BY business_date,mnv,resource_type,resource_id`),\n    env.DB.prepare(`SELECT session_id,business_date,mnv,resource_type,resource_id,state FROM session_resource_assignments WHERE business_date IN (SELECT business_date FROM business_dates ORDER BY sequence_no DESC LIMIT 7) AND state IN ('ACTIVE','USED') ORDER BY business_date,mnv,resource_type,acquired_at`),\n  ]);\n  const sessions=(sessionsR?.results??[]) as unknown as SessionRow[],events=(eventsR?.results??[]) as unknown as EventRow[],cons=(consR?.results??[]) as unknown as ConsumptionRow[],assignmentRows=(assignmentsR?.results??[]) as unknown as AssignmentProjectionRow[];\n''',
'projection assignment query')
p=once(p,
'''  for(const e of events){const g=bySession.get(e.entity_id);if(!g)continue;g.events.push(e);const p=payload(e),before=obj(p.before),after=obj(p.after);for(const x of [p,before,after]){addResource(g.pdas,x,"pda_serial");addResource(g.picks,x,"user_pick");addResource(g.tables,x,"pack_table");addResource(g.packs,x,"user_pack");}}\n  for(const g of bySession.values()){for(const c of g.cons){if(c.resource_type==="USER_PICK")g.picks.push(c.resource_id);if(c.resource_type==="USER_PACK")g.packs.push(c.resource_id);}g.pdas=uniq(g.pdas);g.picks=uniq(g.picks);g.tables=uniq(g.tables);g.packs=uniq(g.packs);}\n''',
'''  for(const e of events){const g=bySession.get(e.entity_id);if(!g)continue;g.events.push(e);if(e.origin!=="SESSION_V64"){const p=payload(e),before=obj(p.before),after=obj(p.after);for(const x of [p,before,after]){addResource(g.pdas,x,"pda_serial");addResource(g.picks,x,"user_pick");addResource(g.tables,x,"pack_table");addResource(g.packs,x,"user_pack");}}}\n  for(const a of assignmentRows){const g=bySession.get(a.session_id);if(!g)continue;if(a.resource_type==="PDA")g.pdas.push(a.resource_id);if(a.resource_type==="USER_PICK")g.picks.push(a.resource_id);if(a.resource_type==="PACK_TABLE")g.tables.push(a.resource_id);if(a.resource_type==="USER_PACK")g.packs.push(a.resource_id);}\n  for(const g of bySession.values()){for(const c of g.cons){if(c.resource_type==="USER_PICK")g.picks.push(c.resource_id);if(c.resource_type==="USER_PACK")g.packs.push(c.resource_id);}g.pdas=uniq(g.pdas);g.picks=uniq(g.picks);g.tables=uniq(g.tables);g.packs=uniq(g.packs);}\n''',
'projection authoritative assignments')
PROJ.write_text(p)

for path,markers in [
    (ENTRY,['/v1/session/enter-v2','/v1/session/resources/mutate','/v1/session/exit-v2']),
    (HOT,['deletedResources','deletedPositions']),
    (PROJ,['AssignmentProjectionRow','e.origin!=="SESSION_V64"','assignmentRows']),
]:
    t=path.read_text()
    for m in markers:
        assert m in t,(path,m)
print('S64_SESSION_RESOURCE_MODEL_MATERIALIZE_PASS')
