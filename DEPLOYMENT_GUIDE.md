# 🚀 Context Cut Pro - デプロイメントガイド

## 📋 クイックスタート

このガイドは、Context Cut Pro を Streamlit Community Cloud にデプロイするための完全な手順を提供します。

---

## ✅ デプロイ前チェックリスト

### 必須項目
- [ ] GitHubアカウント
- [ ] Streamlit Community Cloud アカウント（無料）
- [ ] Google Cloud Platform プロジェクト（Google Drive連携用）
- [ ] GCPサービスアカウントのJSONキー

### オプション項目
- [ ] カスタムフォントファイル（.ttf, .otf）
- [ ] テスト用動画ファイル

---

## 🔧 Step 1: Google Cloud Platform セットアップ

### 1.1 GCPプロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成:
   - プロジェクト名: `context-cut-pro` (任意)
   - 組織: なし（個人利用の場合）
3. プロジェクトを選択

### 1.2 Google Drive API の有効化

1. 左メニュー → 「APIとサービス」 → 「ライブラリ」
2. 検索ボックスに `Google Drive API` と入力
3. 「Google Drive API」を選択
4. 「有効にする」をクリック

### 1.3 サービスアカウントの作成

1. 左メニュー → 「APIとサービス」 → 「認証情報」
2. 「認証情報を作成」 → 「サービスアカウント」を選択
3. サービスアカウントの詳細:
   - 名前: `context-cut-pro-service` (任意)
   - ID: 自動生成される
   - 説明: `Context Cut Pro video processing service` (任意)
4. 「作成して続行」をクリック
5. 役割の選択:
   - **役割**: `閲覧者` (Viewer) を選択
   - ※ Google Driveの読み取り専用アクセスのみ
6. 「完了」をクリック

### 1.4 サービスアカウントキーの取得

1. 作成したサービスアカウントをクリック
2. 上部の「キー」タブを選択
3. 「鍵を追加」 → 「新しい鍵を作成」
4. キーのタイプ: **JSON** を選択
5. 「作成」をクリック
6. JSONファイルがダウンロードされます
   - ファイル名例: `context-cut-pro-12345-abcdef.json`
   - **重要**: このファイルを安全な場所に保管してください

### 1.5 Google Drive 共有設定

Google Driveから動画を取得する場合:

1. サービスアカウントのメールアドレスをコピー
   - 形式: `xxx@xxx.iam.gserviceaccount.com`
2. Google Driveで動画ファイルまたはフォルダを右クリック
3. 「共有」を選択
4. サービスアカウントのメールアドレスを追加
5. 権限: 「閲覧者」を選択
6. 「送信」をクリック

---

## 📦 Step 2: GitHubリポジトリのセットアップ

### 2.1 リポジトリの作成

