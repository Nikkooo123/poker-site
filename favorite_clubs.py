"""Stable, account-scoped club bookmarks independent of short-lived table IDs."""
import hashlib
import json
import re
import unicodedata
from html import escape

NETWORKS = {'clubgg', 'pokerbros', 'pppoker', 'xpoker', 'unknown'}


def club_record(source):
    name = str(source.get('club_name') or source.get('club') or '').strip()[:120]
    if not name or name == '***':
        return None
    network = re.sub(r'[^a-z0-9]', '', str(source.get('network') or source.get('application') or source.get('platform') or '').lower())
    network = network if network in NETWORKS else 'unknown'
    linked = source.get('club_subscription_id') or source.get('subscription_id')
    try:
        linked = int(linked)
    except (TypeError, ValueError):
        linked = 0
    normalized = ' '.join(unicodedata.normalize('NFKC', name).casefold().split())
    key = 'club:' + str(linked) if linked > 0 else 'legacy:' + hashlib.sha256((network + '\0' + normalized).encode()).hexdigest()
    return dict(key=key, name=name, network=network)


def normalize_favorite_clubs(value):
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError('Choose up to 100 favorite clubs.')
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {'key', 'name', 'network'}:
            raise ValueError('Invalid favorite club.')
        key, name, network = item['key'], item['name'], item['network']
        if not isinstance(key, str) or not re.fullmatch(r'(?:club:[1-9][0-9]{0,18}|legacy:[a-f0-9]{64})', key):
            raise ValueError('Invalid club identifier.')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120 or not all(c.isprintable() for c in name):
            raise ValueError('Invalid club name.')
        if not isinstance(network, str) or network not in NETWORKS or key in seen:
            raise ValueError('Invalid or duplicate club.')
        seen.add(key)
        result.append(dict(key=key, name=name.strip(), network=network))
    return result


def club_catalogue(tables, clubs=()):
    records = {}
    for source in [*tables, *clubs]:
        record = club_record(source)
        if record:
            records[record['key']] = record
    return sorted(records.values(), key=lambda x: (x['name'].casefold(), x['network'], x['key']))


def catalogue_attribute(records):
    return escape(json.dumps(records, ensure_ascii=True), quote=True)


def render_club_controls(enabled, signed_in=True):
    if not enabled:
        return ''
    markup = '''<div class="tr-my-clubs-control"><label title="Show tables from your saved clubs"><input id="favorite-clubs-only" type="checkbox"> My clubs <span id="favorite-clubs-count">0</span></label><button id="manage-favorite-clubs" type="button" aria-label="Manage favorite clubs" aria-expanded="false" aria-controls="favorite-clubs-panel" title="Manage favorite clubs">＋</button></div>
    <div id="favorite-clubs-panel" role="dialog" aria-labelledby="favorite-clubs-title" hidden><div class="tr-club-picker-head"><strong id="favorite-clubs-title">My clubs</strong><button id="close-favorite-clubs" type="button" aria-label="Close favorite clubs">×</button></div><p>Save clubs you want to follow. They stay saved when tables close.</p><!--SYNC--><input id="favorite-club-search" type="search" maxlength="120" placeholder="Find a club…" aria-label="Find a club to save"><div id="favorite-club-list"></div><p id="favorite-club-message" role="status" aria-live="polite"></p></div>'''
    return markup.replace('<!--SYNC-->', '' if signed_in else '<p>Saved in this browser. <a href="/signin_login">Sign in</a> to sync your clubs across devices.</p>')


