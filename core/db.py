"""데이터 저장.  키-값 문서 저장소 인터페이스.  기능 코드는 이 함수들만 부른다.

    db.put('items', {'id': ..., 'title': ...})   # 저장 (id 없으면 만들어 준다)
    db.get('items', id)                          # 하나
    db.find('items', seller='kim')               # 조건(같음)으로 여럿
    db.all('items')                              # 전부 (최신순)
    db.update('items', id, price=9000)           # 일부 필드
    db.delete('items', id)

.env 의 DB_BACKEND 값에 따라 동작한다:
  - DB_BACKEND=sqlite   (기본값) → 로컬 SQLite data.db 파일에 저장
  - DB_BACKEND=dynamodb          → AWS DynamoDB (테이블명 = DDB_PREFIX + table, PK = id)에 저장
"""
import builtins
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.db')
_lock = threading.RLock()
_known = set()
_conn_obj = None
_ddb_resource = None


def _backend() -> str:
    return os.getenv('DB_BACKEND', 'sqlite').strip().lower()


def _prefix() -> str:
    return os.getenv('DDB_PREFIX', 'tubelite-').strip()


def _region() -> str:
    return os.getenv('AWS_REGION', 'ap-northeast-2').strip()


def _ddb():
    global _ddb_resource
    if _ddb_resource is None:
        import boto3
        _ddb_resource = boto3.resource('dynamodb', region_name=_region())
    return _ddb_resource


def _to_ddb(obj):
    """DynamoDB는 float를 직접 허용하지 않으므로 Decimal로 변환한다."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_ddb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_ddb(v) for v in obj]
    return obj


def _from_ddb(obj):
    """DynamoDB에서 읽은 Decimal을 int 또는 float로 복원한다."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _from_ddb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_ddb(v) for v in obj]
    return obj


def _conn():
    """연결은 프로세스에 하나만 둔다 (Flask 스레드가 여럿이라 lock 으로 감싼다)."""
    global _conn_obj
    if _conn_obj is None:
        _conn_obj = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn_obj.row_factory = sqlite3.Row
        _conn_obj.execute('PRAGMA journal_mode=WAL')
    return _conn_obj


def close():
    global _conn_obj
    if _conn_obj is not None:
        _conn_obj.close()
        _conn_obj = None
    _known.clear()


def _ddb_table(table: str):
    tname = f'{_prefix()}{table}'
    ddb = _ddb()
    tbl = ddb.Table(tname)
    if tname not in _known:
        with _lock:
            if tname not in _known:
                from botocore.exceptions import ClientError
                try:
                    tbl.load()
                except ClientError as e:
                    code = e.response.get('Error', {}).get('Code', '')
                    if code == 'ResourceNotFoundException':
                        print(f'[db] DynamoDB 테이블 자동 생성 중: {tname} (PK: id)')
                        tbl = ddb.create_table(
                            TableName=tname,
                            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                            BillingMode='PAY_PER_REQUEST',
                        )
                        tbl.wait_until_exists()
                        print(f'[db] DynamoDB 테이블 생성 완료: {tname}')
                    else:
                        raise
                _known.add(tname)
    return tbl


def _ensure(table: str):
    if _backend() == 'dynamodb':
        _ddb_table(table)
        return
    if table in _known:
        return
    with _lock:
        _conn().execute(
            f'CREATE TABLE IF NOT EXISTS "{table}" (id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT NOT NULL)')
        _conn().commit()
    _known.add(table)


def init():
    if _backend() == 'dynamodb':
        print(f'[db] DynamoDB 모드 (리전: {_region()}, 접두사: {_prefix()}) · storage={os.getenv("STORAGE_BACKEND", "local")}')
    else:
        print(f'[db] SQLite {DB_PATH} — 이 파일이 지워지면 데이터도 사라집니다 (DB_BACKEND=dynamodb 로 전환 가능)')


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def put(table: str, item: dict) -> dict:
    item = dict(item)
    item.setdefault('id', uuid.uuid4().hex[:12])
    item.setdefault('created_at', now())

    if _backend() == 'dynamodb':
        tbl = _ddb_table(table)
        tbl.put_item(Item=_to_ddb(item))
        return item

    _ensure(table)
    with _lock:
        _conn().execute(f'INSERT OR REPLACE INTO "{table}" (id, data, created_at) VALUES (?, ?, ?)',
                        (item['id'], json.dumps(item, ensure_ascii=False), item['created_at']))
        _conn().commit()
    return item


def get(table: str, id: str):
    if _backend() == 'dynamodb':
        tbl = _ddb_table(table)
        resp = tbl.get_item(Key={'id': str(id)})
        item = resp.get('Item')
        return _from_ddb(item) if item else None

    _ensure(table)
    with _lock:
        row = _conn().execute(f'SELECT data FROM "{table}" WHERE id=?', (id,)).fetchone()
    return json.loads(row['data']) if row else None


def all(table: str, desc: bool = True) -> list:
    if _backend() == 'dynamodb':
        tbl = _ddb_table(table)
        items = []
        resp = tbl.scan()
        items.extend(resp.get('Items', []))
        while 'LastEvaluatedKey' in resp:
            resp = tbl.scan(ExclusiveStartKey=resp['LastEvaluatedKey'])
            items.extend(resp.get('Items', []))
        parsed = [_from_ddb(x) for x in items]
        parsed.sort(key=lambda x: (x.get('created_at', ''), x.get('id', '')), reverse=desc)
        return parsed

    _ensure(table)
    order = 'DESC' if desc else 'ASC'
    with _lock:
        rows = _conn().execute(f'SELECT data FROM "{table}" ORDER BY created_at {order}, id {order}').fetchall()
    return [json.loads(r['data']) for r in rows]


def find(table: str, **eq) -> list:
    """같음 조건만. DynamoDB 모드에서는 Scan + FilterExpression 으로 조회한다."""
    if _backend() == 'dynamodb' and eq:
        from boto3.dynamodb.conditions import Attr
        tbl = _ddb_table(table)
        expr = None
        for k, v in eq.items():
            cond = Attr(k).eq(_to_ddb(v))
            expr = cond if expr is None else (expr & cond)
        items = []
        resp = tbl.scan(FilterExpression=expr)
        items.extend(resp.get('Items', []))
        while 'LastEvaluatedKey' in resp:
            resp = tbl.scan(FilterExpression=expr, ExclusiveStartKey=resp['LastEvaluatedKey'])
            items.extend(resp.get('Items', []))
        parsed = [_from_ddb(x) for x in items]
        parsed.sort(key=lambda x: (x.get('created_at', ''), x.get('id', '')), reverse=True)
        return parsed

    return [x for x in all(table) if builtins.all(x.get(k) == v for k, v in eq.items())]


def update(table: str, id: str, **fields):
    item = get(table, id)
    if item is None:
        return None
    item.update(fields)
    return put(table, item)


def delete(table: str, id: str) -> None:
    if _backend() == 'dynamodb':
        tbl = _ddb_table(table)
        tbl.delete_item(Key={'id': str(id)})
        return

    _ensure(table)
    with _lock:
        _conn().execute(f'DELETE FROM "{table}" WHERE id=?', (id,))
        _conn().commit()
