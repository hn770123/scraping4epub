# -*- coding: utf-8 -*-
"""
src/scraper.py
小説家になろうのWeb小説をスクレイピングするモジュール。

このモジュールは、指定された小説の目次（TOC）情報、
および各エピソードの本文（ルビ付）をスクレイピングして取得します。
"""

import time
import urllib.parse
import requests
from bs4 import BeautifulSoup

class SyosetuScraper:
    """
    小説家になろう（syosetu.com）から小説の目次情報や
    各エピソードの本文データを取得・抽出するスクレイパークラス。
    """

    def __init__(self, delay=1.0):
        """
        スクレイパーオブジェクトを初期化する。

        Parameters:
            delay (float): 各リクエストの送信前に挿入するウェイト（秒）。サーバー負荷軽減用。
        """
        self.delay = delay

    def _get_request(self, url):
        """
        HTTP GETリクエストを送信し、ページのHTMLソースを取得するヘルパーメソッド。
        ネットワークエラー時のリトライハンドリングと、User-Agentの設定、ウェイト制御を行います。

        Parameters:
            url (str): リクエスト対象のURL

        Returns:
            str: 取得したHTMLコンテンツ（UTF-8デコード済み）
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        max_retries = 3
        retry_delay = 2.0

        # サーバ負荷軽減のためのウェイト挿入
        if self.delay > 0:
            time.sleep(self.delay)

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                # 文字コードをUTF-8に明示的に設定
                response.encoding = "utf-8"
                return response.text
            except (requests.RequestException, Exception) as e:
                # 最終リトライが失敗した場合は、例外を発生させる
                if attempt == max_retries - 1:
                    raise e
                # 指数バックオフ（または徐々にウェイトを長くする）でリトライを待機
                time.sleep(retry_delay * (attempt + 1))

    def _parse_toc(self, html_content, base_url):
        """
        取得した目次ページのHTMLを解析し、小説情報を抽出する。
        テストが容易に行えるよう、HTTPリクエストとパース処理を分離しています。

        Parameters:
            html_content (str): 目次ページのHTMLソース
            base_url (str): 相対パスを絶対URLに変換するためのベースURL

        Returns:
            dict: 抽出された情報（タイトル、作者、あらすじ、エピソード一覧、次ページURL）
        """
        soup = BeautifulSoup(html_content, "lxml")

        # 小説タイトルの抽出（.p-novel__title または og:title から）
        title_el = soup.find(class_="p-novel__title")
        title = title_el.get_text(strip=True) if title_el else ""

        # 作者名の抽出（.p-novel__author から「作者：」を除去）
        author_el = soup.find(class_="p-novel__author")
        author = ""
        if author_el:
            text = author_el.get_text(strip=True)
            if "作者：" in text:
                author = text.split("作者：", 1)[1].strip()
            elif "作者:" in text:
                author = text.split("作者:", 1)[1].strip()
            else:
                author = text

        # 前書き・あらすじの抽出（#novel_ex または .p-novel__summary）
        intro_el = soup.find(id="novel_ex") or soup.find(class_="p-novel__summary")
        introduction = intro_el.get_text(strip=True) if intro_el else ""

        # 各エピソード情報の抽出（.p-eplist 内の .p-eplist__sublist）
        episodes = []
        sublists = soup.find_all(class_="p-eplist__sublist")
        for i, sub in enumerate(sublists):
            a_tag = sub.find("a", class_="p-eplist__subtitle")
            if a_tag:
                href = a_tag.get("href", "")
                full_url = urllib.parse.urljoin(base_url, href) if href else ""
                subtitle = a_tag.get_text(strip=True)

                # URLから話数（no）を抽出する試み、失敗した場合はシーケンシャルな番号を付与
                ep_no = None
                if href:
                    parts = [p for p in href.split("/") if p]
                    if parts and parts[-1].isdigit():
                        ep_no = int(parts[-1])
                if ep_no is None:
                    ep_no = i + 1

                episodes.append({
                    "no": ep_no,
                    "title": subtitle,
                    "url": full_url
                })

        # 複数ページにまたがる目次の「次へ」リンクの解析
        next_el = soup.find("a", class_="c-pager__item--next")
        next_page_url = None
        if next_el:
            next_href = next_el.get("href")
            if next_href:
                next_page_url = urllib.parse.urljoin(base_url, next_href)

        return {
            "title": title,
            "author": author,
            "introduction": introduction,
            "episodes": episodes,
            "next_page_url": next_page_url
        }

    def _parse_episode(self, html_content):
        """
        取得したエピソードページのHTMLを解析し、サブタイトルと本文（ルビを含む）を抽出する。

        Parameters:
            html_content (str): エピソードページのHTMLソース

        Returns:
            dict: サブタイトルと本文のHTMLデータ
        """
        soup = BeautifulSoup(html_content, "lxml")

        # サブタイトル（話名）の抽出（.p-novel__title または .p-novel__title--rensai）
        sub_el = soup.find(class_="p-novel__title")
        subtitle = sub_el.get_text(strip=True) if sub_el else ""

        # 本文データの抽出（.js-novel-text もしくは .p-novel__body 内の段落）
        body_el = soup.find(class_="js-novel-text") or soup.find(class_="p-novel__text")
        paragraphs = []
        if body_el:
            for p in body_el.find_all("p"):
                # <ruby>, <rt>, <rp> 等を保持するため、段落ごとHTML文字列として抽出
                paragraphs.append(str(p))
        body_html = "\n".join(paragraphs)

        return {
            "subtitle": subtitle,
            "body": body_html
        }

    def fetch_toc(self, url):
        """
        指定された小説の目次ページを取得し、小説情報とエピソード一覧を抽出する。
        複数ページにまたがる目次（ページネーション）にも自動で追従します。

        Parameters:
            url (str): 目次ページのURLまたはNコード（例：n9636x）

        Returns:
            dict: 抽出されたタイトル、作者名、前書き、エピソード一覧などの情報
        """
        # URLの正規化処理（Nコード単体が渡された場合、標準のなろうURLに補完）
        if not url.startswith("http://") and not url.startswith("https://"):
            ncode = url.lower().strip()
            ncode = ncode.replace("/", "")
            target_url = f"https://ncode.syosetu.com/{ncode}/"
        else:
            target_url = url

        current_url = target_url
        all_episodes = []
        title = None
        author = None
        introduction = None

        # ページネーションをすべて辿るループ
        while current_url:
            html_content = self._get_request(current_url)
            parsed = self._parse_toc(html_content, current_url)

            # 初回ページのみ基本小説情報を登録
            if title is None:
                title = parsed["title"]
            if author is None:
                author = parsed["author"]
            if introduction is None:
                introduction = parsed["introduction"]

            all_episodes.extend(parsed["episodes"])

            # 次ページURLがあればループを継続、なければ終了
            current_url = parsed["next_page_url"]

        # エピソード番号を昇順（1始まり）で再割り当て
        for i, ep in enumerate(all_episodes):
            ep["no"] = i + 1

        return {
            "title": title,
            "author": author,
            "introduction": introduction,
            "episodes": all_episodes
        }

    def fetch_episode(self, url):
        """
        指定されたエピソードページを取得し、サブタイトルと本文（ルビを含む）を抽出する。

        Parameters:
            url (str): エピソードページの絶対URL

        Returns:
            dict: サブタイトルと本文データ（HTML形式）
        """
        html_content = self._get_request(url)
        return self._parse_episode(html_content)
