"""[조 추가] 검색 · 필터 · 정렬.   core.search 를 부른다 (V2 아키텍처의 OpenSearch 자리).
   GET /api/search/?q=&sort=&date=&duration=&category=
        sort     : relevance(관련성) | latest(업로드 날짜) | views(조회수) | likes(좋아요)
        date     : any | hour | today | week | month | year      (업로드 날짜)
        duration : any | short(4분 미만) | medium(4~20분) | long(20분 초과)
        category : '' | 브이로그 | 교육 | …                       (features.videos.CATEGORIES)
        q 에 '#태그' 를 쓰면 해시태그로 찾는다.
   → {items, total, categories: {카테고리: 개수}}   (categories 는 카테고리 필터를 빼고 센 값 — 필터 칩 숫자)
"""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from core import search
from features.videos.api import CATEGORIES, view

bp = Blueprint('search', __name__)

FIELDS = {'title': 3, 'tags': 3, 'uploader_name': 2, 'desc': 1}
DATES = {'hour': timedelta(hours=1), 'today': timedelta(days=1), 'week': timedelta(days=7),
         'month': timedelta(days=30), 'year': timedelta(days=365)}
DURATIONS = {'short': (0, 239), 'medium': (240, 1200), 'long': (1201, None)}
SORTS = {
    'latest': lambda v: v.get('created_at', ''),
    'views': lambda v: v.get('views', 0),
    'likes': lambda v: len(v.get('likes', [])),
}


@bp.get('/')
def index():
    a = request.args
    q = (a.get('q') or '').strip()
    sort = a.get('sort') or 'relevance'
    category = a.get('category') or ''

    ranges = {}
    if a.get('date') in DATES:
        since = datetime.now(timezone.utc) - DATES[a['date']]
        ranges['created_at'] = (since.isoformat(timespec='microseconds'), None)
    if a.get('duration') in DURATIONS:
        ranges['duration'] = DURATIONS[a['duration']]

    hits = search.query('videos', q, fields=FIELDS, ranges=ranges)
    counts = {c: 0 for c in CATEGORIES}
    for h in hits:
        c = h.get('category') or '기타'
        counts[c] = counts.get(c, 0) + 1
    if category:
        hits = [h for h in hits if (h.get('category') or '기타') == category]

    if sort in SORTS:
        hits.sort(key=SORTS[sort], reverse=True)
    return jsonify(items=[view(h) for h in hits], total=len(hits), categories=counts)
