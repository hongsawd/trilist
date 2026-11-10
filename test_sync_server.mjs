// In-memory integration fixture. No external service or real credentials.
import {createServer} from 'node:http';
import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
const worker=(await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(new URL('./sync-worker/src/index.js',import.meta.url))).toString('base64'))).default;
const db=new DatabaseSync(':memory:');db.exec(fs.readFileSync(new URL('./sync-worker/schema.sql',import.meta.url),'utf8'));
const wrap=(q,a=[])=>({bind(...args){return wrap(q,args)},async first(){return db.prepare(q).get(...a)||null},async all(){return {results:db.prepare(q).all(...a)}},run(){return db.prepare(q).run(...a)}});
const env={SYNC_TOKEN:'integration-only',DB:{prepare:q=>wrap(q),async batch(rows){for(const r of rows)r.run()}}};
const server=createServer(async(req,res)=>{
 const chunks=[];for await(const c of req)chunks.push(c);
 const body=Buffer.concat(chunks);
 const result=await worker.fetch(new Request('http://127.0.0.1'+req.url,{method:req.method,headers:req.headers,body:['GET','HEAD'].includes(req.method)?undefined:body}),env);
 res.writeHead(result.status,Object.fromEntries(result.headers));res.end(await result.text());
});
server.listen(Number(process.argv[2]),'127.0.0.1');