def render_club_styles():
    return '''<style>
    .tr-club-search-tools{display:flex;gap:10px;position:relative;align-items:center}.tr-club-search-tools>#club-search{flex:1;min-width:0!important;width:auto!important}
    .tr-my-clubs-control{display:flex;align-items:center;gap:2px;white-space:nowrap;background:#243b3c;border:1px solid #83958a66;border-radius:12px;padding:3px 5px;color:#f2eee5;min-height:39px;box-sizing:border-box}
    .tr-my-clubs-control label{display:flex;align-items:center;gap:6px;font-size:12px;padding:4px 6px;cursor:pointer}.tr-my-clubs-control input{accent-color:#e8bd70}.tr-my-clubs-control span{color:#e8bd70}.tr-my-clubs-control button{background:none;border:0;color:#e8bd70;font-size:20px;cursor:pointer;padding:2px 5px}
    #favorite-clubs-panel[hidden]{display:none!important}#favorite-clubs-panel{position:fixed;z-index:5000;width:350px;max-width:calc(100vw - 24px);box-sizing:border-box;padding:18px;border-radius:16px;background:#203638;color:#f3eee5;border:1px solid #8c9e8880;box-shadow:0 18px 60px #0008}
    .tr-club-picker-head{display:flex;align-items:center;justify-content:space-between;gap:12px}#favorite-clubs-panel button{cursor:pointer}#close-favorite-clubs{background:none;color:#f3eee5;border:0;font-size:23px}#favorite-clubs-panel p{font-size:12px;color:#c5d2ce;line-height:1.5;margin:10px 0}#favorite-clubs-panel input{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;border:1px solid #84958b;background:#f3eee5;color:#1d3032}
    #favorite-club-list{max-height:min(300px,40vh);overflow:auto;margin-top:10px}.tr-club-choice{width:100%;display:flex;gap:10px;align-items:center;text-align:left;padding:10px 6px;border:0;border-bottom:1px solid #ffffff1a;background:none;color:#f3eee5}.tr-club-choice:hover{background:#ffffff08}.tr-club-choice .tr-club-star{font-size:22px;color:#e8bd70}.tr-club-choice small{display:block;color:#b7c8c2;font-size:11px;margin-top:4px}.tr-club-choice strong{font-size:13px;overflow-wrap:anywhere}
    .tr-club-fav-toggle{float:right;background:none;border:0;color:#d5c390;font-size:16px;padding:0 0 0 4px;line-height:1;cursor:pointer}.tr-club-fav-toggle[aria-pressed=true]{color:#efb300}.tr-club-fav-toggle:focus-visible,.tr-my-clubs-control button:focus-visible,.tr-club-choice:focus-visible{outline:2px solid #e8bd70;outline-offset:3px}
    @media(max-width:520px){.tr-club-search-tools{flex-wrap:wrap}.tr-club-search-tools>#club-search{flex-basis:100%}.tr-my-clubs-control{margin-left:auto}}
    </style>'''


