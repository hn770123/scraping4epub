# -*- coding: utf-8 -*-
"""
main.py
小説家になろう EPUB作成ツールのエントリーポイント。
"""

import sys
from src.scraper import SyosetuScraper
from src.converter import ContentConverter
from src.epub_builder import EpubBuilder

def main():
    """
    コマンドラインからURL等を受け取り、スクレイピングからEPUB変換、ビルドまでを一貫して実行するメイン関数。
    """
    print("小説家になろう EPUB作成ツールを起動しています...")
    if len(sys.argv) < 2:
        print("使用法: python main.py [小説家になろうURL]")
        return

    target_url = sys.argv[1]
    print(f"対象URL: {target_url}")

    # 1. スクレイピング
    scraper = SyosetuScraper()
    print("目次を読込中...")
    toc = scraper.fetch_toc(target_url)
    print(f"作品名: {toc['title']} (作者: {toc['author']})")

    # 2. 変換・ビルドのシミュレーション（フェーズ1）
    print("中間データ変換およびEPUBファイルの作成を行います（ダミー）...")
    builder = EpubBuilder("output.epub")
    builder.build_epub(toc, [])
    print("処理完了しました。")

if __name__ == "__main__":
    main()
