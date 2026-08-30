export type StableSheetBridgeKind="primary"|"outbound"|"dr";

function stableEnv(env:Env):boolean{return String(env.ENVIRONMENT_ID||"").toUpperCase()==="STABLE";}

function bridgeUrl(env:Env,kind:StableSheetBridgeKind):string{
  if(kind==="primary")return String(env.GAS_API_URL||"").trim();
  if(kind==="outbound")return String(env.OUTBOUND_GAS_API_URL||"").trim();
  return String(env.DR_GAS_API_URL||"").trim();
}

export function isStableEnvironment(env:Env):boolean{return stableEnv(env);}

export async function stableSheetBridge<T=Record<string,unknown>>(env:Env,kind:StableSheetBridgeKind,operation:string,payload:Record<string,unknown>={}):Promise<T>{
  if(!stableEnv(env))throw new Error("STABLE_BRIDGE_ENV_REQUIRED");
  const url=bridgeUrl(env,kind);
  if(!url.startsWith("https://script.google.com/"))throw new Error(`STABLE_${kind.toUpperCase()}_GAS_URL_INVALID`);
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
