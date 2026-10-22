"""Account-private support endpoints and a staff inbox shared by operators."""
import secrets
from html import escape
from fastapi import Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from account_membership import page
from staff_access import can_edit_tables
import support_chat_storage as storage


def token(request):
    return request.session.setdefault('support_csrf',secrets.token_urlsafe(32))


def valid_token(request,value):
    current=request.session.get('support_csrf','')
    return bool(current and secrets.compare_digest(current.encode(),value.encode()))


def private_json(data,status=200):
    return JSONResponse(data,status_code=status,headers={'Cache-Control':'no-store'})


def install_support_routes(app,get_current_user):
    @app.get('/support/chat')
    def customer_chat(request:Request):
        user=get_current_user(request)
        if not user:
            return private_json(dict(signed_in=False,messages=[]))
        storage.initialize()
        return private_json(dict(signed_in=True,csrf=token(request),messages=storage.customer_messages(user['email'])))

    @app.post('/support/chat/message')
    def customer_send(request:Request,body:str=Form(''),csrf:str=Form(''),nonce:str=Form('')):
        user=get_current_user(request)
        if not user:
            return private_json({'error':'Please sign in to send a message.'},401)
        if not valid_token(request,csrf):
            return private_json({'error':'Refresh the chat and try again.'},403)
        storage.initialize()
        try:
            storage.send(user['email'],body,nonce)
        except ValueError as error:
            return private_json({'error':str(error)},400)
        return private_json({'sent':True})

    @app.get('/staff/chat/inbox')
    def staff_inbox_data(request:Request):
        if not can_edit_tables(request):
            return private_json({'error':'Staff access required.'},403)
        storage.initialize()
        return private_json({'threads':storage.inbox()})

    @app.get('/staff/chat', response_class=HTMLResponse)
    def staff_inbox(request:Request):
        if not can_edit_tables(request):
            return HTMLResponse('Staff access required.',status_code=403)
        storage.initialize()
        items=[]
        for item in storage.inbox():
            items.append(f'<a class="tr-chat-thread" href="/staff/chat/{int(item["id"])}"><strong>{escape(item["email"])}</strong><span>{"Needs reply" if item["status"]=="waiting" else "Replied"}</span><p>{escape(item["preview"])}</p></a>')
        body='<p class="tr-page-intro">Customer conversations. Administrators and managers can reply. Latest 200 conversations, with unanswered messages first.</p><p><a class="tr-button" href="/admin">← Table administration</a></p><div id="support-inbox">'+(''.join(items) or '<p>No conversations yet.</p>')+'</div>'
        body+='''<script>setInterval(async()=>{try{const r=await fetch('/staff/chat/inbox',{cache:'no-store'});if(!r.ok)return;const data=await r.json(),box=document.getElementById('support-inbox');box.replaceChildren();if(!data.threads.length){box.textContent='No conversations yet.';return}data.threads.forEach(t=>{const link=document.createElement('a');link.className='tr-chat-thread';link.href='/staff/chat/'+Number(t.id);const title=document.createElement('strong');title.textContent=t.email;const status=document.createElement('span');status.textContent=t.status==='waiting'?'Needs reply':'Replied';const preview=document.createElement('p');preview.textContent=t.preview;link.append(title,status,preview);box.append(link)})}catch(e){}},10000);</script>'''
        return page('Live chat inbox',body,get_current_user(request) or {})

    @app.get('/staff/chat/{thread_id}/messages')
    def staff_thread_data(request:Request,thread_id:int):
        if not can_edit_tables(request):
            return private_json({'error':'Staff access required.'},403)
        storage.initialize()
        item=storage.staff_messages(thread_id)
        return private_json(item or {'error':'Conversation not found.'},200 if item else 404)

    @app.get('/staff/chat/{thread_id}', response_class=HTMLResponse)
    def staff_thread(request:Request,thread_id:int):
        if not can_edit_tables(request):
            return HTMLResponse('Staff access required.',status_code=403)
        storage.initialize()
        item=storage.staff_messages(thread_id)
        if not item:
            return HTMLResponse('Conversation not found.',status_code=404)
        csrf=escape(token(request),quote=True)
        messages=''.join(f'<div class="tr-support-message {m["sender"]}"><small>{"Customer" if m["sender"]=="customer" else "TableRadar team"}</small><p>{escape(m["body"])}</p></div>' for m in item['messages'])
        body=f'''<p><a class="tr-button" href="/staff/chat">← Live chat inbox</a> <a class="tr-button" href="/admin">Table administration</a></p><p class="tr-page-intro">{escape(item['email'])} · latest 100 messages</p><section class="tr-support-conversation" id="support-thread">{messages}</section><form id="support-reply" class="tr-support-reply"><input type="hidden" name="csrf" value="{csrf}"><label>Reply to customer<textarea name="body" maxlength="2000" required></textarea></label><button class="tr-button" type="submit">Send reply</button><p id="support-reply-status" role="status"></p></form>'''
        body+='''<script>(function(){const box=document.getElementById('support-thread'),form=document.getElementById('support-reply'),notice=document.getElementById('support-reply-status');let nonce='',busy=false,last='';async function load(){try{const r=await fetch(location.pathname+'/messages',{cache:'no-store'});if(!r.ok)return;const data=await r.json(),sig=JSON.stringify(data.messages);if(sig===last)return;last=sig;box.replaceChildren();data.messages.forEach(m=>{const b=document.createElement('div');b.className='tr-support-message '+(m.sender==='customer'?'customer':'staff');const label=document.createElement('small');label.textContent=m.sender==='customer'?'Customer':'TableRadar team';const text=document.createElement('p');text.textContent=m.body;b.append(label,text);box.append(b)});box.scrollTop=box.scrollHeight}catch(e){}}form.addEventListener('submit',async e=>{e.preventDefault();if(busy)return;const field=form.querySelector('textarea');if(!field.value.trim())return;busy=true;form.querySelector('button').disabled=true;nonce=nonce||crypto.randomUUID();try{const data=new URLSearchParams({body:field.value,csrf:form.elements.csrf.value,nonce});const r=await fetch(location.pathname+'/reply',{method:'POST',body:data,credentials:'same-origin'});const result=await r.json();if(!r.ok)throw Error(result.error||'Reply could not be sent.');field.value='';nonce='';notice.textContent='Reply sent.';await load()}catch(e){notice.textContent=e.message}finally{busy=false;form.querySelector('button').disabled=false}});setInterval(load,10000);load()})();</script>'''
        return page('Customer conversation',body,get_current_user(request) or {})

    @app.post('/staff/chat/{thread_id}/reply')
    def staff_reply(request:Request,thread_id:int,body:str=Form(''),csrf:str=Form(''),nonce:str=Form('')):
        if not can_edit_tables(request) or not valid_token(request,csrf):
            return private_json({'error':'Staff access required. Refresh the page and try again.'},403)
        storage.initialize()
        user=get_current_user(request) or {}
        try:
            storage.send('',body,nonce,sender='staff',actor=user.get('email') or 'owner-staff-login',thread_id=thread_id)
        except ValueError as error:
            return private_json({'error':str(error)},400)
        return private_json({'sent':True})
