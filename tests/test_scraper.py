# -*- coding: utf-8 -*-
"""
tests/test_scraper.py
SyosetuScraperクラスの動作テスト。

ローカルに保存されているサンプルの目次HTMLおよびエピソードHTMLファイルを読み込み、
SyosetuScraperの解析機能（パーサーロジック）を詳細にテストします。
"""

import os
import unittest
from src.scraper import SyosetuScraper

class TestSyosetuScraper(unittest.TestCase):
    """
    SyosetuScraperの各パーサーメソッドをテストするクラス。
    """

    def setUp(self):
        """
        テスト用スクレイパーインスタンスとサンプルファイルのパスを準備する。
        """
        self.scraper = SyosetuScraper(delay=0.0)
        self.sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample")
        self.toc_path = os.path.join(self.sample_dir, "目次.html")
        self.episode_path = os.path.join(self.sample_dir, "1.html")

    def test_parse_toc_from_local_file(self):
        """
        ローカルの「目次.html」を解析し、小説の基本情報およびエピソード一覧が
        正しくパースできることをテストします。
        """
        # 目次サンプルの読み込み
        with open(self.toc_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        base_url = "https://ncode.syosetu.com/n9636x/"
        parsed = self.scraper._parse_toc(html_content, base_url)

        # 小説基本情報の検証
        self.assertEqual(parsed["title"], "薬屋のひとりごと")
        self.assertEqual(parsed["author"], "日向夏")
        self.assertIn("薬草を取りに出かけたら、後宮の女官狩りに遭いました。", parsed["introduction"])

        # エピソード一覧の検証
        episodes = parsed["episodes"]
        self.assertTrue(len(episodes) > 0)

        # 最初のエピソードのパース内容を確認
        first_ep = episodes[0]
        self.assertEqual(first_ep["no"], 1)
        self.assertEqual(first_ep["title"], "１　猫猫")
        self.assertEqual(first_ep["url"], "https://ncode.syosetu.com/n9636x/1/")

        # 2番目のエピソードのパース内容を確認
        second_ep = episodes[1]
        self.assertEqual(second_ep["no"], 2)
        self.assertEqual(second_ep["title"], "２　二人の妃")
        self.assertEqual(second_ep["url"], "https://ncode.syosetu.com/n9636x/2/")

        # ページネーション（次のページへのURL）の検証
        self.assertEqual(parsed["next_page_url"], "https://ncode.syosetu.com/n9636x/?p=2")

    def test_parse_episode_from_local_file(self):
        """
        ローカルの「1.html」を解析し、サブタイトルおよび本文のHTML（ルビタグを含む）が
        正しく抽出できることをテストします。
        """
        # エピソードサンプルの読み込み
        with open(self.episode_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        parsed = self.scraper._parse_episode(html_content)

        # サブタイトルの検証
        self.assertEqual(parsed["subtitle"], "１　猫猫")

        # 本文データの検証
        body = parsed["body"]
        self.assertIn("（露天の串焼きが食べたいなあ）", body)
        self.assertIn("曇天を見上げて", body)

        # ルビ要素が保持されているかの検証（<ruby> と <rt> の存在確認）
        self.assertIn("<ruby>", body)
        self.assertIn("<rt>マオマオ</rt>", body)
        self.assertIn("<rp>（</rp>", body)

    def test_fetch_toc_stub_fallback(self):
        """
        Nコード補完ロジックのテスト。
        Nコード形式のURL指定が渡された場合に、自動的に標準なろうURLへ補完されることを検証します。
        """
        # 実際にリクエストを送らないように、_get_requestをモック化
        original_get_request = self.scraper._get_request
        try:
            called_urls = []
            def mock_get_request(url):
                called_urls.append(url)
                # 終了条件（次のページなし）を満たす最小限の目次HTMLを返す
                return """
                <h1 class="p-novel__title">テストタイトル</h1>
                <div class="p-novel__author">作者：テスト作者</div>
                <div id="novel_ex">テストあらすじ</div>
                """

            self.scraper._get_request = mock_get_request
            result = self.scraper.fetch_toc("n1234x")

            self.assertEqual(result["title"], "テストタイトル")
            self.assertEqual(result["author"], "テスト作者")
            self.assertEqual(called_urls[0], "https://ncode.syosetu.com/n1234x/")
        finally:
            self.scraper._get_request = original_get_request

    def test_get_request_retry_on_network_failure(self):
        """
        ネットワークエラー（HTTPエラーなど）が発生した際に、
        _get_requestが指定回数リトライを試み、最終的に例外を発生させることをテストします。
        """
        import requests

        # 実際にリクエストが送信されないようにrequests.getをモック化してエラーを発生させる
        original_get = requests.get
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # ネットワークエラーを再現する例外を発生させる
            raise requests.RequestException("Simulated network failure")

        requests.get = mock_get
        # テスト時間を短縮するため、一時的にウェイト設定を0にする
        self.scraper.delay = 0.0

        try:
            # 3回のリトライが失敗した後に例外が発生することを確認
            with self.assertRaises(requests.RequestException):
                # 存在しないダミーURLを指定
                self.scraper._get_request("https://example.com/failed_url")

            # 最大試行回数が3回であることを検証
            self.assertEqual(call_count, 3)
        finally:
            requests.get = original_get

    def test_parse_episode_without_target_classes(self):
        """
        本文を構成するなろう特有のCSSクラス（.js-novel-text、.p-novel__textなど）
        が存在しない場合でも、空文字の本文を返すことでエラーを起こさず適切にハンドリングできるかテストします。
        """
        html_content = """
        <html>
          <body>
            <div class="unknown-class">本文がありません</div>
          </body>
        </html>
        """
        parsed = self.scraper._parse_episode(html_content)
        # サブタイトルと本文が空でもクラッシュしないことを確認
        self.assertEqual(parsed["subtitle"], "")
        self.assertEqual(parsed["body"], "")

if __name__ == "__main__":
    unittest.main()
