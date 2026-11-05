from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from utils.images import download_image


class ImageDownloadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.image_dir = Path(self.directory.name)
        patcher = patch('utils.images.IMAGE_DIR', self.image_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = MagicMock()
        self.response = self.client.get.return_value.__enter__.return_value
        self.response.headers = {'Content-Type': 'image/png'}
        self.response.iter_content.return_value = [b'image bytes']

    def test_completed_download(self):
        filename = download_image('https://example.com/image', self.client)
        self.assertEqual((self.image_dir / filename).read_bytes(), b'image bytes')
        self.assertTrue(filename.endswith('.png'))
        self.assertEqual(list(self.image_dir.iterdir()), [self.image_dir / filename])
        self.client.get.assert_called_once_with('https://example.com/image', stream=True, timeout=30)

    def test_html_response_is_not_saved(self):
        self.response.headers = {'Content-Type': 'text/html'}
        with self.assertRaises(ValueError):
            download_image('https://example.com/image', self.client)
        self.assertEqual(list(self.image_dir.iterdir()), [])

    def test_empty_response_is_not_saved(self):
        self.response.iter_content.return_value = []
        with self.assertRaises(ValueError):
            download_image('https://example.com/image', self.client)
        self.assertEqual(list(self.image_dir.iterdir()), [])

    def test_interrupted_download_keeps_existing_image(self):
        existing = self.image_dir / 'existing.png'
        existing.write_bytes(b'previous image')

        def chunks():
            yield b'partial download'
            raise requests.ConnectionError('download interrupted')

        self.response.iter_content.return_value = chunks()
        with self.assertRaises(requests.ConnectionError):
            download_image('https://example.com/image', self.client)
        self.assertEqual(existing.read_bytes(), b'previous image')
        self.assertEqual(list(self.image_dir.iterdir()), [existing])
