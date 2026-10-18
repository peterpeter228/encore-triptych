import io, sys, uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c: yield c

def auth(key): return {'Authorization':'Bearer '+key}
def create(client):
    body={'title':'安可现场','date':'2026-10-18','organizer':'主办人','nickname':'我','caption':'最后一首歌','demo':'stage','request_id':str(uuid.uuid4())}
    r=client.post('/api/events',json=body); assert r.status_code==201,r.text
    return r.json(),body

def join(client,x,rid=None):
    return client.post('/api/invites/'+x['invite_token']+'/join',json={'nickname':'朋友','caption':'不同的视角','demo':'crowd','request_id':rid or str(uuid.uuid4())})
def test_create_retry_and_secret_separation(client):
    x,body=create(client); eid=x['event']['id']
    assert client.post('/api/events',json=body).json()==x
    assert client.get('/api/events/'+eid).status_code==401
    public=client.get('/api/events/'+eid,headers=auth(x['view_key'])).json()
    assert public==x['event']
    for key in ('owner_key','view_key','invite_token','contribution_key'):
        assert x[key] not in str(public)
    assert client.delete('/api/events/'+eid,headers=auth(x['view_key'])).status_code==403

def test_concurrent_join_capacity_and_retry(client):
    x,_=create(client); rid=str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=6) as pool:
        res=list(pool.map(lambda _:join(client,x,rid),range(6)))
    assert all(r.status_code==201 for r in res)
    assert len({r.json()['contribution_id'] for r in res})==1
    with ThreadPoolExecutor(max_workers=6) as pool:
        res=list(pool.map(lambda _:join(client,x),range(6)))
    assert [r.status_code for r in res].count(201)==1
    assert [r.status_code for r in res].count(409)==5
    event=client.get('/api/events/'+x['event']['id'],headers=auth(x['view_key'])).json()
    assert event['count']==3
    assert len({r['slot'] for r in event['contributions']})==3

def test_permissions_rotate_withdraw(client):
    x,_=create(client); rid=str(uuid.uuid4()); y=join(client,x,rid).json(); eid=x['event']['id']
    path='/api/events/'+eid+'/contributions/'
    assert client.delete(path+x['contribution_id'],headers=auth(y['contribution_key'])).status_code==403
    assert client.delete('/api/events/'+eid+'/invite',headers=auth(y['contribution_key'])).status_code==403
    assert client.delete(path+y['contribution_id'],headers=auth(y['contribution_key'])).status_code==204
    assert client.delete(path+y['contribution_id'],headers=auth(y['contribution_key'])).status_code==204
    assert join(client,x,rid).status_code==410
    new=client.post('/api/events/'+eid+'/invite',headers=auth(x['owner_key'])).json()['invite_token']
    assert client.get('/api/invites/'+x['invite_token']).status_code==404
    x['invite_token']=new; assert join(client,x).status_code==201
    assert client.delete('/api/events/'+eid+'/invite',headers=auth(x['owner_key'])).status_code==204
    assert client.get('/api/invites/'+new).status_code==404

def test_upload_strip_metadata_and_delete(client):
    x,_=create(client); eid=x['event']['id']; path=f"/api/events/{eid}/contributions/{x['contribution_id']}/image"
    im=Image.new('RGB',(2000,1000),'purple'); exif=Image.Exif(); exif[270]='secret location'; out=io.BytesIO(); im.save(out,'JPEG',exif=exif)
    assert client.put(path,content=out.getvalue(),headers=auth(x['view_key'])).status_code==403
    assert client.put(path,content=b'<svg/>',headers=auth(x['contribution_key'])).status_code==400
    assert client.put(path,content=out.getvalue(),headers=auth(x['contribution_key'])).status_code==200
    assert client.get(path).status_code==401
    result=client.get(path,headers=auth(x['view_key']))
    clean=Image.open(io.BytesIO(result.content)); assert clean.width==1800; assert not clean.getexif()
    assert len(list((client.app.state.data_dir/'media').iterdir()))==1
    assert client.delete('/api/events/'+eid,headers=auth(x['owner_key'])).status_code==204
    assert not list((client.app.state.data_dir/'media').iterdir())
    assert client.get(path,headers=auth(x['view_key'])).status_code==404
    assert client.delete('/api/events/'+eid,headers=auth(x['owner_key'])).status_code==204

