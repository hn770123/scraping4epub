# -*- coding: utf-8 -*-
"""
main.py
小説家になろう EPUB作成ツールのエントリーポイント。

このモジュールは、指定されたURL（またはNコード、ローカルの目次HTMLファイル）から
小説の目次情報を取得し、その後、各エピソードを1話ずつ遅延を挟みながら巡回ダウンロードし、
EpubBuilderおよびContentConverterを利用して縦書き対応のEPUB 3電子書籍を自動生成する
コマンドラインインターフェース（CLI）を提供します。
"""

import sys
import os
from src.scraper import SyosetuScraper
from src.converter import ContentConverter
from src.epub_builder import EpubBuilder

def main():
    """
    コマンドライン引数（URL・Nコード・ローカルファイルパス、および任意の出力EPUBパス）を受け取り、
    スクレイピングからXHTML変換、EPUBビルドまでの一連のワークフローを実行するメイン関数。
    """
    print("==================================================")
    print("小説家になろう EPUB作成ツール (Phase 4 CLI)")
    print("==================================================")

    # 1. 引数の数を確認。最低1つの引数（対象URL等）が必要
    if len(sys.argv) < 2:
        print("【使用法】")
        print("  python main.py [対象URL / Nコード / 目次HTMLファイルパス] [出力EPUBパス (省略時は output.epub)]")
        print("\n【実行例】")
        print("  python main.py n9636x")
        print("  python main.py https://ncode.syosetu.com/n9636x/")
        print("  python main.py sample/目次.html my_novel.epub")
        print("==================================================")
        return

    # コマンド引数からターゲットの入力（URL、Nコード、またはローカルファイルパス）を取得
    target_input = sys.argv[1]

    # 出力先EPUBパス。第2引数があればそれを、無ければデフォルト「output.epub」を使用
    output_path = "output.epub"
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]

    print(f"対象入力: {target_input}")
    print(f"出力先   : {output_path}")

    # 2. スクレイピング（目次の取得）
    # リクエスト間のウェイト（秒）を指定（デフォルト1.0秒）
    # ローカルファイルが対象の場合は不要なウェイトを避けるため0秒でも動作可能ですが、
    # 汎用性を考慮して通常の1秒ウェイトを基本としてスクレイパーを初期化
    scraper = SyosetuScraper(delay=1.0)

    # ローカルの目次ファイルを処理する場合は、ウェイトを0秒に設定
    if os.path.exists(target_input):
        scraper.delay = 0.0

    print("\n[STEP 1/3] 目次情報を取得中...")
    try:
        toc = scraper.fetch_toc(target_input)
    except Exception as e:
        print(f"エラー: 目次情報の取得に失敗しました。詳細: {e}")
        sys.exit(1)

    title = toc.get("title") or "No Title"
    author = toc.get("author") or "Unknown Author"
    episodes = toc.get("episodes") or []

    print(f"  作品名: {title}")
    print(f"  作者名: {author}")
    print(f"  総話数: {len(episodes)} 話")

    if not episodes:
        print("エラー: 該当するエピソードが目次から見つかりませんでした。")
        sys.exit(1)

    # 3. 各エピソードの巡回ダウンロード（本文取得）
    print("\n[STEP 2/3] 各エピソードを巡回ダウンロード中...")
    chapters = []

    for idx, ep in enumerate(episodes):
        ep_no = ep["no"]
        ep_title = ep["title"]
        ep_url = ep["url"]

        # 進捗を表示
        print(f"  [{idx + 1}/{len(episodes)}] 第{ep_no}話「{ep_title}」を取得中...", end="", flush=True)

        try:
            # 1話ダウンロード
            episode_data = scraper.fetch_episode(ep_url)

            # 各チャプターのデータを格納
            chapters.append({
                "title": ep_title,
                "content": episode_data["body"]
            })
            print(" [完了]")
        except Exception as e:
            print(f" [失敗]")
            print(f"エラー: 第{ep_no}話の取得中にエラーが発生しました。詳細: {e}")
            # エラー時も途中で諦めず、続行するかユーザーに示すか、今回はバッチ処理として失敗で終了
            sys.exit(1)

    # 4. EPUBのパッケージング・ビルド
    print("\n[STEP 3/3] EPUB電子書籍ファイルを作成中...")
    try:
        builder = EpubBuilder(output_path)
        success = builder.build_epub(toc, chapters)
        if success:
            print(f"\n🎉 正常に処理が完了しました！")
            print(f"作成されたファイル: {os.path.abspath(output_path)}")
        else:
            print("\nエラー: EPUBのビルド中に不明なエラーが発生しました。")
            sys.exit(1)
    except Exception as e:
        print(f"\nエラー: EPUBのビルドに失敗しました。詳細: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
