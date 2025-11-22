# 🎬 Context Cut Pro

**AI動画自動切り抜き＆テロップ編集ツール**

クラウドネイティブなMVPアプリケーション。Streamlit Community Cloudでのデプロイを前提とした設計で、動画の文字起こし、AI検索、カット編集、テロップ合成を一貫して行えるツールです。

---

## 🌟 主な機能

### 1. 動画インジェスト
- **Google Drive**: Google Drive URLから直接動画を取得
- **Web URL**: YouTubeなどのWeb URLから動画をダウンロード（yt-dlp使用）
- **ローカルファイル**: 手元の動画ファイルをアップロード

### 2. AI文字起こし（RAG）
- **Whisper AI**: OpenAI Whisper（baseモデル）による高精度な日本語文字起こし
- **ChromaDB**: ベクトルデータベースによる意味的な検索機能
- **キャッシュ機能**: 一度処理した動画は再処理不要

### 3. 自然言語シーン検索
- 自然言語クエリで動画内の特定シーンを検索
- 意味的な類似度に基づいた検索結果
- 検索結果から直接カット範囲を選択可能

### 4. 精密なカット範囲指定
- 数値入力による秒単位の精密指定
- スライダーによる視覚的な範囲調整
- FFmpegによる高速プレビュー生成（コピーモード）

### 5. 高機能テロップ編集
- **動的フォント管理**: 
  - `./fonts/` ディレクトリ内のフォントを自動検出
  - フォントのアップロード機能（.ttf, .otf）
  - アップロード後、即座に選択可能
- **スタイル設定**:
  - フォントサイズ: 24px ~ 120px
  - 文字色: カラーピッカーによる自由設定
  - 背景: 透明、黒（半透明）、白から選択
  - 位置: 下部中央、上部中央、中央
- **リアルタイムプレビュー**: 設定を確認しながら編集可能

### 6. 動画生成・エクスポート
- FFmpegによる高品質な動画生成
- テロップ合成（drawtext フィルタ）
- MP4形式での出力
- ダウンロードボタンによる簡単エクスポート

---

## 📂 プロジェクト構造

```
context-cut-pro/
├── app.py                  # メインアプリケーション
├── requirements.txt        # Python依存ライブラリ
├── packages.txt            # システム依存パッケージ（ffmpeg）
├── README.md               # このファイル
├── .gitignore              # Git除外設定
├── fonts/                  # フォントディレクトリ
│   └── NotoSansJP-Regular.ttf  # デフォルトフォント
├── temp_videos/            # 一時動画保存ディレクトリ（Git除外）
├── chromadb_data/          # ChromaDBデータ（Git除外）
└── .streamlit/             # Streamlit設定
    └── secrets.toml        # 認証情報（Git除外）
```

---

## 🚀 デプロイ手順

### 前提条件
- GitHubアカウント
- Streamlit Community Cloudアカウント
- Google Cloud Platform（GCP）サービスアカウント（Google Drive連携用）

### 1. リポジトリの準備

```bash
# リポジトリのクローン（またはフォーク）
git clone https://github.com/yourusername/context-cut-pro.git
cd context-cut-pro

# fontsディレクトリが存在することを確認
ls -la fonts/
# NotoSansJP-Regular.ttf があることを確認
```

**重要**: `fonts/` ディレクトリとデフォルトフォント `NotoSansJP-Regular.ttf` をリポジトリに含めてください。

### 2. Google Cloud Platform（GCP）のセットアップ

#### Google Drive API の有効化
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（または既存プロジェクトを選択）
3. 「APIとサービス」→「ライブラリ」→「Google Drive API」を検索して有効化

#### サービスアカウントの作成
1. 「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「サービスアカウント」
3. サービスアカウント名を入力（例: `context-cut-pro`）
4. 役割: 「閲覧者」を選択
5. 「完了」をクリック

#### 認証キーの取得
1. 作成したサービスアカウントをクリック
2. 「キー」タブ → 「鍵を追加」→「新しい鍵を作成」
3. キーのタイプ: **JSON** を選択
4. JSONファイルがダウンロードされます（例: `your-project-12345-abcdef.json`）

#### Google Driveでの共有設定
Google Driveから動画を取得する場合、サービスアカウントのメールアドレス（`xxx@xxx.iam.gserviceaccount.com`）に対して、対象の動画ファイルまたはフォルダの共有設定を行ってください。

### 3. Streamlit Community Cloud へのデプロイ

#### リポジトリをGitHubにプッシュ
```bash
git add .
git commit -m "Initial commit: Context Cut Pro"
git push origin main
```