def test_validation_and_restart(client):
    x,body=create(client); eid=x['event']['id']
    body['request_id']=str(uuid.uuid4()); body['title']=' '; assert client.post('/api/events',json=body).status_code==422
    body['title']='a'*81; assert client.post('/api/events',json=body).status_code==422
    with TestClient(create_app(client.app.state.data_dir)) as restarted:
        assert restarted.get('/api/events/'+eid,headers=auth(x['owner_key'])).json()==x['event']
    assert client.get('/api/health',headers={'host':'evil.example'}).status_code==403
    assert client.post('/api/events',json=body,headers={'origin':'https://evil.example'}).status_code==403

def test_withdraw_removes_media(client):
    x,_=create(client); y=join(client,x).json(); eid=x['event']['id']; path=f"/api/events/{eid}/contributions/{y['contribution_id']}"
    out=io.BytesIO(); Image.new('RGB',(30,30)).save(out,'PNG')
    assert client.put(path+'/image',content=out.getvalue(),headers=auth(y['contribution_key'])).status_code==200
    assert client.delete(path,headers=auth(y['contribution_key'])).status_code==204
    assert not list((client.app.state.data_dir/'media').iterdir())
    assert client.put(path+'/image',content=out.getvalue(),headers=auth(y['contribution_key'])).status_code==403

def test_deleted_create_retry_does_not_resurrect(client):
    x,body=create(client)
    assert client.delete('/api/events/'+x['event']['id'],headers=auth(x['owner_key'])).status_code==204
    assert client.post('/api/events',json=body).status_code==410

def test_retry_never_returns_revoked_invite(client):
    x,body=create(client)
    client.delete('/api/events/'+x['event']['id']+'/invite',headers=auth(x['owner_key']))
    retry=client.post('/api/events',json=body).json()
    assert retry['invite_token'] is None

def test_corrupt_oversized_and_traversal(client):
    x,_=create(client); path=f"/api/events/{x['event']['id']}/contributions/{x['contribution_id']}/image"
    assert client.put(path,content=b'x'*(8*1024*1024+1),headers=auth(x['owner_key'])).status_code==413
    out=io.BytesIO(); Image.new('RGB',(5000,4100)).save(out,'PNG')
    assert client.put(path,content=out.getvalue(),headers=auth(x['owner_key'])).status_code==400
    assert client.get('/data/encore.sqlite3').status_code==404
    assert client.get('/static/../app.py').status_code==404

def test_crash_orphans_cleaned_on_restart(client):
    orphan=client.app.state.data_dir/'media'/'orphan.jpg'; orphan.write_bytes(b'not exposed')
    with TestClient(create_app(client.app.state.data_dir)) as restarted:
        assert not orphan.exists()

def test_owner_cannot_modify_other_contributor(client):
    x,_=create(client); y=join(client,x).json(); path=f"/api/events/{x['event']['id']}/contributions/{y['contribution_id']}"
    assert client.delete(path,headers=auth(x['owner_key'])).status_code==403
    assert client.put(path,json={'nickname':'改名'},headers=auth(x['owner_key'])).status_code==403

def test_owner_retry_after_own_slot_reused(client):
    x,body=create(client); eid=x['event']['id']
    client.delete(f"/api/events/{eid}/contributions/{x['contribution_id']}",headers=auth(x['owner_key']))
    y=join(client,x).json()
    retry=client.post('/api/events',json=body).json()
    assert retry['contribution_id'] is None
    assert retry['event']['contributions'][0]['id']==y['contribution_id']

def test_image_versions_change_without_exposing_filename(client):
    x,_=create(client); eid=x['event']['id']; path=f"/api/events/{eid}/contributions/{x['contribution_id']}/image"
    out=io.BytesIO(); Image.new('RGB',(20,20)).save(out,'PNG')
    first=client.put(path,content=out.getvalue(),headers=auth(x['owner_key'])).json()['contributions'][0]['image_url']
    second=client.put(path,content=out.getvalue(),headers=auth(x['owner_key'])).json()['contributions'][0]['image_url']
    assert first!=second
    assert client.get(second,headers=auth(x['view_key'])).status_code==200
    assert not any(p.name in second for p in (client.app.state.data_dir/'media').iterdir())
