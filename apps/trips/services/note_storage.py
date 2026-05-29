import os
import uuid
from functools import lru_cache

import supabase as supabase_lib

BUCKET_NAME = 'connection_note_images'
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}


class NoteImageUploadError(Exception):
    pass


@lru_cache(maxsize=1)
def get_supabase_client():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise NoteImageUploadError(
            'SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment.',
        )
    return supabase_lib.create_client(url, key)


def storage_path_from_public_url(image_url: str) -> str | None:
    marker = f'/storage/v1/object/public/{BUCKET_NAME}/'
    if marker in image_url:
        return image_url.split(marker, 1)[1]
    return None


def upload_note_image(user_id: int, connection_id: int, uploaded_file) -> str:
    content_type = getattr(uploaded_file, 'content_type', None)
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise NoteImageUploadError(
            f'Unsupported image type. Allowed: {", ".join(ALLOWED_CONTENT_TYPES)}.',
        )

    size = getattr(uploaded_file, 'size', None)
    if size is None:
        data = uploaded_file.read()
        size = len(data)
        uploaded_file.seek(0)
    else:
        data = None

    if size > MAX_IMAGE_BYTES:
        raise NoteImageUploadError('Image exceeds the 5 MB size limit.')

    ext = ALLOWED_CONTENT_TYPES[content_type]
    storage_path = f'{user_id}/{connection_id}/{uuid.uuid4()}{ext}'

    if data is None:
        data = uploaded_file.read()

    client = get_supabase_client()
    try:
        client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=data,
            file_options={'content-type': content_type, 'upsert': 'true'},
        )
    except Exception as exc:
        raise NoteImageUploadError(f'Failed to upload image to storage: {exc}') from exc
    return client.storage.from_(BUCKET_NAME).get_public_url(storage_path)


def delete_note_image(image_url: str) -> None:
    storage_path = storage_path_from_public_url(image_url)
    if not storage_path:
        return

    client = get_supabase_client()
    client.storage.from_(BUCKET_NAME).remove([storage_path])
