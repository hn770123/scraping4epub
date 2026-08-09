# -*- coding: utf-8 -*-
"""
tests/test_epub_builder.py
EpubBuilderクラスおよびContentConverterクラスのテスト。
"""

import os
import unittest
import zipfile
from bs4 import BeautifulSoup
from src.epub_builder import EpubBuilder
from src.converter import ContentConverter

class TestEpubBuilder(unittest.TestCase):
    """
    EPUBビルダーおよびコンバーターの動作確認テスト。
    """

    def setUp(self):
        self.test_output = "test_output.epub"
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def tearDown(self):
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def test_content_converter(self):
        """
        ContentConverterによるHTMLクレンジングおよびXHTMLへの変換テスト。
        """
        converter = ContentConverter()

        # 不要なタグがクレンジングされるかテスト
        raw_html = "<p>本文1</p><script>alert('bad');</script><style>body { color: red; }</style><p>本文2 <ruby>猫猫<rt>マオマオ</rt></ruby></p>"
        cleaned = converter.clean_html(raw_html)

        self.assertIn("本文1", cleaned)
        self.assertIn("本文2", cleaned)
        self.assertIn("<ruby>", cleaned)
        self.assertIn("<rt>マオマオ</rt>", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("<style>", cleaned)

        # XHTML変換テスト
        xhtml = converter.convert_to_xhtml("テスト章", cleaned)
        soup = BeautifulSoup(xhtml, "xml")

        # XHTML5として必要な名前空間および構造が定義されているか検証
        self.assertEqual(soup.html["xmlns"], "http://www.w3.org/1999/xhtml")
        self.assertEqual(soup.title.string, "テスト章")
        self.assertIsNotNone(soup.find("link", href="style.css"))

    def test_build_epub_structure(self):
        """
        実際にEPUBファイルをビルドし、EPUB仕様に準拠したZIP構造が構築されているかテスト。
        """
        builder = EpubBuilder(self.test_output)

        meta = {
            "title": "薬屋のひとりごと",
            "author": "日向夏",
            "introduction": "薬草を取りに出かけたら、後宮の女官狩りに遭いました。"
        }

        chapters = [
            {"title": "１　猫猫", "content": "<p>（露天の串焼きが食べたいなあ）</p>"},
            {"title": "２　二人の妃", "content": "<p>桜が散り、新緑の季節へと移り変わる。</p>"}
        ]

        result = builder.build_epub(meta, chapters)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_output))

        # ZIPアーカイブとしての正当性の検証
        with zipfile.ZipFile(self.test_output, 'r') as z:
            namelist = z.namelist()

            # 必要なファイルがすべて格納されているか検証
            self.assertIn("mimetype", namelist)
            self.assertIn("META-INF/container.xml", namelist)
            self.assertIn("OEBPS/content.opf", namelist)
            self.assertIn("OEBPS/nav.xhtml", namelist)
            self.assertIn("OEBPS/toc.ncx", namelist)
            self.assertIn("OEBPS/style.css", namelist)
            self.assertIn("OEBPS/introduction.xhtml", namelist)
            self.assertIn("OEBPS/chapter_1.xhtml", namelist)
            self.assertIn("OEBPS/chapter_2.xhtml", namelist)

            # mimetype仕様の厳密な検証（ZIPアーカイブの最初のファイル、かつ非圧縮であること）
            first_info = z.infolist()[0]
            self.assertEqual(first_info.filename, "mimetype")
            self.assertEqual(first_info.compress_type, zipfile.ZIP_STORED)
            self.assertEqual(z.read("mimetype"), b"application/epub+zip")

            # container.xml の検証（content.opfへの正しいフルパス）
            container_data = z.read("META-INF/container.xml").decode("utf-8")
            self.assertIn('full-path="OEBPS/content.opf"', container_data)

            # content.opf のメタデータ検証
            opf_data = z.read("OEBPS/content.opf").decode("utf-8")
            opf_soup = BeautifulSoup(opf_data, "xml")
            self.assertEqual(opf_soup.find("dc:title").string, "薬屋のひとりごと")
            self.assertEqual(opf_soup.find("dc:creator").string, "日向夏")
            self.assertEqual(opf_soup.find("dc:language").string, "ja")

            # nav.xhtml (目次) の検証
            nav_data = z.read("OEBPS/nav.xhtml").decode("utf-8")
            nav_soup = BeautifulSoup(nav_data, "xml")
            links = [a["href"] for a in nav_soup.find_all("a")]
            self.assertIn("introduction.xhtml", links)
            self.assertIn("chapter_1.xhtml", links)
            self.assertIn("chapter_2.xhtml", links)

if __name__ == "__main__":
    unittest.main()
