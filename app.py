"""Private, loopback-only default MVP. Capability possession grants access."""
from __future__ import annotations
import hashlib, hmac, io, os, secrets, sqlite3, threading, warnings
from datetime import date as Date, datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Literal
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

class Contribution(BaseModel):
    nickname: str = Field(min_length=1, max_length=40)
    caption: str = Field(default='', max_length=280)
    demo: Literal['stage','crowd','lights'] | None = 'stage'
    @field_validator('nickname')
    @classmethod
    def clean_name(cls,v):
        if not v.strip(): raise ValueError('昵称不能为空')
        return v.strip()
class Create(Contribution):
    title: str = Field(min_length=1,max_length=80)
    date: Date
    organizer: str = Field(min_length=1,max_length=40)
    request_id: str = Field(min_length=16,max_length=100)
    @field_validator('title','organizer')
    @classmethod
    def clean_text(cls,v):
        if not v.strip(): raise ValueError('内容不能为空')
        return v.strip()
class Join(Contribution):
    request_id: str = Field(min_length=16,max_length=100)


def create_app(data_dir=None):
    data = Path(data_dir or os.environ.get('ENCORE_DATA_DIR', ROOT/'data'))
    data.mkdir(parents=True,exist_ok=True)
    media = data/'media'; media.mkdir(exist_ok=True)
    dbpath = data/'encore.sqlite3'
    lock = threading.RLock()
    @contextmanager
    def db(write=False):
        con=sqlite3.connect(dbpath,timeout=15)
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            if write: con.execute('BEGIN IMMEDIATE')
            yield con
            con.commit()
        except Exception:
            con.rollback(); raise
        finally: con.close()
    with db(True) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS deleted_creates(request_hash TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,title TEXT,date TEXT,organizer TEXT,created_at TEXT,
          owner_hash TEXT,view_hash TEXT,invite_hash TEXT,create_request TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS contributions(id TEXT PRIMARY KEY,event_id TEXT REFERENCES events(id) ON DELETE CASCADE,
          slot INTEGER CHECK(slot BETWEEN 0 AND 2),nickname TEXT,caption TEXT,demo TEXT,image TEXT,edit_hash TEXT,
          UNIQUE(event_id,slot));
        CREATE TABLE IF NOT EXISTS joins(event_id TEXT REFERENCES events(id) ON DELETE CASCADE,request_id TEXT,
          invite_hash TEXT,contribution_id TEXT,PRIMARY KEY(event_id,request_id));
        ''')
        c.execute('INSERT OR IGNORE INTO settings VALUES (?,?)',('secret',secrets.token_hex(32)))
        secret=c.execute('SELECT value FROM settings WHERE key=?',('secret',)).fetchone()[0].encode()
    # Recover harmless crash leftovers: media is never served without a live DB row.
    with db() as c:
        referenced = {r[0] for r in c.execute('SELECT image FROM contributions WHERE image IS NOT NULL')}
    for candidate in media.glob('*.jpg'):
        if candidate.name not in referenced: candidate.unlink(missing_ok=True)
    def hashed(x): return hashlib.sha256(x.encode()).hexdigest()
    def cap(scope,rid): return hmac.new(secret,(scope+':'+rid).encode(),hashlib.sha256).hexdigest()
    def bearer(request:Request):
        v=request.headers.get('authorization','')
        if not v.startswith('Bearer ') or len(v)>256: raise HTTPException(401,'需要访问链接')
        return v[7:]
    def event(c,eid):
        e=c.execute('SELECT * FROM events WHERE id=?',(eid,)).fetchone()
        if not e: raise HTTPException(404,'纪念册不存在或已删除')
        return e
    def authorize(c,e,key,owner=False,cid=None):
        kh=hashed(key)
        if hmac.compare_digest(kh,e['owner_hash']):
            if not cid: return
            own=c.execute('SELECT edit_hash FROM contributions WHERE id=? AND event_id=?',(cid,e['id'])).fetchone()
            if own and own[0] == hashed(cap('contribution_key',e['create_request'])): return
            raise HTTPException(403,'只能修改或撤回自己的贡献')
        if owner: raise HTTPException(403,'需要主办者管理链接')
        if cid:
            row=c.execute('SELECT edit_hash FROM contributions WHERE id=? AND event_id=?',(cid,e['id'])).fetchone()
            if row and hmac.compare_digest(kh,row[0]): return
        elif kh in (e['view_hash'],e['invite_hash']): return
        elif c.execute('SELECT 1 FROM contributions WHERE event_id=? AND edit_hash=?',(e['id'],kh)).fetchone(): return
        raise HTTPException(403,'链接无效或权限不足')
    def model(c,e):
        rows=c.execute('SELECT id,slot,nickname,caption,demo,image FROM contributions WHERE event_id=? ORDER BY slot',(e['id'],)).fetchall()
        return {k:e[k] for k in ('id','title','date','organizer','created_at')} | {'count':len(rows),'contributions':[
            {k:r[k] for k in ('id','slot','nickname','caption','demo')} | {'image_url': f"/api/events/{e['id']}/contributions/{r['id']}/image?v={hashlib.sha256(r['image'].encode()).hexdigest()[:16]}" if r['image'] else None} for r in rows]}
    def unlink(name):
        if name: (media/name).unlink(missing_ok=True)
    app=FastAPI(title='安可三联 · Local MVP',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.data_dir=data
    @app.middleware('http')
    async def security(request,call_next):
        # Block cross-origin mutation and DNS rebinding against this localhost service.
        host=request.headers.get('host','').split(':')[0]
        if host not in ('127.0.0.1','localhost','testserver','[::1]'):
            return Response('Local access only',status_code=403)
        origin=request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return Response('Cross-origin access denied',status_code=403)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response
    @app.get('/api/health')
    def health(): return {'ok':True,'local_only':True}
    @app.post('/api/events',status_code=201)
    def create(payload:Create):
        rid=payload.request_id
        keys={k:cap(k,rid) for k in ('owner_key','view_key','invite_token','contribution_key')}
        with lock,db(True) as c:
            if c.execute('SELECT 1 FROM deleted_creates WHERE request_hash=?',(hashed(rid),)).fetchone():
                raise HTTPException(410,'这份纪念册已删除，请重新开始')
            old=c.execute('SELECT * FROM events WHERE create_request=?',(rid,)).fetchone()
            if old:
                own=c.execute('SELECT id FROM contributions WHERE event_id=? AND edit_hash=?',(old['id'],hashed(keys['contribution_key']))).fetchone()
                if hashed(keys['invite_token']) != old['invite_hash']: keys['invite_token'] = None
                return {'event':model(c,old),**keys,'contribution_id':own[0] if own else None}
            eid=secrets.token_urlsafe(16); cid=secrets.token_urlsafe(16)
            c.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)',(eid,payload.title,str(payload.date),payload.organizer,datetime.now(timezone.utc).isoformat(),hashed(keys['owner_key']),hashed(keys['view_key']),hashed(keys['invite_token']),rid))
            c.execute('INSERT INTO contributions VALUES (?,?,?,?,?,?,?,?)',(cid,eid,0,payload.nickname,payload.caption,payload.demo,None,hashed(keys['contribution_key'])))
            return {'event':model(c,event(c,eid)),**keys,'contribution_id':cid}
    @app.get('/api/events/{eid}')
    def read(eid:str,key=Depends(bearer)):
        with db() as c:
            e=event(c,eid); authorize(c,e,key); return model(c,e)
    @app.get('/api/invites/{token}')
    def invitation(token:str):
        with db() as c:
            e=c.execute('SELECT * FROM events WHERE invite_hash=?',(hashed(token),)).fetchone()
            if not e: raise HTTPException(404,'邀请已撤销或不存在')
            return model(c,e)
    @app.post('/api/invites/{token}/join',status_code=201)
    def join(token:str,payload:Join):
        with lock,db(True) as c:
            e=c.execute('SELECT * FROM events WHERE invite_hash=?',(hashed(token),)).fetchone()
            if not e: raise HTTPException(404,'邀请已撤销或不存在')
            rid=payload.request_id; ck=cap('join:'+e['id'],rid)
            previous=c.execute('SELECT * FROM joins WHERE event_id=? AND request_id=?',(e['id'],rid)).fetchone()
            if previous:
                row=c.execute('SELECT id FROM contributions WHERE id=?',(previous['contribution_id'],)).fetchone()
                if not row: raise HTTPException(410,'这份贡献已撤回，请重新开始')
                cid=row[0]
            else:
                used={r[0] for r in c.execute('SELECT slot FROM contributions WHERE event_id=?',(e['id'],))}
                slots=[s for s in range(3) if s not in used]
                if not slots: raise HTTPException(409,'三联已满，感谢你的心意')
                cid=secrets.token_urlsafe(16)
                c.execute('INSERT INTO contributions VALUES (?,?,?,?,?,?,?,?)',(cid,e['id'],slots[0],payload.nickname,payload.caption,payload.demo,None,hashed(ck)))
                c.execute('INSERT INTO joins VALUES (?,?,?,?)',(e['id'],rid,hashed(token),cid))
            return {'event':model(c,e),'view_key':cap('view_key',e['create_request']),'contribution_key':ck,'contribution_id':cid}
    @app.post('/api/events/{eid}/invite')
    def rotate(eid:str,key=Depends(bearer)):
        token=secrets.token_urlsafe(32)
        with lock,db(True) as c:
            e=event(c,eid); authorize(c,e,key,owner=True)
            c.execute('UPDATE events SET invite_hash=? WHERE id=?',(hashed(token),eid))
        return {'invite_token':token}
    @app.delete('/api/events/{eid}/invite',status_code=204)
    def revoke(eid:str,key=Depends(bearer)):
        with lock,db(True) as c:
            e=event(c,eid); authorize(c,e,key,owner=True)
            c.execute('UPDATE events SET invite_hash=NULL WHERE id=?',(eid,))
        return Response(status_code=204)
    @app.put('/api/events/{eid}/contributions/{cid}')
    def edit(eid:str,cid:str,payload:Contribution,key=Depends(bearer)):
        with lock,db(True) as c:
            e=event(c,eid); authorize(c,e,key,cid=cid)
            row=c.execute('SELECT * FROM contributions WHERE id=? AND event_id=?',(cid,eid)).fetchone()
            if not row: raise HTTPException(404,'贡献不存在')
            c.execute('UPDATE contributions SET nickname=?,caption=?,demo=? WHERE id=?',(payload.nickname,payload.caption,payload.demo,cid))
            return model(c,e)
    @app.put('/api/events/{eid}/contributions/{cid}/image')
    async def upload(eid:str,cid:str,request:Request,key=Depends(bearer)):
        with db() as c: authorize(c,event(c,eid),key,cid=cid)
        buf=bytearray()
        async for chunk in request.stream():
            buf.extend(chunk)
            if len(buf)>MAX_BYTES: raise HTTPException(413,'图片不能超过 8 MB')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(buf)) as probe:
                    if probe.format not in ('JPEG','PNG','WEBP'): raise ValueError('unsupported')
                    if probe.width*probe.height>MAX_PIXELS: raise ValueError('pixels')
                    probe.verify()
                with Image.open(io.BytesIO(buf)) as src:
                    im=ImageOps.exif_transpose(src).convert('RGB'); im.thumbnail((1800,1800))
                    clean=Image.new('RGB',im.size); clean.paste(im)
                    output=io.BytesIO(); clean.save(output,'JPEG',quality=88,optimize=True)
        except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombWarning,Image.DecompressionBombError):
            raise HTTPException(400,'请选择有效的 JPG、PNG 或 WebP 图片（最多 2000 万像素）')
        with lock,db(True) as c:
            e=event(c,eid); authorize(c,e,key,cid=cid)
            row=c.execute('SELECT image FROM contributions WHERE id=? AND event_id=?',(cid,eid)).fetchone()
            if not row: raise HTTPException(404,'贡献已撤回')
            name=secrets.token_hex(24)+'.jpg'
            try:
                (media/name).write_bytes(output.getvalue())
                c.execute('UPDATE contributions SET image=?,demo=NULL WHERE id=?',(name,cid))
                c.commit()
            except Exception:
                unlink(name); raise
            unlink(row[0]); return model(c,e)
    @app.get('/api/events/{eid}/contributions/{cid}/image')
    def get_image(eid:str,cid:str,key=Depends(bearer)):
        with lock,db() as c:
            e=event(c,eid); authorize(c,e,key)
            row=c.execute('SELECT image FROM contributions WHERE id=? AND event_id=?',(cid,eid)).fetchone()
            if not row or not row[0]: raise HTTPException(404,'图片不存在')
            return Response((media/row[0]).read_bytes(),media_type='image/jpeg')
    @app.delete('/api/events/{eid}/contributions/{cid}',status_code=204)
    def withdraw(eid:str,cid:str,key=Depends(bearer)):
        with lock,db(True) as c:
            e=event(c,eid)
            row=c.execute('SELECT * FROM contributions WHERE id=? AND event_id=?',(cid,eid)).fetchone()
            if not row:
                # A withdrawn capability cannot touch other contributions; repeated delete is a no-op.
                return Response(status_code=204)
            authorize(c,e,key,cid=cid)
            c.execute('DELETE FROM contributions WHERE id=?',(cid,)); c.commit(); unlink(row['image'])
        return Response(status_code=204)
    @app.delete('/api/events/{eid}',status_code=204)
    def delete(eid:str,key=Depends(bearer)):
        with lock,db(True) as c:
            e=c.execute('SELECT * FROM events WHERE id=?',(eid,)).fetchone()
            if not e: return Response(status_code=204)
            authorize(c,e,key,owner=True)
            images=[r[0] for r in c.execute('SELECT image FROM contributions WHERE event_id=?',(eid,))]
            c.execute('INSERT OR IGNORE INTO deleted_creates VALUES (?)',(hashed(e['create_request']),))
            c.execute('DELETE FROM events WHERE id=?',(eid,)); c.commit()
            for name in images: unlink(name)
        return Response(status_code=204)
    static=ROOT/'static'
    static.mkdir(exist_ok=True)
    app.mount('/static',StaticFiles(directory=static),name='assets')
    app.mount('/',StaticFiles(directory=static,html=True),name='static')
    return app

app=create_app()
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=int(os.environ.get('PORT','8765')),access_log=False)
