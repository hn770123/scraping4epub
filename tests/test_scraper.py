# -*- coding: utf-8 -*-
"""
tests/test_scraper.py
SyosetuScraperクラスのテスト。
"""

import unittest
from src.scraper import SyosetuScraper

class TestSyosetuScraper(unittest.TestCase):
    """
    スクレイパーの動作確認テスト。
    """

    def setUp(self):
        self.scraper = SyosetuScraper(delay=0.1)

    def test_fetch_toc(self):
        """
        目次取得スタブのテスト。
        """
        toc = self.scraper.fetch_toc("https://ncode.syosetu.com/n9636x/")
        self.assertEqual(toc["title"], "薬屋のひとりごと")
        self.assertEqual(toc["author"], "日向夏")
        self.assertTrue(len(toc["episodes"]) > 0)

    def test_fetch_episode(self):
        """
        エピソード取得スタブのテスト。
        """
        episode = self.scraper.fetch_episode("https://ncode.syosetu.com/n9636x/1/")
        self.assertEqual(episode["subtitle"], "１　猫猫")
        self.assertIn("マオマオ", episode["body"])

if __name__ == "__main__":
    unittest.main()
