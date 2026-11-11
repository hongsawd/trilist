// Shared Worker / Pages handler. Owners are resolved only from server-issued tokens.
const CORS={"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST, OPTIONS","Access-Control-Allow-Headers":"authorization, content-type","Access-Control-Max-Age":"86400"};
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{...CORS,"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});
async function digest(text){
 const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text));
 return [...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,"0")).join("");
}
function safeEqual(a,b){
 if(typeof a!=="string"||typeof b!=="string"||a.length!==b.length)return false;
 let diff=0;for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0;
}
async function resolveOwner(token,env){
 if(!token||token.length>256)return null;
 const hash=await digest(token);
 const user=await env.DB.prepare("SELECT owner, enabled FROM sync_users WHERE token_sha256 = ?").bind(hash).first();
 if(user)return user.enabled===1?user.owner:null;
 // Preserve the existing personal space. Never distribute its token to new users.
 if(env.SYNC_TOKEN&&safeEqual(token,env.SYNC_TOKEN))return String(env.SYNC_OWNER||"default");
 const legacy=await env.DB.prepare("SELECT value FROM meta WHERE key = 'token_sha256'").first();
 return legacy&&safeEqual(hash,legacy.value)?String(env.SYNC_OWNER||"default"):null;
}
async function register(req,env){
 const raw=await req.text();
 if(raw.length>2048)return json({error:"request too large"},413);
 try{const body=JSON.parse(raw||"{}");if(!body||typeof body!=="object"||Array.isArray(body))return json({error:"invalid json"},400);}catch{return json({error:"invalid json"},400);}
 const time=Date.now();
 const fingerprint=await digest((req.headers.get("CF-Connecting-IP")||"unknown")+"|"+Math.floor(time/3600000));
 const limit=Math.max(1,Math.min(300,Number(env.SIGNUP_LIMIT_PER_HOUR)||30));
 const attempt=await env.DB.prepare(`INSERT INTO signup_limits(fingerprint,created_at,attempts) VALUES(?,?,1)
   ON CONFLICT(fingerprint) DO UPDATE SET attempts=signup_limits.attempts+1 RETURNING attempts`).bind(fingerprint,time).first();
 if(!attempt||attempt.attempts>limit)return json({error:"registration rate limit"},429);
 const token="sg_"+[...crypto.getRandomValues(new Uint8Array(32))].map(x=>x.toString(16).padStart(2,"0")).join("");
 const owner="user-"+crypto.randomUUID();
 await env.DB.batch([
  env.DB.prepare("INSERT INTO sync_users(token_sha256,owner,enabled,created_at) VALUES(?,?,1,?)").bind(await digest(token),owner,time),
  env.DB.prepare("DELETE FROM signup_limits WHERE created_at < ?").bind(time-86400000)
 ]);
 return json({ok:true,token,serverTime:time},201);
}
export default{async fetch(req,env){
 const path=new URL(req.url).pathname;
 if(path==="/health"||path==="/api/health")return json({ok:true,service:"sange-sync",protocol:3});
 const signup=path==="/register"||path==="/api/register";
 if(!signup&&path!=="/sync"&&path!=="/api/sync")return env.ASSETS?env.ASSETS.fetch(req):json({error:"not found"},404);
 if(req.method==="OPTIONS")return new Response(null,{headers:CORS});
 if(req.method!=="POST")return json({error:"method not allowed"},405);
 try{
  if(signup)return await register(req,env);
  const auth=req.headers.get("authorization")||"";
  const owner=await resolveOwner(auth.startsWith("Bearer ")?auth.slice(7).trim():"",env);
  if(!owner)return json({error:"unauthorized"},401);
  if(Number(req.headers.get("content-length"))>2*1024*1024)return json({error:"request too large"},413);
  const raw=await req.text();
  if(new TextEncoder().encode(raw).length>2*1024*1024)return json({error:"request too large"},413);
  let body;try{body=JSON.parse(raw);}catch{return json({error:"invalid json"},400);}
  if(!Array.isArray(body?.items))return json({error:"items must be an array"},400);
  if(body.items.length>5000)return json({error:"too many items"},413);
  const rows=[];
  for(const it of body.items){
   if(!it||!["todo","event","thought","course"].includes(it.kind)||typeof it.id!=="string"||!it.id||it.id.length>128
    ||!Number.isSafeInteger(it.updatedAt)||it.updatedAt<=0||typeof it.deleted!=="boolean"
    ||(!it.deleted&&(!it.payload||typeof it.payload!=="object"||Array.isArray(it.payload))))return json({error:"invalid item"},400);
   const payload=JSON.stringify(it.deleted?null:it.payload);
   if(new TextEncoder().encode(payload).length>64*1024)return json({error:"item too large"},413);
   rows.push({kind:it.kind,id:it.id,payload,updatedAt:it.updatedAt,deleted:it.deleted?1:0});
  }
  if(rows.length){
   const stmt=env.DB.prepare(`INSERT INTO items (owner, kind, id, payload, updated_at, deleted)
    VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(owner, kind, id) DO UPDATE SET
    payload=excluded.payload, updated_at=excluded.updated_at, deleted=excluded.deleted
    WHERE excluded.updated_at > items.updated_at
    OR (excluded.updated_at = items.updated_at AND excluded.deleted > items.deleted)`);
   await env.DB.batch(rows.map(x=>stmt.bind(owner,x.kind,x.id,x.payload,x.updatedAt,x.deleted)));
  }
  const{results}=await env.DB.prepare("SELECT kind, id, payload, updated_at, deleted FROM items WHERE owner = ?").bind(owner).all();
  return json({ok:true,serverTime:Date.now(),items:(results||[]).map(x=>({kind:x.kind,id:x.id,payload:JSON.parse(x.payload),updatedAt:x.updated_at,deleted:!!x.deleted}))});
 }catch{return json({error:"sync service unavailable"},503);}
}};
