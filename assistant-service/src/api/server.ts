/** Dependency-light health endpoint; clinical assistant routes are TODO. */
import { createServer } from 'node:http';
const port=Number(process.env.PORT ?? 8200);
export const server=createServer((req,res)=>{ if(req.url==='/health'){res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify({status:'ok',service:'assistant-service',provider:process.env.GEMINI_API_KEY?'TODO_GEMINI':'mock'}));return;} res.writeHead(404);res.end(); });
if(process.env.NODE_ENV!=='test') server.listen(port,'0.0.0.0');
