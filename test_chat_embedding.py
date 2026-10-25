from types import SimpleNamespace
from fastapi.responses import HTMLResponse, JSONResponse
from main import browser_security_headers

def apply(path,compact,response):
 request=SimpleNamespace(url=SimpleNamespace(path=path),query_params={'compact':compact})
 async def next_response(request):return response
 coroutine=browser_security_headers(request,next_response)
 try:coroutine.send(None)
 except StopIteration as result:return result.value
 raise AssertionError('Unexpected suspended middleware')

for value in ('1','true','True','on','yes'):
 response=apply('/staff/chat',value,HTMLResponse('authenticated inbox'))
 assert response.headers['x-frame-options']=='SAMEORIGIN'
 assert "frame-ancestors 'self'" in response.headers['content-security-policy']
 assert response.headers['cache-control']=='no-store'
for path,compact,response in (
 ('/staff/chat','1',HTMLResponse('Forbidden',status_code=403)),
 ('/staff/chat','0',HTMLResponse('Full inbox')),
 ('/staff/chat','',HTMLResponse('Full inbox')),
 ('/profile','1',HTMLResponse('Profile')),
 ('/staff/chat','1',JSONResponse({'data':[]})),
):
 response=apply(path,compact,response)
 assert response.headers['x-frame-options']=='DENY'
 assert "frame-ancestors 'none'" in response.headers['content-security-policy']
print('PASS: only successful compact HTML inbox permits same-origin embedding; denied/full/other pages remain blocked')
