import os
import tempfile
from uuid import uuid4

from utils.storage import IMAGE_DIR


IMAGE_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/avif': '.avif',
}


def download_image(url, client):
    """Download with the API client's token and return the completed filename."""
    temporary_path = None
    try:
        with client.get(url, stream=True, timeout=30) as response:
            content_type = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            extension = IMAGE_EXTENSIONS.get(content_type)
            if extension is None:
                raise ValueError('Provider did not return a supported image')
            filename = uuid4().hex + extension
            size = 0
            with tempfile.NamedTemporaryFile(dir=IMAGE_DIR, delete=False) as image:
                temporary_path = image.name
                for chunk in response.iter_content(chunk_size=65536):
                    image.write(chunk)
                    size += len(chunk)
            if size == 0:
                raise ValueError('Provider returned an empty image')
            os.replace(temporary_path, IMAGE_DIR / filename)
            return filename
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)
