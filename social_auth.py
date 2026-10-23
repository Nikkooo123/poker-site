"""Guarded Google OIDC and Discord OAuth code flows; tokens are never persisted."""
import logging
import os
import secrets
import time
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from social_auth_config import configured_providers, callback_url
import social_auth_storage as store


class SocialCallbackPrivacyMiddleware:
    """Preserve query parameters for the handler while redacting the access-log scope."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get('type') == 'http' and scope.get('path') in ('/auth/google/callback','/auth/discord/callback'):
            private_scope = dict(scope)
            scope['query_string'] = b''
            return await self.app(private_scope, receive, send)
        return await self.app(scope, receive, send)


def oauth_client(provider):
    from authlib.integrations.starlette_client import OAuth
    oauth = OAuth()
    settings = dict(client_id=os.environ[provider.upper()+'_CLIENT_ID'],client_secret=os.environ[provider.upper()+'_CLIENT_SECRET'],client_kwargs=dict(code_challenge_method='S256',timeout=15,follow_redirects=False))
    if provider=='google':
        settings.update(server_metadata_url='https://accounts.google.com/.well-known/openid-configuration')
        settings['client_kwargs']['scope']='openid email profile'
    else:
        settings.update(authorize_url='https://discord.com/oauth2/authorize',access_token_url='https://discord.com/api/oauth2/token',api_base_url='https://discord.com/api/v10/')
        settings['client_kwargs'].update(scope='identify email',token_endpoint_auth_method='client_secret_post')
    oauth.register(provider,**settings)
    client=oauth.create_client(provider)
    client.framework.expires_in=600
    return client


def failure(message, status=400):
    from auth.auth_views import auth_shell, message_block
    response = HTMLResponse(auth_shell('<h1>Sign-in help</h1>'+message_block(error=message)+'<a class="tr-button" href="/signin_login">Back to sign in</a>','Sign-in help'),status_code=status)
    response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    return response


def checked_profile(provider, profile):
    verified = profile.get('email_verified') if provider=='google' else profile.get('verified')
    if verified is not True:
        raise store.PublicAuthError('Verify your email with the provider before continuing.')
    return str(profile.get('sub' if provider=='google' else 'id') or ''),str(profile.get('email') or ''),str(profile.get('name') or profile.get('global_name') or profile.get('username') or '')


def install_social_routes(app, get_current_user):
    app.add_middleware(SocialCallbackPrivacyMiddleware)
    async def begin(request, provider, user=None):
        if provider not in configured_providers():
            return failure('This sign-in method is not configured yet. Use email and password.',503)
        if not user and get_current_user(request):
            return RedirectResponse('/profile',status_code=303)
        try:
            for key in list(request.session):
                if key.startswith('_state_'+provider+'_'):
                    request.session.pop(key,None)
            state=secrets.token_urlsafe(32)
            browser=request.session.setdefault('social_browser',secrets.token_urlsafe(32))
            response=await oauth_client(provider).authorize_redirect(request,callback_url(provider),state=state,prompt='select_account' if provider=='google' else 'consent')
            await run_in_threadpool(store.create_flow,state,browser,provider,user)
            response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
            return response
        except Exception as error:
            logging.getLogger(__name__).warning('Social sign-in initiation failed: %s',type(error).__name__)
            return failure('This sign-in method is temporarily unavailable. Use email and password.',503)

    @app.get('/auth/{provider}')
    async def social_begin(request: Request, provider: str):
        return await begin(request,provider)

    @app.post('/auth/{provider}/connect')
    async def social_connect(request: Request, provider: str, csrf: str=Form(''),current_password: str=Form('')):
        if provider not in configured_providers():
            return failure('This sign-in method is not configured yet.',503)
        user=get_current_user(request)
        token=request.session.get('account_csrf','')
        if not user or not token or not secrets.compare_digest(token,csrf):
            return failure('Sign in and reopen My Account before connecting a sign-in method.',403)
        if user.get('password_login_enabled',True):
            from auth.auth_storage import _verify_password
            if len(current_password)>256 or not await run_in_threadpool(_verify_password,current_password,user.get('password_hash','')):
                return failure('Enter your current TableRadar password to connect another sign-in method.',403)
        elif not 0<=time.time()-request.session.get('social_authenticated_at',0)<=300:
            return failure('Sign in with your connected provider again before connecting another method.',403)
        return await begin(request,provider,user)

    @app.get('/auth/{provider}/callback')
    async def social_callback(request: Request, provider: str):
        if provider not in configured_providers():
            return failure('This sign-in method is not configured yet.',503)
        try:
            issuer=request.query_params.get('iss')
            if (provider=='discord' and issuer!='https://discord.com') or (provider=='google' and issuer and issuer not in ('https://accounts.google.com','accounts.google.com')):
                raise store.PublicAuthError('The sign-in provider could not be verified. Start again.')
            flow=await run_in_threadpool(store.consume_flow,request.query_params.get('state',''),request.session.get('social_browser',''),provider)
            current=get_current_user(request)
            connect=flow if flow['purpose']=='connect' else None
            if connect:
                if not current or current['email']!=flow['email'] or current.get('credential_version','')!=flow.get('credential_version',''):
                    raise store.PublicAuthError('Your account session changed. Start again from My Account.')
            elif current:
                raise store.PublicAuthError('Your account session changed. Start sign-in again.')
            client=oauth_client(provider)
            token=await client.authorize_access_token(request,leeway=30)
            if provider=='google':
                if not token.get('id_token') or not token.get('userinfo'):
                    raise store.PublicAuthError('Google did not provide a verified identity. Start again.')
                profile=token['userinfo']
            else:
                response=await client.get('users/@me',token=token)
                response.raise_for_status()
                profile=response.json()
            subject,email,name=checked_profile(provider,profile)
            user=await run_in_threadpool(store.resolve_identity,provider,subject,email,name,connect)
            # Rotate the signed session and keep provider access/refresh tokens out of it.
            request.session.clear()
            request.session.update(user_email=user['email'],username=user['username'],credential_version=user.get('credential_version',''),social_authenticated_at=int(time.time()))
            from player_access import enabled, entitled
            destination = '/profile' if connect else '/verify-account' if enabled() and not entitled(user) else '/'
            response=RedirectResponse(destination,status_code=303)
            response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
            return response
        except store.PublicAuthError as error:
            return failure(str(error))
        except Exception as error:
            logging.getLogger(__name__).warning('Social sign-in callback failed: %s',type(error).__name__)
            return failure('Sign-in could not be verified. Start again or use email and password.')
