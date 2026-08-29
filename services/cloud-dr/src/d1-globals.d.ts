interface D1Result<T=Record<string,unknown>>{results?:T[];meta?:{changes?:number};success?:boolean}
interface D1PreparedStatement{bind(...values:unknown[]):D1PreparedStatement;first<T=Record<string,unknown>>():Promise<T|null>;all<T=Record<string,unknown>>():Promise<D1Result<T>>;run<T=Record<string,unknown>>():Promise<D1Result<T>>}
interface D1Database{prepare(query:string):D1PreparedStatement;batch<T=Record<string,unknown>>(statements:D1PreparedStatement[]):Promise<D1Result<T>[]>}
interface Env{DB:D1Database;SERVICE_TOKEN_SECRET:string;SERVICE_GENERATION:string}

declare const Deno:{env:{get(key:string):string|undefined};serve(handler:(request:Request)=>Response|Promise<Response>):unknown};
