# -*- coding: utf-8 -*-
"""
src/epub_builder.py
XHTMLや各種メタデータファイルをZIPアーカイブとしてEPUB形式にパッケージングするモジュール。

このモジュールは、EPUB 3の仕様に基づき、mimetype、container.xml、content.opf、
およびナビゲーション文書（nav.xhtml、toc.ncx）を適切に自動生成し、
縦書き対応スタイルシート（style.css）とともにZIP圧縮して「.epub」ファイルをビルドします。
"""

import os
import zipfile
import uuid
import datetime
from src.converter import ContentConverter

class EpubBuilder:
    """
    EPUB構造体（mimetype、container.xml、content.opf、XHTMLコンテンツなど）を構築し、
    仕様に準拠したZIP形式のEPUBファイルをビルドするクラス。
    """

    def __init__(self, output_path):
        """
        ビルダーの初期化。

        Parameters:
            output_path (str): 出力するEPUBファイルのパス
        """
        self.output_path = output_path

    def build_epub(self, meta_info, chapters):
        """
        メタ情報と各エピソードのXHTMLをもとにEPUBファイルを生成する。

        Parameters:
            meta_info (dict): タイトル、作者、識別子、前書きなどのメタデータ
            chapters (list): 各章/エピソードのタイトルとXHTMLコンテンツのリスト
                             ※リスト内要素はdict（{"title": "...", "content": "..."}）
                             または tuple/list（(title, content)）のいずれにも対応します。

        Returns:
            bool: 成功した場合はTrue
        """
        # メタデータの抽出と補完
        title = meta_info.get("title") or "No Title"
        # 1. 必須メタデータである「著者名（Author）」を明示的に追加する。
        # デフォルトの著者名として「Syosetu Downloader」を必ず設定します。
        author = meta_info.get("author") or "Syosetu Downloader"
        introduction = meta_info.get("introduction") or ""

        # EPUB識別用のUUIDおよび更新時刻の生成
        unique_id = meta_info.get("id") or str(uuid.uuid4())
        # Python 3.12 以降の非推奨警告（utcnow()）を防ぐため、timezone-awareな表現にする
        try:
            modified_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        except AttributeError:
            modified_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        # コンバーターのインスタンス化
        converter = ContentConverter()

        # チャプター（エピソード）情報の標準化
        processed_chapters = []
        for idx, item in enumerate(chapters):
            if isinstance(item, dict):
                c_title = item.get("title") or item.get("subtitle") or f"第{idx+1}話"
                c_content = item.get("content") or item.get("xhtml") or item.get("body") or ""
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                c_title = item[0]
                c_content = item[1]
            else:
                c_title = f"第{idx+1}話"
                c_content = str(item)
            processed_chapters.append({
                "no": idx + 1,
                "title": c_title,
                "content": c_content
            })

        # 各ファイル用データの構築
        manifest_items = []
        spine_items = []
        nav_items = []
        ncx_items = []
        chapter_files = {}

        play_order = 1
        # nav.xhtml (目次) 自体のplayOrder（EPUB2互換用NCX用）
        play_order += 1

        # 1. 前書き（あらすじ）ページがある場合は作成する
        if introduction:
            # 改行を段落タグで囲う
            intro_paragraphs = "".join(f"<p>{line.strip()}</p>" for line in introduction.split("\n") if line.strip())
            intro_xhtml = converter.convert_to_xhtml("前書き", intro_paragraphs)
            chapter_files["OEBPS/introduction.xhtml"] = intro_xhtml

            manifest_items.append('<item id="introduction" href="introduction.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.append('<itemref idref="introduction"/>')
            nav_items.append('<li><a href="introduction.xhtml">前書き</a></li>')
            ncx_items.append(f"""    <navPoint id="nav-intro" playOrder="{play_order}">
      <navLabel><text>前書き</text></navLabel>
      <content src="introduction.xhtml"/>
    </navPoint>""")
            play_order += 1

        # 2. 各エピソードのXHTMLファイル作成
        for ch in processed_chapters:
            no = ch["no"]
            c_title = ch["title"]
            c_content = ch["content"]

            # すでに完全なXML/XHTML構成でなければ、自動的に補正・ラップする
            if not (c_content.strip().startswith("<?xml") or "<html" in c_content):
                cleaned_body = converter.clean_html(c_content)
                xhtml_content = converter.convert_to_xhtml(c_title, cleaned_body)
            else:
                xhtml_content = c_content

            filename = f"chapter_{no}.xhtml"
            chapter_files[f"OEBPS/{filename}"] = xhtml_content

            manifest_items.append(f'<item id="chapter_{no}" href="{filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="chapter_{no}"/>')
            nav_items.append(f'<li><a href="{filename}">{c_title}</a></li>')
            ncx_items.append(f"""    <navPoint id="nav-chapter_{no}" playOrder="{play_order}">
      <navLabel><text>{c_title}</text></navLabel>
      <content src="{filename}"/>
    </navPoint>""")
            play_order += 1

        # マニフェストとスパイン文字列の生成
        manifest_str = "\n    ".join(manifest_items)
        spine_str = "\n    ".join(spine_items)
        nav_items_str = "\n            ".join(nav_items)
        ncx_items_str = "\n".join(ncx_items)

        # 3. EPUBに必要なメタデータファイルの生成

        # META-INF/container.xml の生成
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

        # OEBPS/style.css (縦書き用スタイルシート) の生成
        style_css = """@charset "utf-8";

/* 日本語の縦書き表示設定 */
html {
    writing-mode: vertical-rl;
    -webkit-writing-mode: vertical-rl;
    -epub-writing-mode: vertical-rl;
}

body {
    font-family: "Hiragino Mincho ProN", "YuMincho", "MS Mincho", serif;
    margin: 5%;
    line-height: 1.8;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", "MS Gothic", sans-serif;
    margin-left: 1.5em;
    margin-right: 0.5em;
}

p {
    margin: 0;
    text-indent: 1em;
}

ruby rt {
    font-size: 0.5em;
}
"""

        # OEBPS/content.opf (パッケージドキュメント) の生成
        # 2. Kindleでエラー原因になりやすい「空のナビゲーション（Nav）」の出力を綺麗に整えるため、
        # spineに 'nav' を入れず、最後に add_item(epub.EpubNav()) もしないという修正の方向性に則り、
        # spine内の <itemref idref="nav"/> を削除します。
        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id" version="3.0" xml:lang="ja">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:{unique_id}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator id="creator">{author}</dc:creator>
    <dc:language>ja</dc:language>
    <meta property="dcterms:modified">{modified_time}</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="style" href="style.css" media-type="text/css"/>
    {manifest_str}
  </manifest>
  <spine toc="toc">
    {spine_str}
  </spine>
</package>"""

        # OEBPS/nav.xhtml (EPUB 3 ナビゲーション文書) の生成
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2011/epub" xml:lang="ja" lang="ja">
<head>
    <meta charset="utf-8" />
    <title>目次</title>
    <link rel="stylesheet" type="text/css" href="style.css" />
</head>
<body class="vertical-text">
    <nav epub:type="toc" id="toc">
        <h1>目次</h1>
        <ol>
            <li><a href="nav.xhtml">目次</a></li>
            {nav_items_str}
        </ol>
    </nav>
</body>
</html>"""

        # OEBPS/toc.ncx (EPUB 2 互換用目次) の生成
        toc_ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{unique_id}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>{title}</text>
  </docTitle>
  <navMap>
    <navPoint id="nav-nav" playOrder="1">
      <navLabel><text>目次</text></navLabel>
      <content src="nav.xhtml"/>
    </navPoint>
    {ncx_items_str}
  </navMap>
</ncx>"""

        # 4. ZIPアーカイブ(EPUB)としてのパッケージング
        # mimetypeファイルは非圧縮かつアーカイブの先頭に確実に配置する必要がある。
        with zipfile.ZipFile(self.output_path, 'w') as z:
            # mimetypeを追加 (非圧縮)
            z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # メタデータおよび共通ファイルを追加
            z.writestr("META-INF/container.xml", container_xml, compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("OEBPS/style.css", style_css, compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("OEBPS/content.opf", content_opf, compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("OEBPS/nav.xhtml", nav_xhtml, compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("OEBPS/toc.ncx", toc_ncx, compress_type=zipfile.ZIP_DEFLATED)

            # 動的チャプターおよび前書きを追加
            for path, content in chapter_files.items():
                z.writestr(path, content, compress_type=zipfile.ZIP_DEFLATED)

        return True
