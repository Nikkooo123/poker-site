"""An opt-in browser bridge, using the existing manager login and a chosen output folder."""
import json
import secrets
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from collector_sync import apply_snapshot


PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Collector sync · TableRadar</title>
<style>body{background:#142524;color:#e7f2ee;font:16px system-ui;max-width:850px;margin:45px auto;padding:20px}button{padding:12px 18px;margin:8px;border-radius:8px;border:1px solid #87ad9e;background:#294b48;color:white}pre{white-space:pre-wrap}a{color:#87ddc3}</style>
<h1>Local Collector sync</h1><p>Choose the Collector's <b>sync-outbox</b> folder once, then leave this page open.
Only verified table data is sent to TableRadar. Screenshots and login credentials stay on your computer.</p>
<p>Each complete club result replaces its active table list. Tables with no players or missing from the complete result are removed from the directory and archived.
Incomplete, ambiguous or old results leave existing tables unchanged.</p>
<button id="start">Choose sync-outbox and start</button><button id="stop" disabled>Stop sync</button>
<p id="status" role="status">Not connected. No background access has been granted.</p><pre id="log"></pre>
<details><summary>Apply one verified local result</summary>
<p>Paste a verified Collector JSON result. The same completeness, age and club checks apply.</p>
<textarea id="manual" aria-label="Verified Collector JSON" rows="6" style="width:100%"></textarea>
<button id="apply">Apply verified result</button></details>
<a href="/manager">Back to manager workspace</a>
<script>
const csrf=__CSRF__; let folder=null, timer=null, busy=false, generation=0; const applied=new Map(), failures=new Map();
const status=document.querySelector('#status'), log=document.querySelector('#log');
function report(message){status.textContent=message;log.textContent=(new Date().toLocaleTimeString()+' '+message+'\\n'+log.textContent).slice(0,12000)}
function stop(){generation++;clearInterval(timer);timer=null;folder=null;document.querySelector('#stop').disabled=true;document.querySelector('#start').disabled=false;report('Stopped. No new results will be sent. An in-flight request may finish.')}
document.querySelector('#stop').onclick=stop;
async function sendResult(body){
 const snapshot=JSON.parse(body);
 const response=await fetch('/manager/collector-sync',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Collector-CSRF':csrf},body});
 let result;try{result=await response.json()}catch{throw Error('Manager login expired or server is unavailable. Existing data unchanged.')}
 if(!response.ok)throw Error(result.detail||'Snapshot rejected.');
 report(result.applied?'Club '+snapshot.club_code+': '+result.active+' active tables; '+result.added+' added, '+result.removed+' removed.':'Result was already applied.');
 return result;
}
document.querySelector('#apply').onclick=async()=>{
 if(busy)return;busy=true;document.querySelector('#apply').disabled=true;
 try{await sendResult(document.querySelector('#manual').value)}catch(error){report(error.message)}
 finally{busy=false;document.querySelector('#apply').disabled=false}
};
document.querySelector('#start').onclick=async()=>{try{
 if(!window.showDirectoryPicker)throw Error('Use a current Chrome or Edge browser on this computer.');
 const chosen=await window.showDirectoryPicker({mode:'read'});
 if(chosen.name!=='sync-outbox')throw Error('Choose the sync-outbox folder, not your screenshots or home folder.');
 folder=chosen;generation++;document.querySelector('#stop').disabled=false;document.querySelector('#start').disabled=true;
 report('Connected. Waiting for complete verified results.'); timer=setInterval(poll,5000);await poll();
}catch(error){report(error.message)}};
async function poll(){if(busy||!folder)return;busy=true;const own=generation;try{
 for await(const [name,handle] of folder.entries()){
  if(own!==generation||!folder)break;
  if(handle.kind!=='file'||!/^club-[0-9]{1,32}\\.json$/.test(name))continue;
  const file=await handle.getFile();if(file.size>262144){report('Oversized result skipped: '+name);continue}
  const body=await file.text();if(applied.get(name)===body)continue;
  const failed=failures.get(name);if(failed&&failed.body===body&&Date.now()-failed.at<60000)continue;
  const snapshot=JSON.parse(body);if(name!=='club-'+snapshot.club_code+'.json')throw Error('Result identity differs from its filename.');
  if(own!==generation||!folder)break;
  try{await sendResult(body);applied.set(name,body);failures.delete(name)}
  catch(error){failures.set(name,{body,at:Date.now()});report(name+': '+error.message)}
 }
}catch(error){report(error.message)}finally{busy=false}}
window.addEventListener('pagehide',()=>{generation++;clearInterval(timer);folder=null});
</script></html>'''


def install_routes(app, is_manager):
    @app.get('/manager/collector', response_class=HTMLResponse)
    def collector_page(request: Request):
        if not is_manager(request):
            return HTMLResponse('Manager access required.',status_code=403)
        token=request.session.setdefault('account_csrf',secrets.token_urlsafe(32))
        return HTMLResponse(PAGE.replace('__CSRF__',json.dumps(token)),headers={'Cache-Control':'no-store'})

    @app.post('/manager/collector-sync')
    async def collector_snapshot(request: Request):
        if not is_manager(request):
            return JSONResponse({'detail':'Manager access required.'},status_code=403)
        expected=request.session.get('account_csrf','')
        supplied=request.headers.get('X-Collector-CSRF','')
        if not expected or not secrets.compare_digest(expected,supplied):
            return JSONResponse({'detail':'Refresh the sync page and reconnect.'},status_code=403)
        if request.headers.get('content-type','').split(';')[0]!='application/json':
            return JSONResponse({'detail':'JSON required.'},status_code=415)
        chunks=[];length=0
        async for chunk in request.stream():
            length+=len(chunk)
            if length>262144:
                return JSONResponse({'detail':'Snapshot too large.'},status_code=413)
            chunks.append(chunk)
        try:
            document=json.loads(b''.join(chunks))
            from starlette.concurrency import run_in_threadpool
            result=await run_in_threadpool(apply_snapshot,document)
            return JSONResponse(result)
        except (ValueError,UnicodeDecodeError):
            return JSONResponse({'detail':'Snapshot invalid, incomplete, stale or ambiguous. Existing data unchanged.'},status_code=422)