#### Streamlit Community Cloudでアプリを作成
1. [Streamlit Community Cloud](https://streamlit.io/cloud) にアクセス
2. 「New app」をクリック
3. リポジトリ、ブランチ、メインファイル（`app.py`）を選択
4. 「Deploy!」をクリック

#### Secretsの設定
1. デプロイしたアプリの「Settings」→「Secrets」に移動
2. 以下の形式でGCPサービスアカウントのJSONキーを貼り付け:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
```

**注意**: 
- `private_key` の改行は `\n` でエスケープしてください
- ダウンロードしたJSONファイルの内容をそのまま使用できます

3. 「Save」をクリック

### 4. アプリの起動確認
- デプロイ完了後、自動的にアプリが起動します
- 初回起動時、デフォルトフォント（Noto Sans JP）が自動ダウンロードされます
- エラーがなければ、アプリが正常に動作します

---

## 🛠️ ローカル開発

### 環境構築

```bash
# Python 3.9以上を推奨
python --version

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate

# 依存ライブラリのインストール
pip install -r requirements.txt

# FFmpegのインストール（システムレベル）
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

### Secretsファイルの作成

`.streamlit/secrets.toml` を作成し、GCPサービスアカウントの情報を設定:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
Your-Private-Key-Here
-----END PRIVATE KEY-----
"""
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
```

### アプリの起動

```bash
streamlit run app.py
```

ブラウザが自動的に開き、`http://localhost:8501` でアプリにアクセスできます。

---

## 📖 使い方

### 1. 動画の取得
1. サイドバーから動画ソースを選択（Google Drive、Web URL、ローカルファイル）
2. URLを入力するか、ファイルをアップロード
3. 「ダウンロード」または「アップロード」を実行

### 2. 文字起こし
1. サイドバーの「AI文字起こし」セクション
2. 「文字起こしを実行」ボタンをクリック
3. 処理完了まで数分待つ（動画の長さに依存）

### 3. シーン検索
1. 「🔍 シーン検索」タブに移動
2. 検索クエリを入力（例: "面白いシーン"）
3. 「検索実行」をクリック
4. 結果から目的のシーンを選択

### 4. カット範囲指定
1. 「✂️ カット範囲指定」タブに移動
2. 開始時間と終了時間を数値入力またはスライダーで調整
3. 「プレビューを生成」でカット結果を確認

### 5. テロップ編集
1. 「💬 テロップ編集」タブに移動
2. テロップテキストを入力
3. フォント、サイズ、色、背景を設定
4. 必要に応じて新しいフォントをアップロード
5. 「🎬 テロップ付き動画を生成」をクリック
6. 生成完了後、「📥 動画をダウンロード」でエクスポート

---

## 🎨 フォント管理

### デフォルトフォント
- **Noto Sans JP Regular**: 日本語対応の高品質フォント
- リポジトリに `fonts/NotoSansJP-Regular.ttf` として同梱

### カスタムフォントの追加

#### 方法1: リポジトリに追加（推奨）
```bash
# フォントファイルをfontsディレクトリにコピー
cp /path/to/your/font.ttf fonts/

# Gitにコミット
git add fonts/your-font.ttf
git commit -m "Add custom font"
git push
```

#### 方法2: アプリ内でアップロード
1. 「💬 テロップ編集」タブ
2. 「新しいフォントを追加」セクション
3. フォントファイル（.ttf, .otf）をアップロード
4. 「フォントを追加」をクリック
5. 自動的に選択肢に追加されます

**注意**: アプリ内アップロードはStreamlit Cloudの場合、再デプロイ時にリセットされます。恒久的に使用する場合は、方法1を推奨します。

---

## 🔧 技術スタック

| 分類 | 技術 |
|------|------|
| **UI** | Streamlit |
| **動画取得** | google-api-python-client, yt-dlp |
| **AI処理** | OpenAI Whisper (base), LangChain, ChromaDB |
| **動画加工** | ffmpeg-python |
| **システム** | FFmpeg (packages.txt) |
| **インフラ** | Streamlit Community Cloud |

---

## 🐛 トラブルシューティング

### Q: "Google Cloud認証情報が設定されていません" と表示される
**A**: Streamlit CloudのSecretsに `gcp_service_account` が正しく設定されているか確認してください。

### Q: フォントが表示されない
**A**: 
1. `fonts/` ディレクトリに `.ttf` または `.otf` ファイルが存在するか確認
2. ファイル名に日本語や特殊文字が含まれていないか確認
3. アプリを再起動してみる

### Q: FFmpegエラーが発生する
**A**: 
1. `packages.txt` に `ffmpeg` が記載されているか確認
2. Streamlit Cloudの場合、自動的にインストールされます
3. ローカルの場合、システムに FFmpeg がインストールされているか確認

### Q: Whisperの文字起こしが遅い
**A**: 
- Streamlit Community Cloud の無料プランはCPUのみです
- 長時間の動画は処理に時間がかかります（10分動画で5-10分程度）
- 必要に応じて動画を短くカットしてからアップロードしてください

### Q: メモリエラーが発生する
**A**: 
- Streamlit Community Cloud の無料プランはメモリ制限があります
- 大容量の動画（1GB以上）は処理できない場合があります
- 動画を圧縮してからアップロードしてください

---

## 📝 ライセンス

MIT License

---

## 🤝 コントリビューション

プルリクエストを歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを作成

---

## 📧 お問い合わせ

問題や質問がある場合は、GitHubのIssuesでお知らせください。

---

## 🙏 謝辞

- [OpenAI Whisper](https://github.com/openai/whisper) - 高精度な音声認識
- [Streamlit](https://streamlit.io/) - 素晴らしいUIフレームワーク
- [ChromaDB](https://www.trychroma.com/) - ベクトルデータベース
- [FFmpeg](https://ffmpeg.org/) - 動画処理の標準ツール
- [Noto Sans JP](https://fonts.google.com/noto/specimen/Noto+Sans+JP) - 日本語フォント

---

**Enjoy creating amazing video clips with Context Cut Pro! 🎬**
