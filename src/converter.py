# -*- coding: utf-8 -*-
"""
src/converter.py
スクレイピングした中間データをXHTMLおよびEPUB用フォーマットに整形・変換するモジュール。

このモジュールは、小説家になろうから取得したHTMLデータのクレンジング（不要なスクリプトや広告の排除）、
およびEPUB 3の仕様に準拠した厳格なXML/XHTMLフォーマットへの変換を担当します。
"""

from bs4 import BeautifulSoup

class ContentConverter:
    """
    中間データを読み込み、縦書き表示などに最適化されたHTML/XHTMLへと整形・変換するクラス。
    """

    def clean_html(self, raw_html):
        """
        不要なタグ（スクリプト、広告、スタイルなど）を除去し、必要なルビ等を保持した状態でクレンジングする。

        Parameters:
            raw_html (str): スクレイピングした生のHTML文字列

        Returns:
            str: 整形・クレンジング後のHTML文字列
        """
        if not raw_html:
            return ""

        # BeautifulSoupを用いてHTMLをパース
        soup = BeautifulSoup(raw_html, "lxml")

        # 削除対象の不要タグを定義
        unwanted_tags = [
            "script", "style", "iframe", "noscript",
            "input", "button", "form", "select", "textarea", "link"
        ]
        for tag_name in unwanted_tags:
            for tag in soup.find_all(tag_name):
                tag.extract()

        # 各要素から不要なイベントハンドラ属性や、不要な属性を削除してクリーンにする
        # ルビタグや段落のid属性（なろうの行数を示すL1, L2など）は保持する
        allowed_attrs = {"class", "id", "href"}
        for tag in soup.find_all(True):
            attrs = list(tag.attrs.keys())
            for attr in attrs:
                # 許可された属性以外を削除、またはイベントハンドラ（onで始まる）を削除
                if attr not in allowed_attrs or attr.startswith("on"):
                    del tag[attr]

        # BeautifulSoupのbody要素がある場合は、その子要素の文字列表現を結合する
        if soup.body:
            # bodyタグそのものを除外し、中身だけをプレーンなHTMLフラグメントとして抽出
            return "".join(str(child) for child in soup.body.children)

        return str(soup)

    def convert_to_xhtml(self, title, body_content):
        """
        コンテンツをEPUB用の標準的なXHTML 1.1 / EPUB 3 XHTML構造に変換する。
        EPUB 3仕様に準拠するため、XMLパーサーを利用して閉じタグの不整合などを厳密に補正します。

        Parameters:
            title (str): ページのタイトル（サブタイトル）
            body_content (str): 本文のHTMLフラグメント（クレンジング済み）

        Returns:
            str: EPUB3準拠の厳格なXHTMLフォーマットの文字列
        """
        # xml宣言とxhtml5スケルトン
        # 縦書き用スタイルシート「style.css」を参照する
        xhtml_template = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ja" lang="ja">
<head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body class="vertical-text">
    <section class="chapter">
        <h1 class="chapter-title">{title}</h1>
        <div class="chapter-content">
            {body_content}
        </div>
    </section>
</body>
</html>"""

        # XMLパーサー（lxmlのxmlパーサー、または標準xml）を通して、XHTMLとしての妥当性を確保
        # 属性のクォーテーションや自己完結タグ（<br /> など）を厳密に整形する
        soup = BeautifulSoup(xhtml_template, "xml")
        return str(soup)
