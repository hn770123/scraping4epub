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

    def test_content_converter_broken_html(self):
        """
        ContentConverterにおいて、壊れたHTMLや空のHTML、無効な入力データが渡された場合に、
        クラッシュせず正しくパースされ、妥当なXHTMLとして自動修正されるかテストします。
        """
        converter = ContentConverter()

        # 壊れたHTML（閉じタグの欠落など）
        broken_html = "<div><p>テスト本文"
        cleaned = converter.clean_html(broken_html)
        xhtml = converter.convert_to_xhtml("壊れたテスト", cleaned)

        # BeautifulSoupのxmlパーサーで、厳密なXML/XHTMLとして問題なくパースできるか検証
        soup = BeautifulSoup(xhtml, "xml")
        self.assertEqual(soup.title.string, "壊れたテスト")
        # 閉じタグが自動で補完され、pタグが抽出できるか検証
        self.assertIsNotNone(soup.find("p"))
        self.assertEqual(soup.find("p").string, "テスト本文")

        # 空のHTML
        empty_html = ""
        cleaned_empty = converter.clean_html(empty_html)
        self.assertEqual(cleaned_empty, "")

    def test_epub_builder_incomplete_metadata(self):
        """
        EpubBuilderにおいて、不完全なメタデータ（タイトルや著者が欠落しているなど）や、
        空チャプターリストが渡された場合、自動的にデフォルト値で補完されビルドが成功するかテストします。
        """
        builder = EpubBuilder(self.test_output)

        incomplete_meta = {}  # 完全に空のメタデータ
        chapters = []        # 完全に空のチャプター

        result = builder.build_epub(incomplete_meta, chapters)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_output))

        # ビルドされたEPUBの content.opf を読み込み、デフォルト値（No Title / Syosetu Downloader）が設定されているか検証
        with zipfile.ZipFile(self.test_output, 'r') as z:
            opf_data = z.read("OEBPS/content.opf").decode("utf-8")
            opf_soup = BeautifulSoup(opf_data, "xml")
            self.assertEqual(opf_soup.find("dc:title").string, "No Title")
            # 著者名のデフォルト値が「Syosetu Downloader」に変更されたことを検証します
            self.assertEqual(opf_soup.find("dc:creator").string, "Syosetu Downloader")

    def test_epub_horizontal_writing(self):
        """
        style.css において、横書き表示（writing-mode: horizontal-tb）が正しく定義されているかテスト。
        """
        builder = EpubBuilder(self.test_output)
        meta = {"title": "横書きテスト"}
        chapters = [{"title": "第1話", "content": "<p>横書き本文</p>"}]

        result = builder.build_epub(meta, chapters)
        self.assertTrue(result)

        with zipfile.ZipFile(self.test_output, 'r') as z:
            style_data = z.read("OEBPS/style.css").decode("utf-8")
            # writing-mode が horizontal-tb に変更されたことを検証
            self.assertIn("writing-mode: horizontal-tb;", style_data)
            self.assertIn("-webkit-writing-mode: horizontal-tb;", style_data)
            self.assertIn("-epub-writing-mode: horizontal-tb;", style_data)

    def test_epub_with_cover_image(self):
        """
        カレントディレクトリに cover.png が存在する場合に、EPUB内に表紙画像と表紙XHTML、
        およびそれらに対応するOPFマニフェスト、スパイン、NCX、メタデータが正しく追加されるかテスト。
        """
        # テスト開始前にカレントディレクトリにダミーの cover.png を作成
        cover_path = "cover.png"
        dummy_png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

        with open(cover_path, "wb") as f:
            f.write(dummy_png_data)

        try:
            builder = EpubBuilder(self.test_output)
            meta = {"title": "表紙テスト"}
            chapters = [{"title": "第1話", "content": "<p>表紙画像テスト本文</p>"}]

            result = builder.build_epub(meta, chapters)
            self.assertTrue(result)

            with zipfile.ZipFile(self.test_output, 'r') as z:
                namelist = z.namelist()
                # 必要な表紙ファイルがZIPに含まれているか検証
                self.assertIn("OEBPS/cover.png", namelist)
                self.assertIn("OEBPS/cover.xhtml", namelist)

                # cover.png のバイナリデータが一致するか検証
                self.assertEqual(z.read("OEBPS/cover.png"), dummy_png_data)

                # content.opf のメタデータ、マニフェスト、スパインの検証
                opf_data = z.read("OEBPS/content.opf").decode("utf-8")
                opf_soup = BeautifulSoup(opf_data, "xml")

                # EPUB 2 互換用カバーメタデータ
                meta_cover = opf_soup.find("meta", attrs={"name": "cover"})
                self.assertIsNotNone(meta_cover)
                self.assertEqual(meta_cover.get("content"), "cover-image")

                # EPUB 3 カバー画像属性
                cover_item = opf_soup.find("item", id="cover-image")
                self.assertIsNotNone(cover_item)
                self.assertEqual(cover_item.get("properties"), "cover-image")
                self.assertEqual(cover_item.get("href"), "cover.png")

                # 表紙xhtmlアイテム
                cover_xhtml_item = opf_soup.find("item", id="cover")
                self.assertIsNotNone(cover_xhtml_item)
                self.assertEqual(cover_xhtml_item.get("href"), "cover.xhtml")

                # spineの先頭にcoverが含まれているか
                spine = opf_soup.find("spine")
                self.assertIsNotNone(spine)
                itemrefs = spine.find_all("itemref")
                self.assertTrue(len(itemrefs) > 0)
                self.assertEqual(itemrefs[0].get("idref"), "cover")

                # cover.xhtml の検証
                cover_xhtml_data = z.read("OEBPS/cover.xhtml").decode("utf-8")
                self.assertIn('src="cover.png"', cover_xhtml_data)

        finally:
            # テスト終了後にダミーの cover.png を必ず削除
            if os.path.exists(cover_path):
                os.remove(cover_path)

if __name__ == "__main__":
    unittest.main()
