"""Preview-bound manager cleanup. Never deletes club placements or user accounts."""
import hashlib
import hmac
import json
import secrets
from html import escape
from fastapi import Request, Form
from fastapi.responses import HTMLResponse
from storage import _connect, _normalize_network, load_tables, init_db
from club_subscriptions_storage import load_active_operator_clubs
from club_table_lifecycle import init_archive


def belongs_to(row,club):
    linked=row.get('club_subscription_id')
    if linked is not None:
        return int(linked)==int(club['id'])
    return (str(row.get('club','')).strip().casefold()==str(club.get('club_name','')).strip().casefold()
            and _normalize_network(row.get('network') or row.get('platform'))==_normalize_network(club.get('application')))


def signature(csrf,keep_id,ids):
    body=json.dumps([int(keep_id),sorted(map(int,ids))],separators=(',',':')).encode()
    return hmac.new(csrf.encode(),body,hashlib.sha256).hexdigest()


def page(body,status=200):
    return HTMLResponse('''<!doctype html><html lang="en"><meta charset="utf-8"><title>Table cleanup · TableRadar</title>
        <style>body{background:#142524;color:#e7f2ee;font:16px system-ui;max-width:850px;margin:40px auto;padding:20px}button,input,select{padding:10px;margin:8px;border-radius:7px}a{color:#8bdbc2}li{margin:5px}button{cursor:pointer}</style>'''+body+'</html>',
        status_code=status,headers={'Cache-Control':'no-store'})


def remove_previewed_tables(keep_id,ids):
    init_db()
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout = '3s'")
            cur.execute('SELECT * FROM club_subscriptions WHERE id=%s FOR UPDATE',(keep_id,))
            club=cur.fetchone()
            if not club:
                raise ValueError('The club to preserve no longer exists.')
            cur.execute('SELECT * FROM poker_tables WHERE id=ANY(%s) ORDER BY id FOR UPDATE',(ids,))
            rows=cur.fetchall()
            if sorted(row['id'] for row in rows)!=sorted(ids) or any(belongs_to(row,club) for row in rows):
                raise ValueError('The preview changed or includes a protected table. Nothing was removed. Preview again.')
            if not ids:
                return 0
            init_archive(cur)
            cur.execute('''WITH removed AS (
                DELETE FROM poker_tables WHERE id=ANY(%s) RETURNING *
                ) INSERT INTO tableradar_removed_club_tables(reason,document)
                SELECT %s,to_jsonb(removed) FROM removed''',
                (ids,'Manager cleanup: kept club placement '+str(keep_id)))
            count=max(0,cur.rowcount)
            if count!=len(ids):
                raise ValueError('Cleanup count changed. Transaction was rolled back.')
        conn.commit()
    return count


def install_routes(app,is_manager):
    @app.get('/manager/tables/cleanup',response_class=HTMLResponse)
    def cleanup_preview(request: Request, keep_subscription_id: int=0):
        if not is_manager(request):
            return page('Manager access required.',403)
        csrf=request.session.setdefault('account_csrf',secrets.token_urlsafe(32))
        clubs=load_active_operator_clubs()
        club=next((c for c in clubs if c['id']==keep_subscription_id),None)
        options=''.join('<option value="'+str(c['id'])+'"'+(' selected' if c['id']==keep_subscription_id else '')+'>'+escape(c['club_name'])+'</option>' for c in clubs)
        body='<h1>Remove tables outside one club</h1><form method="get"><label>Club to keep <select name="keep_subscription_id">'+options+'</select></label><button>Preview cleanup</button></form>'
        if club:
            rows=load_tables();keep=[r for r in rows if belongs_to(r,club)];remove=[r for r in rows if not belongs_to(r,club)]
            ids=sorted(r['id'] for r in remove)
            body+='<h2>Keep '+str(len(keep))+' tables in '+escape(club['club_name'])+'</h2><ul>'+''.join('<li>'+escape(r['table_name'])+' — '+escape(r['players'])+'</li>' for r in keep)+'</ul>'
            body+='<h2>Remove '+str(len(remove))+' other tables</h2><p>Only table listings are removed. Club subscriptions, requests and accounts stay unchanged. Removed rows are retained in the server audit archive.</p>'
            body+='<details><summary>Review all tables to remove</summary><ul>'+''.join('<li>'+escape(r['table_name'])+' — '+escape(r['club'])+'</li>' for r in remove)+'</ul></details>'
            if ids:
                body+='<form method="post"><input type="hidden" name="csrf" value="'+escape(csrf,quote=True)+'"><input type="hidden" name="keep_subscription_id" value="'+str(club['id'])+'"><input type="hidden" name="table_ids" value="'+','.join(map(str,ids))+'"><input type="hidden" name="preview_signature" value="'+signature(csrf,club['id'],ids)+'"><label>Type DELETE '+str(len(ids))+' TABLES <input name="confirmation" required autocomplete="off"></label><button>Remove '+str(len(ids))+' tables</button></form>'
        return page(body+'<p><a href="/manager">Back to manager workspace</a></p>')

    @app.post('/manager/tables/cleanup',response_class=HTMLResponse)
    def cleanup_apply(request: Request,keep_subscription_id: int=Form(...),table_ids: str=Form(''),
                      preview_signature: str=Form(''),confirmation: str=Form(''),csrf: str=Form('')):
        if not is_manager(request):
            return page('Manager access required.',403)
        expected=request.session.get('account_csrf','')
        if not expected or not secrets.compare_digest(expected,csrf):
            return page('Refresh the preview and try again.',403)
        try:
            if len(table_ids)>20000:
                raise ValueError('Too many tables for one preview.')
            ids=[int(value) for value in table_ids.split(',') if value]
            if not ids or len(ids)!=len(set(ids)) or any(i<1 for i in ids):
                raise ValueError('Invalid table preview.')
            if not secrets.compare_digest(signature(csrf,keep_subscription_id,ids),preview_signature):
                raise ValueError('The table preview changed.')
            if confirmation!='DELETE '+str(len(ids))+' TABLES':
                raise ValueError('Enter the exact confirmation phrase shown in the preview.')
            removed=remove_previewed_tables(keep_subscription_id,ids)
            return page('<h1>Cleanup completed</h1><p>Removed '+str(removed)+' table listings. Protected club tables were preserved.</p><p><a href="/manager">View remaining tables</a></p>')
        except ValueError as error:
            return page('<h1>Nothing removed</h1><p>'+escape(str(error))+'</p><a href="/manager/tables/cleanup">Preview again</a>',400)
