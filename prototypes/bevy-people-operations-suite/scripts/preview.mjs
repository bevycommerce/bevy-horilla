import http from 'node:http';import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const routes=[['/hr/','apps/hr-portal/web'],['/expenses/','apps/expenses/dist'],['/insurance/','apps/insurance'],['/daily-updates/','apps/daily-updates']];
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.pdf':'application/pdf'};
export async function handle(req,res){
 const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'SAMEORIGIN','Referrer-Policy':'no-referrer'};
 try{
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,headers);res.end('Method not allowed');return;}
  const raw=req.url.split('?')[0];let urlPath;try{urlPath=decodeURIComponent(raw);}catch{res.writeHead(400,headers);res.end('Invalid path');return;}
  if(urlPath.includes('\\')||urlPath.split('/').some(x=>x==='..'||x.startsWith('.'))){res.writeHead(404,headers);res.end('Not found');return;}
  let file;if(urlPath==='/')file=path.join(root,'index.html');else{
   const r=routes.find(([prefix])=>urlPath.startsWith(prefix));if(!r){const redirect=routes.find(([prefix])=>urlPath===prefix.slice(0,-1));if(redirect){res.writeHead(302,{...headers,Location:redirect[0]});res.end();return;}res.writeHead(404,headers);res.end('Not found');return;}
   const rel=urlPath.slice(r[0].length)||'index.html';if(rel.includes('/')&&!(r[0]==='/hr/'&&rel.startsWith('expenses/')&&!rel.slice(9).includes('/'))){res.writeHead(404,headers);res.end('Not found');return;}
   const name=path.basename(rel);if(r[0]==='/insurance/'&&!['index.html','config.js','logic.js'].includes(rel)){res.writeHead(404,headers);res.end('Not found');return;}if(name.endsWith('.test.js')||name.endsWith('.test.mjs')||name.endsWith('.test.cjs')||name==='backend-check.mjs'||!types[path.extname(name)]){res.writeHead(404,headers);res.end('Not found');return;}
   file=path.join(root,r[1],rel);
  }
  const bytes=await fs.readFile(file);res.writeHead(200,{...headers,'Content-Type':types[path.extname(file)]});res.end(req.method==='HEAD'?undefined:bytes);
 }catch(e){res.writeHead(e.code==='ENOENT'?404:500,headers);res.end(e.code==='ENOENT'?'Not found':'Preview unavailable');}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const i=process.argv.indexOf('--port'),port=i<0?4173:Number(process.argv[i+1]);if(!Number.isInteger(port)||port<1||port>65535)throw Error('Use a valid --port value.');
 http.createServer(handle).listen(port,'127.0.0.1',()=>console.log('Local preview only: http://127.0.0.1:'+port));
}