def render_club_script():
    return '''<script>
    (function(){
      const body=document.body,user=body.dataset.username||'guest';
      const local=new Map(),read=k=>{try{return localStorage.getItem(k)}catch(e){return local.get(k)||null}},write=(k,v)=>{local.set(k,String(v));try{localStorage.setItem(k,String(v))}catch(e){}};
      const savedKey='favorite_clubs_'+user,onlyKey='only_favorite_clubs_'+user,pendingKey='table_filters_pending_'+user;
      const parse=(s,fallback)=>{try{return JSON.parse(s)||fallback}catch(e){return fallback}};
      const catalogue=parse(body.dataset.clubCatalogue,[]),server=parse(body.dataset.filters,null),known=new Map(catalogue.map(c=>[c.key,c]));
      let saved=parse(read(savedKey),[]),only=read(onlyKey)==='1';
      if(server&&read(pendingKey)!=='1'){saved=server.favoriteClubs||[];only=server.onlyFavoriteClubs===true}
      if(!Array.isArray(saved))saved=[];
      saved=saved.filter(c=>c&&typeof c.key==='string'&&typeof c.name==='string'&&typeof c.network==='string').slice(0,100).map(c=>known.get(c.key)||c);
      const panel=document.getElementById('favorite-clubs-panel'),toggle=document.getElementById('manage-favorite-clubs'),box=document.getElementById('favorite-clubs-only'),list=document.getElementById('favorite-club-list'),search=document.getElementById('favorite-club-search');
      const labels={clubgg:'Club GG',pokerbros:'Poker Bros',pppoker:'PP Poker',xpoker:'X Poker',unknown:'Other network'};
      function persist(){write(savedKey,JSON.stringify(saved));write(onlyKey,only?'1':'0')}
      function notify(){persist();paint();document.dispatchEvent(new CustomEvent('tr-favorite-clubs-change'))}
      function counts(){const map=new Map();document.querySelectorAll('.table-row').forEach(r=>map.set(r.dataset.clubKey,(map.get(r.dataset.clubKey)||0)+1));return map}
      function paint(){
        if(box)box.checked=only;const count=document.getElementById('favorite-clubs-count');if(count)count.textContent=String(saved.length);
        document.querySelectorAll('.tr-club-fav-toggle').forEach(b=>{const active=saved.some(c=>c.key===b.dataset.clubKey);b.textContent=active?'★':'☆';b.setAttribute('aria-pressed',String(active));b.setAttribute('aria-label',(active?'Remove ':'Save ')+b.dataset.clubName+(active?' from My clubs':' to My clubs'))});
        if(!list)return;const all=new Map(known);saved.forEach(c=>{if(!all.has(c.key))all.set(c.key,c)});const focusedKey=document.activeElement?.classList.contains('tr-club-choice')?document.activeElement.dataset.clubKey:null;const query=(search?.value||'').trim().toLocaleLowerCase(),activeCounts=counts();list.replaceChildren();
        const entries=[...all.values()].sort((a,b)=>Number(saved.some(c=>c.key===b.key))-Number(saved.some(c=>c.key===a.key))||a.name.localeCompare(b.name));
        entries.filter(c=>(c.name+' '+(labels[c.network]||c.network)).toLocaleLowerCase().includes(query)).forEach(c=>{
          const active=saved.some(x=>x.key===c.key),button=document.createElement('button');button.type='button';button.className='tr-club-choice';button.dataset.clubKey=c.key;button.setAttribute('aria-pressed',String(active));button.setAttribute('aria-label',(active?'Remove ':'Save ')+c.name+' · '+(labels[c.network]||c.network));
          const star=document.createElement('span');star.className='tr-club-star';star.textContent=active?'★':'☆';star.setAttribute('aria-hidden','true');const copy=document.createElement('span'),title=document.createElement('strong'),meta=document.createElement('small');title.textContent=c.name;const n=activeCounts.get(c.key)||0;meta.textContent=(labels[c.network]||c.network)+' · '+(n?n+' active table'+(n===1?'':'s'):'No active tables');copy.append(title,meta);button.append(star,copy);list.append(button);
        });
        const message=document.getElementById('favorite-club-message');if(message)message.textContent=!list.children.length?(query?'No clubs match that search.':'No clubs are available yet. Saved clubs will remain here.'):saved.length+' of 100 clubs saved';if(focusedKey)[...list.children].find(b=>b.dataset.clubKey===focusedKey)?.focus({preventScroll:true});
      }
      function change(key){const index=saved.findIndex(c=>c.key===key);if(index>=0)saved.splice(index,1);else{if(saved.length>=100){document.getElementById('favorite-club-message').textContent='You can save up to 100 clubs.';return}const c=known.get(key);if(!c)return;saved.push(c)}notify()}
      function place(){if(!panel||panel.hidden||!toggle)return;const r=toggle.getBoundingClientRect();panel.style.left=Math.max(12,Math.min(r.right-panel.offsetWidth,innerWidth-panel.offsetWidth-12))+'px';panel.style.top=Math.max(12,Math.min(r.bottom+8,innerHeight-panel.offsetHeight-12))+'px'}
      function close(focus){if(!panel)return;panel.hidden=true;toggle?.setAttribute('aria-expanded','false');if(focus)toggle?.focus()}
      function open(){if(!panel)return;panel.hidden=false;toggle?.setAttribute('aria-expanded','true');paint();place();search?.focus()}
      if(panel)document.body.append(panel);
      toggle?.addEventListener('click',()=>panel.hidden?open():close(true));document.getElementById('close-favorite-clubs')?.addEventListener('click',()=>close(true));search?.addEventListener('input',paint);
      box?.addEventListener('change',()=>{only=box.checked;notify();if(only&&!saved.length)open()});
      document.addEventListener('click',event=>{const choice=event.target.closest('.tr-club-choice,.tr-club-fav-toggle');if(choice){change(choice.dataset.clubKey);return}if(panel&&!panel.hidden&&!panel.contains(event.target)&&!toggle?.contains(event.target)&&event.target!==box&&!box?.parentElement.contains(event.target))close(false)});
      document.addEventListener('keydown',e=>{if(e.key==='Escape'&&panel&&!panel.hidden){e.preventDefault();close(true)}});window.addEventListener('resize',place);window.addEventListener('scroll',e=>{if(!panel?.contains(e.target))close(false)},true);
      window.trClubFavorites={saved:()=>saved.map(c=>({...c})),only:()=>only,matches:row=>saved.some(c=>c.key===row.dataset.clubKey),clearFilter:()=>{only=false;persist();paint()},open};persist();paint();
    })();
    </script>'''
