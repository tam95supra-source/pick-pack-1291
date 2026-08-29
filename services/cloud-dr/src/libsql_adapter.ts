import { createClient, type Client, type InStatement, type ResultSet } from "@libsql/client/web";

const normalize=(v:unknown):string|number|bigint|Uint8Array|null=>{
  if(v===undefined||v===null)return null;
  if(typeof v==="string"||typeof v==="number"||typeof v==="bigint"||v instanceof Uint8Array)return v;
  if(typeof v==="boolean")return v?1:0;
  return String(v);
};
const rowObject=(row:Record<string,unknown>)=>Object.fromEntries(Object.entries(row).map(([k,v])=>[k,v]));
class Stmt implements D1PreparedStatement{
  constructor(readonly client:Client,readonly sql:string,readonly args:unknown[]=[]){}
  bind(...values:unknown[]):D1PreparedStatement{return new Stmt(this.client,this.sql,values)}
  input():InStatement{return {sql:this.sql,args:this.args.map(normalize)}}
  async first<T>():Promise<T|null>{const r=await this.client.execute(this.input());return (r.rows[0]?rowObject(r.rows[0] as unknown as Record<string,unknown>):null) as T|null}
  async all<T>():Promise<D1Result<T>>{const r=await this.client.execute(this.input());return result<T>(r)}
  async run<T>():Promise<D1Result<T>>{const r=await this.client.execute(this.input());return result<T>(r)}
}
const result=<T>(r:ResultSet):D1Result<T>=>({success:true,results:r.rows.map(x=>rowObject(x as unknown as Record<string,unknown>) as T),meta:{changes:Number(r.rowsAffected||0)}})
export class LibsqlD1Adapter implements D1Database{
  readonly client:Client;
  constructor(url:string,authToken:string){this.client=createClient({url,authToken})}
  prepare(query:string):D1PreparedStatement{return new Stmt(this.client,query)}
  async batch<T>(statements:D1PreparedStatement[]):Promise<D1Result<T>[]>{
    const inputs=statements.map(s=>{if(!(s instanceof Stmt))throw new Error("DR_STATEMENT_ADAPTER_MISMATCH");return s.input()});
    const out=await this.client.batch(inputs,"write");return out.map(x=>result<T>(x));
  }
  close(){this.client.close()}
}
