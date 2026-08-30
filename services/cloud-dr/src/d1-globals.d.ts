interface Body{json<T=any>():Promise<T>}
interface D1Meta{
  changes?:number;
  duration?:number;
  rows_read?:number;
  rows_written?:number;
  served_by_region?:string;
  served_by_primary?:boolean;
}
interface D1Result<T=any>{results?:T[];meta?:D1Meta;success?:boolean}
interface D1PreparedStatement{
  bind(...values:unknown[]):D1PreparedStatement;
  first<T=any>():Promise<T|null>;
  all<T=any>():Promise<D1Result<T>>;
  run<T=any>():Promise<D1Result<T>>;
}
interface D1Database{
  prepare(query:string):D1PreparedStatement;
  batch<T=any>(statements:D1PreparedStatement[]):Promise<D1Result<T>[]>;
}
interface Env{
  DB:D1Database;
  SERVICE_TOKEN_SECRET:string;
  SERVICE_GENERATION:string;
  ENVIRONMENT_ID:string;
  SERVICE_AUDIENCE:string;
  GAS_API_URL:string;
  OUTBOUND_GAS_API_URL:string;
  DR_GAS_API_URL:string;
  DR_TARGET_ID:string;
  M1_ADMIN_TOKEN:string;
  GAS_BRIDGE_SHARED_SECRET:string;
  GOOGLE_OAUTH_CLIENT_ID:string;
  GOOGLE_OAUTH_CLIENT_SECRET:string;
  GOOGLE_OAUTH_REFRESH_TOKEN:string;
  GOOGLE_SOURCE_SHEET_ID:string;
  GOOGLE_OUTBOUND_SHEET_ID:string;
  REALTIME_HUB:any;
}
declare const Deno:{env:{get(key:string):string|undefined};serve(handler:(request:Request)=>Response|Promise<Response>):unknown};
