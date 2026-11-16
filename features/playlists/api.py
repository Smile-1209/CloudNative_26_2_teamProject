"""[조 추가] 재생목록 · 나중에 볼 동영상.   playlists 테이블.
   "나중에 볼 동영상" 은 사람마다 하나 있는 특별한 재생목록이다 (id = "WL_<아이디>", 지울 수 없음).
   주소에서는 'WL' 로 부르면 내 것으로 바뀐다.  (/api/playlists/WL)

   GET  /api/playlists/                    → 내 재생목록 (나중에 볼 동영상이 맨 앞)
   POST /api/playlists/                    → 만들기 {title, visibility: private|public, video_id?}
   GET  /api/playlists/saved/<video_id>    → 저장 대화상자용 [{id, title, kind, has}]
   GET  /api/playlists/<id>                → {playlist, owner, videos}   비공개는 주인만
   POST /api/playlists/<id>/toggle         → {video_id} 넣기/빼기 → {has, count}
   POST /api/playlists/<id>/delete         → 삭제 (나중에 볼 동영상은 못 지움)

데이터는 core.db 만 쓴다 → 7주차에 DynamoDB 로 같이 간다.
영상 목록은 video_ids 배열 하나로 둔다 (DynamoDB 한 항목 · 400KB 안이면 수천 개).
"""
from flask import Blueprint, jsonify, request, session

from core import db
from core.auth import login_required
from features.videos.api import channel_of, view

bp = Blueprint('playlists', __name__)

MAX_VIDEOS = 500


def _wl_id(uid):
    return f'WL_{uid}'


def _ensure_wl(uid):
    wl = db.get('playlists', _wl_id(uid))
    if not wl:
        wl = db.put('playlists', {'id': _wl_id(uid), 'owner': uid, 'title': '나중에 볼 동영상', 'kind': 'watch_later',
                                  'visibility': 'private', 'video_ids': [], 'updated_at': db.now()})
    return wl


def _resolve(id):
    uid = session.get('user_id')
    if id == 'WL':
        return _ensure_wl(uid) if uid else None
    return db.get('playlists', id)


def _can_see(p):
    return p['visibility'] == 'public' or p['owner'] == session.get('user_id')


def summary(p):
    first = next((v for v in (db.get('videos', i) for i in p['video_ids']) if v), None)
    return {k: p[k] for k in ('id', 'owner', 'title', 'kind', 'visibility', 'updated_at')} | {
        'count': len(p['video_ids']), 'thumb_url': view(first, with_channel=False)['thumb_url'] if first else ''}


@bp.get('/')
@login_required
def mine():
    uid = session['user_id']
    wl = _ensure_wl(uid)
    others = sorted((p for p in db.find('playlists', owner=uid) if p['id'] != wl['id']),
                    key=lambda p: p['updated_at'], reverse=True)
    return jsonify([summary(p) for p in [wl, *others]])


@bp.post('/')
@login_required
def create():
    d = request.get_json(silent=True) or {}
    title = (d.get('title') or '').strip()
    if not title:
        return jsonify(error='재생목록 제목을 입력하세요.'), 400
    vid = d.get('video_id')
    p = db.put('playlists', {'owner': session['user_id'], 'title': title[:150], 'kind': 'normal',
                             'visibility': 'public' if d.get('visibility') == 'public' else 'private',
                             'video_ids': [vid] if vid and db.get('videos', vid) else [], 'updated_at': db.now()})
    return jsonify(summary(p)), 201


@bp.get('/saved/<video_id>')
@login_required
def saved(video_id):
    uid = session['user_id']
    wl = _ensure_wl(uid)
    others = sorted((p for p in db.find('playlists', owner=uid) if p['id'] != wl['id']),
                    key=lambda p: p['updated_at'], reverse=True)
    return jsonify([{'id': p['id'], 'title': p['title'], 'kind': p['kind'], 'visibility': p['visibility'],
                     'has': video_id in p['video_ids']} for p in [wl, *others]])


@bp.get('/<id>')
def detail(id):
    if id == 'WL' and not session.get('user_id'):
        return jsonify(error='로그인이 필요합니다.'), 401
    p = _resolve(id)
    if not p or not _can_see(p):
        return jsonify(error='없거나 비공개인 재생목록입니다.'), 404
    videos = [view(v) for v in (db.get('videos', i) for i in p['video_ids']) if v]
    return jsonify(playlist=summary(p), owner=channel_of(p['owner'], session.get('user_id')), videos=videos)


@bp.post('/<id>/toggle')
@login_required
def toggle(id):
    p = _resolve(id)
    if not p or p['owner'] != session['user_id']:
        return jsonify(error='없는 재생목록입니다.'), 404
    vid = (request.get_json(silent=True) or {}).get('video_id')
    if not vid or not db.get('videos', vid):
        return jsonify(error='없는 동영상입니다.'), 404
    ids = list(p['video_ids'])
    if vid in ids:
        ids.remove(vid)
    elif len(ids) >= MAX_VIDEOS:
        return jsonify(error=f'재생목록에는 {MAX_VIDEOS}개까지 담을 수 있습니다.'), 400
    else:
        ids.insert(0, vid)   # 최근에 담은 것이 위로
    p = db.update('playlists', p['id'], video_ids=ids, updated_at=db.now())
    return jsonify(has=vid in ids, count=len(ids))


@bp.post('/<id>/delete')
@login_required
def delete(id):
    p = _resolve(id)
    if not p or p['owner'] != session['user_id']:
        return jsonify(error='없는 재생목록입니다.'), 404
    if p['kind'] == 'watch_later':
        return jsonify(error='나중에 볼 동영상 목록은 지울 수 없습니다.'), 400
    db.delete('playlists', p['id'])
    return jsonify(ok=True)
