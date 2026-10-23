"""Account-private support cases and shared staff messenger."""
import secrets
from html import escape
from fastapi import Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from account_membership import page
from staff_access import can_edit_tables
from support_chat_inbox import render_staff_messenger
import support_chat_storage as storage


def token(request):
    return request.session.setdefault('support_csrf', secrets.token_urlsafe(32))


def valid_token(request,value):
    current=request.session.get('support_csrf','')
    return bool(current and secrets.compare_digest(current.encode(),value.encode()))


def private_json(data,status=200):
    return JSONResponse(data,status_code=status,headers={'Cache-Control':'no-store'})


def install_support_routes(app,get_current_user):
    @app.get('/support/chat')
    def customer_chat(request:Request,case_id:str='',before:int=0):
        user=get_current_user(request)
        if not user:
            return private_json(dict(signed_in=False,messages=[]))
        storage.initialize()
        if can_edit_tables(request):
            return private_json(dict(signed_in=True,staff=True,csrf=token(request),waiting_count=storage.waiting_count(),messages=[]))
        state=storage.customer_state(user['email'],case_id,before if before>0 else None)
        if state is None:
            return private_json({'error':'Conversation not found.'},404)
        conversation=state.get('conversation') or {}
        return private_json(dict(signed_in=True,staff=False,csrf=token(request),messages=conversation.get('messages',[]),**state))

    @app.post('/support/chat/message')
    def customer_send(request:Request,body:str=Form(''),csrf:str=Form(''),nonce:str=Form(''),case_id:str=Form('')):
        user=get_current_user(request)
        if not user:
            return private_json({'error':'Please sign in to send a message.'},401)
        if not valid_token(request,csrf):
            return private_json({'error':'Refresh the chat and try again.'},403)
        storage.initialize()
        try:
            identifier=storage.send(user['email'],body,nonce,thread_id=case_id or None)
        except ValueError as error:
            return private_json({'error':str(error)},400)
        return private_json({'sent':True,'case_id':identifier})

    @app.get('/staff/chat/count')
    def staff_count(request:Request):
        if not can_edit_tables(request):
            return private_json({'error':'Staff access required.'},403)
        storage.initialize()
        return private_json({'waiting_count':storage.waiting_count()})

    @app.get('/staff/chat/inbox')
    def staff_inbox_data(request:Request,state:str='open'):
        if not can_edit_tables(request):
            return private_json({'error':'Staff access required.'},403)
        storage.initialize()
        try:
            items=storage.inbox(state)
        except ValueError as error:
            return private_json({'error':str(error)},400)
        return private_json({'threads':items,'waiting_count':storage.waiting_count(),'csrf':token(request)})

    def messenger(request,selected='',compact=False):
        content=render_staff_messenger(token(request),selected)
        if compact:
            from brand import render_site_theme
            return HTMLResponse('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Live chat inbox</title>'+render_site_theme()+'</head><body style="margin:0"><style>body .tr-staff-messenger{height:100dvh;max-height:100dvh;border:0;border-radius:0;min-height:0}</style>'+content+'</body></html>',headers={'Cache-Control':'no-store'})
        body='<p class="tr-page-intro">Choose a customer on the left to read and reply. Red counters show unanswered messages. Finish a resolved request, then archive it to remove it from active work. History is kept.</p><p><a class="tr-button" href="/admin">Table administration</a></p>'+content
        return HTMLResponse(page('Live chat inbox',body,get_current_user(request) or {}),headers={'Cache-Control':'no-store'})

    @app.get('/staff/chat', response_class=HTMLResponse)
    def staff_inbox(request:Request,compact:bool=False):
        if not can_edit_tables(request):
            return HTMLResponse('Staff access required.',status_code=403)
        storage.initialize()
        return messenger(request,compact=compact)

    @app.get('/staff/chat/{thread_id}/messages')
    def staff_thread_data(request:Request,thread_id:str,before:int=0):
        if not can_edit_tables(request):
            return private_json({'error':'Staff access required.'},403)
        storage.initialize()
        item=storage.staff_messages(thread_id,before if before>0 else None)
        return private_json(item or {'error':'Conversation not found.'},200 if item else 404)

    @app.get('/staff/chat/{thread_id}', response_class=HTMLResponse)
    def staff_thread(request:Request,thread_id:str):
        if not can_edit_tables(request):
            return HTMLResponse('Staff access required.',status_code=403)
        storage.initialize()
        item=storage.staff_messages(thread_id)
        if not item:
            return HTMLResponse('Conversation not found.',status_code=404)
        return messenger(request,selected=item['id'])

    @app.post('/staff/chat/{thread_id}/reply')
    def staff_reply(request:Request,thread_id:str,body:str=Form(''),csrf:str=Form(''),nonce:str=Form('')):
        if not can_edit_tables(request) or not valid_token(request,csrf):
            return private_json({'error':'Staff access required. Refresh the page and try again.'},403)
        storage.initialize()
        user=get_current_user(request) or {}
        try:
            identifier=storage.send('',body,nonce,sender='staff',actor=user.get('email') or 'staff',thread_id=thread_id)
        except ValueError as error:
            return private_json({'error':str(error)},400)
        return private_json({'sent':True,'case_id':identifier})

    @app.post('/staff/chat/{thread_id}/finish')
    def staff_finish(request:Request,thread_id:str,csrf:str=Form(''),last_message_id:int=Form(-1)):
        if not can_edit_tables(request) or not valid_token(request,csrf):
            return private_json({'error':'Staff access required. Refresh the page and try again.'},403)
        storage.initialize()
        try:
            storage.finish(thread_id,last_message_id)
        except ValueError as error:
            return private_json({'error':str(error)},409)
        return private_json({'finished':True,'waiting_count':storage.waiting_count()})

    @app.post('/staff/chat/{thread_id}/archive')
    def staff_archive(request:Request,thread_id:str,csrf:str=Form('')):
        if not can_edit_tables(request) or not valid_token(request,csrf):
            return private_json({'error':'Staff access required. Refresh the page and try again.'},403)
        storage.initialize()
        try:
            storage.archive(thread_id)
        except ValueError as error:
            return private_json({'error':str(error)},409)
        return private_json({'archived':True,'waiting_count':storage.waiting_count()})
