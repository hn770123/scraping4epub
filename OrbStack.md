# OrbStack (Mac) での本リポジトリの実行手順

[OrbStack](https://orbstack.dev/) は、macOS 上で非常に高速かつ軽量に動作する Docker Desktop および Linux 仮想マシン（VM）の代替ツールです。

本リポジトリ（syosetu-epub-maker）を OrbStack を使用して Mac 上で動作させるための2通りの方法（**1. Dockerコンテナを使用する方法**、および **2. Linux仮想マシンを使用する方法**）を以下に示します。お好みの方法を選択して実行してください。

---

## 前提条件

1. Mac に OrbStack がインストールされ、起動していること。
2. Git がインストールされていること。
3. ターミナルから本リポジトリをクローンしていること。
   ```bash
   git clone <リポジトリのURL>
   cd syosetu-epub-maker
   ```

---

## 方法 1: Dockerコンテナを使用する（推奨）

OrbStack の Docker エンジンを使用して、Python 環境をコンテナとして起動し、ツールを実行する方法です。Mac のローカル環境を汚さずに実行できます。

### 1.1 Dockerfile の作成（オプション）
プロジェクトのルートディレクトリに、動作確認用の軽量な `Dockerfile` を作成します。
（※リポジトリのファイルを汚したくない場合は、次の「1.2 ワンライナーコマンドで実行する」を参照してください。）

以下のような `Dockerfile` を作成します：
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 依存関係のコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードとサンプルのコピー
COPY src/ ./src/
COPY sample/ ./sample/
COPY main.py .

# コンテナ起動時のデフォルトコマンド
ENTRYPOINT ["python", "main.py"]
```

#### イメージのビルド
```bash
docker build -t syosetu-epub-maker .
```

#### コンテナの実行（ローカルにEPUBファイルを出力）
ホスト側のカレントディレクトリをコンテナ内の `/app/output` などにマウントすることで、生成された EPUB ファイルを Mac のローカルに取り出すことができます。

*例：Nコード `n9636x` の小説をダウンロードして `output.epub` を作成する*
```bash
docker run --rm -v "$(pwd)":/app/output syosetu-epub-maker n9636x /app/output/output.epub
```

*例：ローカルのサンプル目次HTMLから EPUB を作成する*
```bash
docker run --rm -v "$(pwd)":/app/output syosetu-epub-maker sample/目次.html /app/output/my_novel_sample.epub
```

---

### 1.2 ワンライナーコマンドで実行する（Dockerfile不要）
Dockerfile を作成せず、公式の Python イメージをその場で立ち上げて実行することも可能です。

*例：カレントディレクトリをマウントして、コンテナ内でインストールから実行まで行う*
```bash
docker run --rm -it -v "$(pwd)":/app -w /app python:3.12-slim bash -c "
  pip install -r requirements.txt && \
  python main.py sample/目次.html output.epub
"
```
実行完了後、Mac のローカルディレクトリに `output.epub` が生成されます。

---

## 方法 2: Linux仮想マシン（VM）を使用する

OrbStack は、非常に軽量な Linux 仮想マシン（Ubuntu や Debian など）を数秒で起動できます。この VM 内で直接 Python 環境を構築してツールを実行する方法です。

### 2.1 Linuxマシンの作成と起動
ターミナルから以下のコマンドを実行して、新しく `ubuntu` の仮想マシンを作成し、シェルに入ります。

```bash
# Ubuntu 22.04 VM を作成して起動し、ログインする
orb create ubuntu syosetu-env
orb shell syosetu-env
```

### 2.2 仮想マシン内での環境構築
OrbStack の仮想マシン内では、Mac のホームディレクトリ（`~`）が `/mnt/mac` または自動的にシンボリックリンク等で共有されています。
仮想マシン内でリポジトリのあるディレクトリに移動します。

```bash
# リポジトリをクローンしたディレクトリに移動（例：Macのホーム直下にある場合）
cd /mnt/mac/path/to/syosetu-epub-maker

# 必要なパッケージをインストール
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# 仮想環境（venv）の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 2.3 仮想マシン内での実行
構築した環境で、通常通りスクリプトを実行します。

*Nコードから EPUB を生成する*
```bash
python main.py n9636x output.epub
```

*テストを実行する*
```bash
python3 -m pytest
```

仮想マシンのシェルを抜けるには `exit` を実行します。
```bash
exit
```

---

## まとめ

- **手軽にコンテナ化したい場合**: [方法 1] の Dockerコンテナでの実行が最も迅速です。
- **通常の Linux 開発環境と同じようにデバッグや pytest を繰り返し実行したい場合**: [方法 2] の OrbStack Linux マシンを使用すると、非常に高速かつシームレスに動作させることができます。
