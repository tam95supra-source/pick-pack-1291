import { requireGasSheetOperations, type GasSheetOperationCost } from "./quota_budget";

export type StableSheetBridgeKind="primary"|"outbound"|"dr";

function stableEnv(env:Env):boolean{return String(env.ENVIRONMENT_ID||"").toUpperCase()==="STABLE";}

function bridgeUrl(env:Env,kind:StableSheetBridgeKind):string{
  if(kind==="primary")return String(env.GAS_API_URL||"").trim();
  if(kind==="outbound")return String(env.OUTBOUND_GAS_API_URL||"").trim();
  return String(env.DR_GAS_API_URL||"").trim();
}
function itemCount(value:unknown,max:number):number{return Array.isArray(value)?Math.min(max,value.length):0;}
function gasOperationCost(kind:StableSheetBridgeKind,operation:string,payload:Record<string,unknown>):GasSheetOperationCost{
  const op=operation.toLowerCase();
  if(op==="get_values")return{read:1};
  if(op==="batch_get"||op==="batch_get_a1")return{read:itemCount(payload.ranges,30)};
  if(op==="put_values")return{write:Array.isArray(payload.values)&&payload.values.length?1:0};
  if(op==="append_values")return Array.isArray(payload.values)&&payload.values.length?{read:1,write:1}:{};
  if(op==="batch_put_a1"){
    const data=Array.isArray(payload.data)?payload.data.slice(0,50) as Array<Record<string,unknown>>:[];
    return{write:data.filter(x=>Array.isArray(x.values)&&x.values.length>0).length};
  }
  // Primary ensure_replica reads sheet/header/id index and can create/update the hidden
  // replica sheet. Reserve conservatively because one bridge HTTP call is not one
  // SpreadsheetApp operation.
  if(kind==="primary"&&op==="ensure_replica")return{read:2,write:2};
  return{};
}

export function isStableEnvironment(env:Env):boolean{return stableEnv(env);}

export async function stableSheetBridge<T=Record<string,unknown>>(env:Env,kind:StableSheetBridgeKind,operation:string,payload:Record<string,unknown>={}):Promise<T>{
  if(!stableEnv(env))throw new Error("STABLE_BRIDGE_ENV_REQUIRED");
  const url=bridgeUrl(env,kind);
  if(!url.startsWith("https://script.google.com/"))throw new Error(`STABLE_${kind.toUpperCase()}_GAS_URL_INVALID`);
  await requireGasSheetOperations(env.DB,gasOperationCost(kind,operation,payload));
  const body={
    action:kind==="primary"?"service_sheet_bridge":"stable_bound_bridge",
    operation,
    _environment_id:"STABLE",
    _service_audience:"PICK_PACK_1291_STABLE",
    _bridge_secret:String(env.GAS_BRIDGE_SHARED_SECRET||""),
    ...payload,
  };
  if(!body._bridge_secret)throw new Error("STABLE_GAS_BRIDGE_SECRET_MISSING");
  const r=await fetch(url,{method:"POST",headers:{"content-type":"application/json; charset=utf-8","accept":"application/json"},body:JSON.stringify(body)});
  const text=await r.text();let j:Record<string,unknown>={};
  try{j=text?JSON.parse(text) as Record<string,unknown>:{};}catch{throw new Error(`STABLE_${kind.toUpperCase()}_GAS_BAD_JSON`);}
  if(!r.ok||j.ok!==true)throw new Error(String(j.error||`STABLE_${kind.toUpperCase()}_GAS_HTTP_${r.status}`).slice(0,240));
  return j as T;
}
