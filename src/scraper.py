# -*- coding: utf-8 -*-
"""
src/scraper.py
小説家になろうのWeb小説をスクレイピングするモジュール。
"""

import time
import requests
from bs4 import BeautifulSoup

class SyosetuScraper:
    """
    小説家になろうから目次情報や各エピソード本文を取得するスクレイパークラス。
    """

    def __init__(self, delay=1.0):
        """
        スクレイパーの初期化。

        Parameters:
            delay (float): リクエスト間のウェイト（秒）
        """
        self.delay = delay

    def fetch_toc(self, url):
        """
        指定された小説の目次ページを取得し、小説情報とエピソード一覧を抽出する。

        Parameters:
            url (str): 目次ページのURLまたはNコード

        Returns:
            dict: 抽出されたタイトル、作者名、前書き、エピソード一覧などの情報
        """
        # フェーズ1用のスタブ実装
        time.sleep(self.delay)
        return {
            "title": "薬屋のひとりごと",
            "author": "日向夏",
            "introduction": "薬草を取りに出かけたら、後宮の女官狩りに遭いました。",
            "episodes": [
                {"no": 1, "title": "１　猫猫", "url": "https://ncode.syosetu.com/n9636x/1/"}
            ]
        }

    def fetch_episode(self, url):
        """
        指定されたエピソードページを取得し、サブタイトルと本文（ルビを含む）を抽出する。

        Parameters:
            url (str): エピソードページのURL

        Returns:
            dict: サブタイトルと本文データ
        """
        # フェーズ1用のスタブ実装
        time.sleep(self.delay)
        return {
            "subtitle": "１　猫猫",
            "body": "<p>曇天を見上げて<ruby>猫猫<rp>（</rp><rt>マオマオ</rt><rp>）</rp></ruby>は溜息をついた。</p>"
        }