1. [GitHub](https://github.com/) にログイン
2. 右上の「+」→ 「New repository」
3. リポジトリ設定:
   - **名前**: `context-cut-pro` (任意)
   - **説明**: `AI-powered video clipping and subtitle editor`
   - **公開設定**: Public（推奨）または Private
   - **Initialize**: チェックなし（既存コードをプッシュするため）
4. 「Create repository」をクリック

### 2.2 ローカルリポジトリとの接続

```bash
# リポジトリのリモート追加
cd /home/user/webapp
git remote add origin https://github.com/yourusername/context-cut-pro.git

# メインブランチの名前確認（main または master）
git branch

# GitHubにプッシュ
git push -u origin main
```

### 2.3 プッシュ確認

ブラウザでGitHubリポジトリを開き、以下のファイルが存在することを確認:

- ✅ `app.py`
- ✅ `requirements.txt`
- ✅ `packages.txt`
- ✅ `README.md`
- ✅ `.gitignore`
- ✅ `fonts/NotoSansJP-Regular.ttf`
- ✅ `.streamlit/config.toml`
- ✅ `.streamlit/secrets.toml.example`

---

## ☁️ Step 3: Streamlit Community Cloud デプロイ

### 3.1 Streamlit Cloud にログイン

1. [Streamlit Community Cloud](https://streamlit.io/cloud) にアクセス
2. 「Sign up」または「Log in」
3. GitHubアカウントで認証

### 3.2 新しいアプリの作成

1. 「New app」ボタンをクリック
2. アプリ設定:
   - **Repository**: `yourusername/context-cut-pro` を選択
   - **Branch**: `main` を選択
   - **Main file path**: `app.py` を入力
   - **App URL**: カスタムURLを設定（任意）
     - 例: `context-cut-pro` → `https://context-cut-pro.streamlit.app`
3. 「Deploy!」をクリック

### 3.3 デプロイ進行状況の確認

- 画面下部にログが表示されます
- 以下の順序で処理が進みます:
  1. ✅ リポジトリのクローン
  2. ✅ `packages.txt` からシステムパッケージのインストール（ffmpeg）
  3. ✅ `requirements.txt` からPythonライブラリのインストール
  4. ✅ アプリの起動

⏱️ **初回デプロイ時間**: 約5〜10分（依存関係のインストール含む）

---

## 🔐 Step 4: Secrets の設定

### 4.1 Secrets エディタを開く

1. デプロイしたアプリの画面右上 → 「Settings」（歯車アイコン）
2. 左メニュー → 「Secrets」

### 4.2 GCP サービスアカウントキーの貼り付け

#### 方法1: JSONファイルからコピー（推奨）

1. ダウンロードしたJSONファイルを開く
2. 以下のような内容が含まれています:

```json
{
  "type": "service_account",
  "project_id": "your-project-123456",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
  "client_email": "context-cut-pro@your-project.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

3. Streamlit Cloud の Secrets エディタに以下の形式で貼り付け:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-123456"
private_key_id = "abc123..."
private_key = "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"
client_email = "context-cut-pro@your-project.iam.gserviceaccount.com"
client_id = "123456789..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

#### 方法2: テンプレートから作成

1. リポジトリの `.streamlit/secrets.toml.example` を参照
2. 実際の値に置き換えて貼り付け

### 4.3 注意事項

⚠️ **重要**:
- `private_key` の改行は `\n` でエスケープされている必要があります
- JSON形式ではなく、TOML形式で記述してください
- ダブルクォートは不要です（TOMLの仕様）

### 4.4 Secrets の保存

1. すべての値を入力後、「Save」ボタンをクリック
2. アプリが自動的に再起動されます

---

## ✅ Step 5: デプロイ確認

### 5.1 アプリの起動確認

1. デプロイ完了後、アプリのURLにアクセス:
   - 例: `https://context-cut-pro.streamlit.app`
2. 画面に以下が表示されればOK:
   - ✅ タイトル: 「🎬 Context Cut Pro」
   - ✅ サイドバーに動画取得オプション
   - ✅ エラーメッセージが表示されていない

### 5.2 フォントの確認

初回起動時:
- デフォルトフォント（Noto Sans JP）が自動的にダウンロードされます
- 「フォントのダウンロードが完了しました!」というメッセージが表示される場合があります

### 5.3 動作テスト

#### テスト1: ローカルファイルアップロード
1. サイドバー → 「ローカルファイル」を選択
2. 小さな動画ファイル（< 100MB）をアップロード
3. 「文字起こしを実行」をクリック
4. 処理完了までしばらく待つ

#### テスト2: Google Drive連携
1. Google Driveに動画をアップロード
2. サービスアカウントと共有
3. URLをコピーしてContext Cut Proに貼り付け
4. 「ダウンロード」をクリック

---

## 🎨 Step 6: カスタマイズ（オプション）

### 6.1 カスタムフォントの追加

#### リポジトリに追加（推奨）

```bash
# フォントファイルを fonts/ ディレクトリにコピー
cp /path/to/your-custom-font.ttf fonts/

# Gitにコミット
git add fonts/your-custom-font.ttf
git commit -m "feat: Add custom font"
git push

# Streamlit Cloud で自動デプロイされる
```

#### アプリ内でアップロード（一時的）

1. 「💬 テロップ編集」タブ
2. 「新しいフォントを追加」セクション
3. フォントファイルをアップロード
4. 「フォントを追加」をクリック

**注意**: アプリ再デプロイ時にリセットされます。

### 6.2 テーマのカスタマイズ

`.streamlit/config.toml` を編集:

```toml
[theme]
primaryColor = "#FF4B4B"        # メインカラー
backgroundColor = "#FFFFFF"     # 背景色
secondaryBackgroundColor = "#F0F2F6"  # サイドバー背景色
textColor = "#262730"           # テキスト色
font = "sans serif"             # フォント
```

変更後、GitHubにプッシュすると自動デプロイされます。

---

## 🐛 トラブルシューティング

### エラー1: "Google Cloud認証情報が設定されていません"

**原因**: Secrets が正しく設定されていない

**解決策**:
1. Settings → Secrets を開く
2. `[gcp_service_account]` セクションが存在するか確認
3. すべてのキーが正しく入力されているか確認
4. Save後、アプリを再起動（Reboot app）

### エラー2: "ffmpeg: command not found"

**原因**: `packages.txt` が正しく読み込まれていない

**解決策**:
1. リポジトリに `packages.txt` が存在するか確認
2. 内容が `ffmpeg` のみであることを確認
3. Settings → Reboot app

### エラー3: メモリエラー（Out of Memory）

**原因**: 大容量の動画ファイル

**解決策**:
- 動画ファイルを圧縮（< 500MB推奨）
- 動画の長さを短くカット（< 10分推奨）
- Streamlit Community Cloud の無料プランはメモリ制限あり

### エラー4: Whisperの処理が遅い

**原因**: CPU処理のため時間がかかる

**対策**:
- 動画を短くカット（5分以内推奨）
- 処理完了までしばらく待つ（10分動画で5〜10分程度）
- GPUは利用できません（無料プラン）

### エラー5: フォントが表示されない

**原因**: フォントファイルが正しく配置されていない

**解決策**:
1. リポジトリの `fonts/` ディレクトリを確認
2. `.ttf` または `.otf` ファイルが存在するか確認
3. ファイル名に特殊文字がないか確認
4. Reboot app

---

## 📊 リソース制限（Streamlit Community Cloud 無料プラン）

| リソース | 制限値 |
|----------|--------|
| CPU | 共有（制限あり） |
| メモリ | 約1GB |
| ストレージ | 一時的（再起動でリセット） |
| アップロード | 最大2GB（config.toml設定） |
| 実行時間 | 制限なし（アイドル時に停止） |

**推奨**:
- 動画サイズ: < 500MB
- 動画長さ: < 10分
- 処理時間: < 15分/動画

---

## 🔄 更新とメンテナンス

### コード更新

```bash
# 変更を加える
nano app.py

# コミット
git add .
git commit -m "feat: Add new feature"
git push

# Streamlit Cloud で自動デプロイ（約1〜2分）
```

### アプリの再起動

1. Streamlit Cloud のアプリ画面
2. 右上のメニュー → 「Reboot app」

### ログの確認

1. Streamlit Cloud のアプリ画面
2. 右下の「Manage app」→ 「Logs」

---

## 🎯 ベストプラクティス

### セキュリティ

- ✅ `secrets.toml` を `.gitignore` に含める（デフォルト設定済み）
- ✅ サービスアカウントの権限を最小限に（閲覧者のみ）
- ✅ JSONキーファイルを安全に保管
- ❌ Secretsをコードに直接記述しない
- ❌ パブリックリポジトリに認証情報をコミットしない

### パフォーマンス

- ✅ 動画を圧縮してからアップロード
- ✅ 必要な範囲のみをカット
- ✅ キャッシュ機能を活用（Whisperモデル）
- ❌ 大容量ファイル（> 1GB）の処理は避ける
- ❌ 長時間動画（> 30分）の一括処理は避ける

### ユーザビリティ

- ✅ テスト動画でフローを確認
- ✅ エラーメッセージをユーザーに表示
- ✅ プログレスバーで進捗を表示
- ✅ プレビュー機能で確認してから生成

---

## 📞 サポート

### 公式ドキュメント

- [Streamlit Docs](https://docs.streamlit.io/)
- [Streamlit Community Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Whisper GitHub](https://github.com/openai/whisper)

### コミュニティ

- [Streamlit Forum](https://discuss.streamlit.io/)
- [GitHub Issues](https://github.com/yourusername/context-cut-pro/issues)

---

## 🎉 デプロイ成功！

Context Cut Pro が正常にデプロイされました！

**次のステップ**:
1. ✅ テスト動画で動作確認
2. ✅ カスタムフォントの追加
3. ✅ ユーザーに共有
4. ✅ フィードバック収集
5. ✅ 機能改善

**Enjoy creating amazing video clips! 🎬✨**
