"""검색.  기능 코드는 이 함수 하나만 부른다.  (조 추가 · 아키텍처 V2 의 OpenSearch 자리)

    hits = search.query('videos', '자료구조 #알고리즘',
                        fields={'title': 3, 'tags': 3, 'desc': 1},     # 필드별 가중치
                        eq={'category': '교육'},                        # 같음 필터
                        ranges={'duration': (240, 1200)})               # 범위 필터 (lo, hi) · None = 열림
    # → [{... 문서 ..., '_score': 7.0}, ...]  점수 높은 순

규칙
  - 검색어는 공백으로 나눈 단어들.  단어 하나라도 맞으면 결과에 들어간다 (OR).  맞은 필드 가중치를 더해 점수.
  - '#태그' 로 쓴 단어는 tags 필드에서 정확히 같은 것만 인정한다.
  - 검색어가 비어 있으면 필터만 적용하고 점수는 0.

로컬 구현은 core.db 를 전부 읽어 파이썬으로 점수를 매긴다 (db.find 와 같은 Scan 성격).

# TODO(조 · 7주차 이후): 이 파일이 Amazon OpenSearch Service 로 간다.
#   query()  → multi_match(fields=['title^3','tags^3','desc']) + bool.filter(term / range)
#   색인      → DynamoDB Streams → Lambda 가 videos 테이블 변경분을 OpenSearch 에 넣는다.
#               그래서 features/ 는 색인을 신경 쓰지 않는다 (지금처럼 db.put 만 한다).
"""
import re

from core import db

_WORD = re.compile(r'\S+')


def tokens(q: str) -> list:
    return [w.lower() for w in _WORD.findall(q or '')]


def _text(v) -> str:
    if isinstance(v, (list, tuple)):
        return ' '.join(str(x) for x in v).lower()
    return str(v or '').lower()


def _in_range(v, lo, hi) -> bool:
    if v is None:
        return False
    return (lo is None or v >= lo) and (hi is None or v <= hi)


def query(table: str, q: str = '', fields: dict | None = None, eq: dict | None = None, ranges: dict | None = None) -> list:
    fields = fields or {}
    words = tokens(q)
    hits = []
    for doc in db.all(table):
        if eq and any(doc.get(k) != v for k, v in eq.items()):
            continue
        if ranges and not all(_in_range(doc.get(k), lo, hi) for k, (lo, hi) in ranges.items()):
            continue
        score = 0.0
        for w in words:
            if w.startswith('#') and len(w) > 1:
                if w[1:] in [str(t).lower() for t in doc.get('tags', [])]:
                    score += fields.get('tags', 1)
                continue
            for f, weight in fields.items():
                if w in _text(doc.get(f)):
                    score += weight
        if words and score == 0:
            continue
        hits.append({**doc, '_score': score})
    hits.sort(key=lambda d: d['_score'], reverse=True)   # 안정 정렬 → 같은 점수면 최신순 유지
    return hits
