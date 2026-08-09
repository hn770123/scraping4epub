# -*- coding: utf-8 -*-
"""
tests/test_epub_builder.py
EpubBuilderクラスのテスト。
"""

import os
import unittest
from src.epub_builder import EpubBuilder

class TestEpubBuilder(unittest.TestCase):
    """
    EPUBビルダーの動作確認テスト。
    """

    def setUp(self):
        self.test_output = "test_output.epub"
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def tearDown(self):
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def test_build_stub(self):
        """
        EPUB構築スタブのテスト。
        """
        builder = EpubBuilder(self.test_output)
        meta = {"title": "テストタイトル", "author": "テスト作者"}
        result = builder.build_epub(meta, [])
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_output))

if __name__ == "__main__":
    unittest.main()
