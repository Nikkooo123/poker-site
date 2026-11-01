"""Private, validated directory preferences attached to the signed-in account."""
import json
import secrets
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from auth.auth_storage import update_user
from favorite_clubs import normalize_favorite_clubs

FIELDS = {'activeGames','activeNetworks','search','minBlind','maxBlind','onlyFav','sortPlayersDir','sortBlindsDir','sortPriority','favoriteClubs','onlyFavoriteClubs'}
BLINDS = {'','0.5','1','2','4','5','6','8','10','15','20','25','30','50','100','200'}


def normalize_filters(value):
    if not isinstance(value,dict) or set(value)-FIELDS:
        raise ValueError('Invalid filters.')
    result = {}
    for key,allowed in [('activeGames',{'NLH','PLO4','PLO5','PLO6'}),('activeNetworks',{'clubgg','pokerbros','pppoker','xpoker'}),('sortPriority',{'players','blinds'})]:
        data=value.get(key,[] if key!='sortPriority' else ['players','blinds'])
        if not isinstance(data,list) or len(data)>len(allowed) or any(not isinstance(x,str) or x not in allowed for x in data) or len(set(data))!=len(data):
            raise ValueError('Invalid filters.')
        if key=='sortPriority' and set(data)!=allowed:
            raise ValueError('Invalid sort priority.')
        result[key]=data
    search=value.get('search','')
    if not isinstance(search,str) or len(search)>120 or any(not x.isprintable() for x in search):
        raise ValueError('Invalid club search.')
    result['search']=search
    for key in ('minBlind','maxBlind'):
        data=value.get(key,'')
        if not isinstance(data,str) or data not in BLINDS:
            raise ValueError('Invalid blinds filter.')
        result[key]=data
    for key in ('sortPlayersDir','sortBlindsDir'):
        data=value.get(key,'')
        if data not in ('','asc','desc'):
            raise ValueError('Invalid sort direction.')
        result[key]=data
    result['onlyFav']=value.get('onlyFav',False)
    if not isinstance(result['onlyFav'],bool):
        raise ValueError('Invalid favorites filter.')
    result['favoriteClubs'] = normalize_favorite_clubs(value.get('favoriteClubs', []))
    result['onlyFavoriteClubs'] = value.get('onlyFavoriteClubs', False)
    if not isinstance(result['onlyFavoriteClubs'], bool):
        raise ValueError('Invalid favorite clubs filter.')
    return result


def saved_filters(user):
    if not user or 'table_filters' not in user:
        return None
    try:return normalize_filters(user['table_filters'])
    except ValueError:return None


def install_preference_routes(app,get_current_user):
    @app.post('/account/table-filters')
    async def save_table_filters(request: Request):
        user=get_current_user(request)
        csrf=request.session.get('account_csrf','')
        supplied=request.headers.get('x-csrf-token','')
        if not user or not csrf or not secrets.compare_digest(csrf.encode(),supplied.encode()):
            return JSONResponse({'error':'Sign in and refresh the page to save filters.'},status_code=403,headers={'Cache-Control':'no-store'})
        body=await request.body()
        if len(body)>65536:
            return JSONResponse({'error':'Invalid filters.'},status_code=400)
        try:
            supplied_filters=json.loads(body)
            values=normalize_filters(supplied_filters)
            # Older cached clients must not erase the new persistent club bookmarks.
            previous=saved_filters(user) or {}
            for field in ('favoriteClubs','onlyFavoriteClubs'):
                if field not in supplied_filters and field in previous:
                    values[field]=previous[field]
        except (ValueError,TypeError):
            return JSONResponse({'error':'Invalid filters.'},status_code=400)
        saved=await run_in_threadpool(update_user,user['email'],table_filters=values)
        if not saved:
            return JSONResponse({'error':'Account no longer exists.'},status_code=403)
        return JSONResponse({'saved':True},headers={'Cache-Control':'no-store'})
