"""파일 저장.  기능 코드는 이 두 함수만 부른다.

    key = storage.save(request.files['photo'])   # 저장하고 키를 받는다
    src = storage.url(key)                       # 화면에 보여줄 주소

.env 의 STORAGE_BACKEND 값에 따라 동작한다:
  - STORAGE_BACKEND=local (기본값) → 로컬 uploads/ 폴더에 저장, /uploads/<key> 반환
  - STORAGE_BACKEND=s3             → S3 버킷(S3_BUCKET)에 put_object, Presigned URL 반환
"""
import mimetypes
import os
import shutil
import uuid

from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov', '.pdf'}

_s3_client = None


class NotAllowed(ValueError):
    pass


def _backend() -> str:
    return os.getenv('STORAGE_BACKEND', 'local').strip().lower()


def _bucket() -> str:
    bucket = os.getenv('S3_BUCKET', '').strip()
    if not bucket:
        raise RuntimeError('STORAGE_BACKEND=s3 이지만 .env 에 S3_BUCKET 이 설정되지 않았습니다.')
    return bucket


def _region() -> str:
    return os.getenv('AWS_REGION', 'ap-northeast-2').strip()


def _s3():
    global _s3_client
    if _s3_client is None:
        import boto3
        from botocore.config import Config
        _s3_client = boto3.client(
            's3',
            region_name=_region(),
            config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}),
        )
    return _s3_client


def save(file_storage) -> str:
    """업로드 파일을 저장하고 key(파일 이름)를 돌려준다. 파일이 없으면 ''.
    허용되지 않은 확장자면 NotAllowed 를 던진다 (app.py 가 400 JSON 으로 바꿔 준다)."""
    if not file_storage or not file_storage.filename:
        return ''
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower()
    if ext not in ALLOWED:
        raise NotAllowed(f'허용되지 않는 파일 형식입니다: {ext or "(확장자 없음)"}')
    key = f'{uuid.uuid4().hex}{ext}'

    if _backend() == 's3':
        content_type = file_storage.mimetype or mimetypes.guess_type(key)[0] or 'application/octet-stream'
        _s3().put_object(
            Bucket=_bucket(),
            Key=key,
            Body=file_storage.read(),
            ContentType=content_type,
        )
        return key

    file_storage.save(os.path.join(UPLOAD_DIR, key))
    _warn_if_full()
    return key


def put_bytes(data: bytes, ext: str) -> str:
    """바이트를 바로 저장 (seed 데이터, 9주차 썸네일 Lambda 등)."""
    key = f'{uuid.uuid4().hex}{ext}'
    if _backend() == 's3':
        content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
        _s3().put_object(
            Bucket=_bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    with open(os.path.join(UPLOAD_DIR, key), 'wb') as f:
        f.write(data)
    return key


def url(key: str) -> str:
    """key 를 브라우저가 열 수 있는 주소로."""
    if not key:
        return ''
    if _backend() == 's3':
        return _s3().generate_presigned_url(
            'get_object',
            Params={'Bucket': _bucket(), 'Key': key},
            ExpiresIn=3600,
        )
    return f'/uploads/{key}'


def delete(key: str) -> None:
    if not key:
        return
    if _backend() == 's3':
        _s3().delete_object(Bucket=_bucket(), Key=key)
        return
    try:
        os.remove(os.path.join(UPLOAD_DIR, key))
    except FileNotFoundError:
        pass


def _warn_if_full():
    """서버 디스크에 파일을 쌓으면 어떤 일이 생기는지 보여주는 경고."""
    total, used, free = shutil.disk_usage(UPLOAD_DIR)
    n = len(os.listdir(UPLOAD_DIR))
    if n and n % 20 == 0:
        print(f'[storage] uploads/ 에 파일 {n}개 · 디스크 남은 공간 {free // 2**30}GB — 이 폴더는 서버와 함께 사라집니다')
