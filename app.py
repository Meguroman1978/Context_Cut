"""
Context Cut Pro - AI動画自動切り抜き＆テロップ編集ツール
Streamlit Community Cloud デプロイ対応版
"""

import streamlit as st
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import io
import subprocess
import re

# 必要なライブラリのインポート
try:
    import whisper
    import ffmpeg
    import chromadb
    from chromadb.config import Settings
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from google.oauth2 import service_account
    import yt_dlp
    import torch
except ImportError as e:
    st.error(f"必要なライブラリのインポートに失敗しました: {e}")
    st.stop()

# ============================
# 定数とディレクトリ設定
# ============================
FONTS_DIR = Path("./fonts")
TEMP_VIDEOS_DIR = Path("./temp_videos")
CHROMADB_DIR = Path("./chromadb_data")

# ディレクトリの作成
for dir_path in [FONTS_DIR, TEMP_VIDEOS_DIR, CHROMADB_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# デフォルトフォントの確認とダウンロード
DEFAULT_FONT = FONTS_DIR / "NotoSansJP-Regular.ttf"
if not DEFAULT_FONT.exists():
    st.warning("デフォルトフォントが見つかりません。初回起動時にダウンロードします...")
    try:
        import urllib.request
        font_url = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansJP-Regular.otf"
        urllib.request.urlretrieve(font_url, str(DEFAULT_FONT))
        st.success("フォントのダウンロードが完了しました!")
    except Exception as e:
        st.error(f"フォントのダウンロードに失敗しました: {e}")

# ============================
# ユーティリティ関数
# ============================

def get_available_fonts() -> List[str]:
    """利用可能なフォントファイルのリストを取得"""
    font_extensions = ['.ttf', '.otf']
    fonts = []
    
    if FONTS_DIR.exists():
        for font_file in FONTS_DIR.iterdir():
            if font_file.suffix.lower() in font_extensions:
                fonts.append(font_file.name)
    
    return sorted(fonts)


def save_uploaded_font(uploaded_file) -> bool:
    """アップロードされたフォントファイルを保存"""
    try:
        font_path = FONTS_DIR / uploaded_file.name
        with open(font_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception as e:
        st.error(f"フォントの保存に失敗しました: {e}")
        return False


def extract_google_drive_id(url: str) -> Optional[Dict[str, str]]:
    """Google Drive URLからファイルID/フォルダIDを抽出"""
    # ファイルURLのパターン
    file_patterns = [
        r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
    ]
    
    # フォルダURLのパターン
    folder_patterns = [
        r"drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)",
    ]
    
    # ファイルIDを検索
    for pattern in file_patterns:
        match = re.search(pattern, url)
        if match:
            return {"type": "file", "id": match.group(1)}
    
    # フォルダIDを検索
    for pattern in folder_patterns:
        match = re.search(pattern, url)
        if match:
            return {"type": "folder", "id": match.group(1)}
    
    return None


def check_gcp_credentials() -> Dict[str, any]:
    """GCP認証情報の状態をチェック"""
    result = {
        "has_credentials": False,
        "is_valid": False,
        "error": None,
        "project_id": None,
        "client_email": None
    }
    
    try:
        if "gcp_service_account" not in st.secrets:
            result["error"] = "認証情報が設定されていません"
            return result
        
        result["has_credentials"] = True
        credentials_dict = dict(st.secrets["gcp_service_account"])
        
        # 基本情報を取得
        result["project_id"] = credentials_dict.get("project_id", "不明")
        result["client_email"] = credentials_dict.get("client_email", "不明")
        
        # 認証情報の妥当性をテスト
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        
        # 簡単なAPIコールでテスト（自分のDriveルート情報を取得）
        service.files().list(pageSize=1).execute()
        
        result["is_valid"] = True
        return result
        
    except Exception as e:
        result["error"] = str(e)
        return result


def list_videos_in_folder(folder_id: str, service) -> List[Dict[str, str]]:
    """フォルダ内の動画ファイル一覧を取得"""
    try:
        video_extensions = ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv']
        query = f"'{folder_id}' in parents and trashed=false"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, size)",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        # 動画ファイルのみをフィルタ
        video_files = []
        for file in files:
            name = file.get('name', '')
            ext = name.split('.')[-1].lower() if '.' in name else ''
            mime = file.get('mimeType', '')
            
            if ext in video_extensions or 'video' in mime:
                video_files.append({
                    'id': file['id'],
                    'name': name,
                    'size': file.get('size', 0)
                })
        
        return video_files
    except Exception as e:
        st.error(f"フォルダ内のファイル取得に失敗しました: {e}")
        return []


def download_from_google_drive(file_id: str, output_path: str) -> bool:
    """Google Driveから動画をダウンロード"""
    try:
        # Secrets から認証情報を取得
        if "gcp_service_account" not in st.secrets:
            st.error("Google Cloud認証情報が設定されていません。")
            return False
        
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        request = service.files().get_media(fileId=file_id)
        
        with io.FileIO(output_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            progress_bar = st.progress(0)
            
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    progress_bar.progress(progress)
        
        return True
    except Exception as e:
        st.error(f"Google Driveからのダウンロードに失敗しました: {e}")
        return False


def download_from_web(url: str, output_path: str) -> bool:
    """Web URLから動画をダウンロード（yt-dlp使用）"""
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            st.info("動画をダウンロード中...")
            ydl.download([url])
        
        return True
    except Exception as e:
        st.error(f"Web URLからのダウンロードに失敗しました: {e}")
        return False


@st.cache_resource
def load_whisper_model(model_name: str = "base"):
    """Whisperモデルをロード（キャッシュ付き）"""
    try:
        return whisper.load_model(model_name)
    except Exception as e:
        st.error(f"Whisperモデルのロードに失敗しました: {e}")
        return None


def check_video_has_audio(video_path: str) -> bool:
    """動画に音声トラックがあるかチェック"""
    try:
        probe = ffmpeg.probe(video_path)
        audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
        return len(audio_streams) > 0
    except Exception as e:
        st.warning(f"動画情報の取得に失敗: {e}")
        return False


def transcribe_video(video_path: str, model) -> Optional[Dict]:
    """動画から音声を文字起こし"""
    try:
        # 動画の長さをチェック
        duration = get_video_duration(video_path)
        if duration < 0.5:
            st.error(f"❌ 動画が短すぎます（{duration:.2f}秒）。最低0.5秒以上の動画が必要です。")
            return None
        
        # 音声トラックの確認
        if not check_video_has_audio(video_path):
            st.error("❌ この動画には音声トラックがありません。")
            st.info("💡 音声付きの動画を使用するか、音声なしで動画編集を行ってください。")
            return None
        
        st.info(f"🎤 動画を文字起こし中... （動画の長さ: {duration:.1f}秒、数分かかる場合があります）")
        
        # 一時的な音声ファイルを作成（Whisperが処理しやすい形式に変換）
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name
        
        try:
            # FFmpegで音声を抽出してWAV形式に変換
            (
                ffmpeg
                .input(video_path)
                .output(tmp_audio_path, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            
            # 音声ファイルのサイズチェック
            import os
            audio_size = os.path.getsize(tmp_audio_path)
            if audio_size < 1000:  # 1KB未満
                st.error("❌ 抽出された音声データが小さすぎます。音声が含まれていない可能性があります。")
                os.unlink(tmp_audio_path)
                return None
            
            # Whisperで文字起こし実行
            result = model.transcribe(
                tmp_audio_path, 
                language='ja', 
                verbose=False,
                fp16=False,  # CPU互換性のため
                temperature=0.0,  # より安定した結果を得る
                condition_on_previous_text=False  # エラー回避
            )
            
            # 一時ファイルを削除
            os.unlink(tmp_audio_path)
            
        except Exception as e:
            # 一時ファイルのクリーンアップ
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)
            raise e
        
        # 結果の検証
        if not result or 'segments' not in result:
            st.error("❌ 文字起こし結果が空です。")
            return None
        
        if len(result['segments']) == 0:
            st.warning("⚠️ 音声は検出されましたが、テキストが認識できませんでした。")
            st.info("💡 考えられる原因:\n- 音声が小さすぎる\n- 背景ノイズが多い\n- 言語が日本語ではない")
            return None
        
        st.success(f"✅ 文字起こし完了！ {len(result['segments'])}個のセグメントを検出しました。")
        return result
        
    except Exception as e:
        error_msg = str(e)
        
        if "cannot reshape tensor" in error_msg:
            st.error("❌ 音声データの処理に失敗しました。")
            st.error("**エラー詳細**: 音声ストリームが空または破損しています。")
            st.info("""
            💡 **対処方法**:
            1. 動画に音声トラックが含まれているか確認してください
            2. 別の動画形式（MP4, MOV）で試してください
            3. 音声付きで動画を再エンコードしてみてください
               ```
               ffmpeg -i input.mp4 -c:v copy -c:a aac output.mp4
               ```
            4. または、音声なしで動画編集機能のみ使用してください
            """)
        else:
            st.error(f"❌ 文字起こしに失敗しました: {error_msg}")
            st.info("💡 動画ファイルが破損していないか、または別の動画で試してください。")
        
        return None


def setup_chromadb() -> chromadb.Client:
    """ChromaDBクライアントをセットアップ"""
    try:
        client = chromadb.Client(Settings(
            persist_directory=str(CHROMADB_DIR),
            anonymized_telemetry=False
        ))
        return client
    except Exception as e:
        st.error(f"ChromaDBのセットアップに失敗しました: {e}")
        return None


def index_transcription_to_chromadb(transcription: Dict, video_name: str, client: chromadb.Client):
    """文字起こし結果をChromaDBにインデックス化"""
    try:
        # コレクションの作成または取得
        collection_name = f"video_{video_name}".replace(" ", "_").replace(".", "_")
        
        # 既存のコレクションを削除（更新の場合）
        try:
            client.delete_collection(name=collection_name)
        except:
            pass
        
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # セグメントごとにインデックス化
        documents = []
        metadatas = []
        ids = []
        
        for i, segment in enumerate(transcription['segments']):
            text = segment['text'].strip()
            if text:
                documents.append(text)
                metadatas.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'segment_id': i
                })
                ids.append(f"segment_{i}")
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            st.success(f"✅ {len(documents)}件のセグメントをインデックス化しました!")
            return collection_name
        else:
            st.warning("インデックス化可能なテキストが見つかりませんでした。")
            return None
            
    except Exception as e:
        st.error(f"インデックス化に失敗しました: {e}")
        return None


def search_scenes(query: str, collection_name: str, client: chromadb.Client, n_results: int = 5) -> List[Dict]:
    """自然言語クエリでシーンを検索"""
    try:
        collection = client.get_collection(name=collection_name)
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        scenes = []
        if results['metadatas'] and len(results['metadatas']) > 0:
            for i, metadata in enumerate(results['metadatas'][0]):
                scenes.append({
                    'text': results['documents'][0][i],
                    'start': metadata['start'],
                    'end': metadata['end'],
                    'segment_id': metadata['segment_id']
                })
        
        return scenes
    except Exception as e:
        st.error(f"検索に失敗しました: {e}")
        return []


def get_video_duration(video_path: str) -> float:
    """動画の長さを取得"""
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['streams'][0]['duration'])
        return duration
    except Exception as e:
        st.error(f"動画の長さの取得に失敗しました: {e}")
        return 0.0


def create_preview_clip(video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
    """プレビュー用の動画クリップを作成（高速コピーモード）"""
    try:
        (
            ffmpeg
            .input(video_path, ss=start_time, to=end_time)
            .output(output_path, c='copy', loglevel='error')
            .overwrite_output()
            .run()
        )
        return True
    except Exception as e:
        st.error(f"プレビュー作成に失敗しました: {e}")
        return False


def get_background_settings(background_type: str) -> Tuple[int, str, int]:
    """背景タイプから設定を取得
    
    Returns:
        (box, boxcolor, boxborderw)
    """
    # シンプル背景
    simple_backgrounds = {
        "なし（透明）": (0, "black@0.0", 0),
        "黒（半透明）": (1, "black@0.5", 5),
        "白（半透明）": (1, "white@0.8", 5),
        "黒（不透明）": (1, "black@1.0", 5),
        "白（不透明）": (1, "white@1.0", 5),
        "黄色（半透明）": (1, "yellow@0.7", 5),
        "青（半透明）": (1, "blue@0.7", 5),
        "赤（半透明）": (1, "red@0.7", 5),
        "緑（半透明）": (1, "green@0.7", 5),
    }
    
    # 吹き出し風背景（角丸の大きさと色で差別化）
    balloon_backgrounds = {
        # 楕円系 - 大きめの角丸で楕円感を出す
        "💬 楕円吹き出し（白）": (1, "white@0.98", 25),
        "💬 楕円吹き出し（黒）": (1, "black@0.90", 25),
        
        # 風船系 - 最大の角丸でふんわり感
        "🎈 風船吹き出し（白）": (1, "white@0.98", 35),
        "🎈 風船吹き出し（黒）": (1, "black@0.90", 35),
        
        # 角丸長方形 - 標準的な角丸
        "🗨️ 角丸長方形（白）": (1, "white@0.98", 15),
        "🗨️ 角丸長方形（黒）": (1, "black@0.90", 15),
        
        # 角張り - 最小の角丸
        "⬛ 角張り長方形（白）": (1, "white@0.98", 3),
        "⬛ 角張り長方形（黒）": (1, "black@0.90", 3),
        
        # ダイア形 - 中程度の角丸
        "💍 ダイア形（白）": (1, "white@0.98", 18),
        "💍 ダイア形（黒）": (1, "black@0.90", 18),
        
        # 六角形 - やや大きめの角丸
        "⬣ 六角形（白）": (1, "white@0.98", 22),
        "⬣ 六角形（黒）": (1, "black@0.90", 22),
        
        # 雲形 - 大きめの角丸でふわふわ感
        "☁️ 雲形（白）": (1, "white@0.98", 30),
        "☁️ 雲形（黒）": (1, "black@0.90", 30),
        
        # 爆発形 - 非常に大きな角丸でインパクト
        "💥 爆発形（白）": (1, "yellow@0.95", 40),  # 黄色で爆発感
        "💥 爆発形（黒）": (1, "red@0.85", 40),     # 赤で爆発感
        
        # 放射線 - 最大の角丸
        "⭐ 放射線（白）": (1, "yellow@0.95", 45),  # 黄色で放射感
        "⭐ 放射線（黒）": (1, "orange@0.85", 45),  # オレンジで放射感
    }
    
    # 該当する背景を検索
    if background_type in simple_backgrounds:
        return simple_backgrounds[background_type]
    elif background_type in balloon_backgrounds:
        return balloon_backgrounds[background_type]
    else:
        # デフォルト
        return (0, "black@0.0", 0)


def generate_final_video_with_subtitle(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    subtitle_text: str,
    font_file: str,
    font_size: int,
    font_color: str,
    background_type: str,
    x_position: str = "(w-text_w)/2",
    y_position: str = "h-text_h-20"
) -> bool:
    """テロップ付き最終動画を生成"""
    try:
        # フォントパスの取得（Windowsパスを/に変換）
        font_path = str(FONTS_DIR / font_file).replace("\\", "/")
        
        # テキストのエスケープ処理（FFmpegのdrawtextフィルタ用）
        # シングルクォート、バックスラッシュ、コロン、改行をエスケープ
        escaped_text = subtitle_text.replace("\\", "\\\\\\\\")
        escaped_text = escaped_text.replace("'", "'\\\\''")  
        escaped_text = escaped_text.replace(":", "\\:")
        escaped_text = escaped_text.replace("\n", " ")
        
        # 背景設定を取得
        box, boxcolor, boxborderw = get_background_settings(background_type)
        
        # FFmpegコマンドの実行
        input_stream = ffmpeg.input(video_path, ss=start_time, to=end_time)
        
        # 映像ストリームにdrawtextフィルタを適用
        if box > 0:
            video_stream = input_stream.video.filter(
                'drawtext',
                text=escaped_text,
                fontfile=font_path,
                fontsize=font_size,
                fontcolor=font_color,
                x=x_position,
                y=y_position,
                box=box,
                boxcolor=boxcolor,
                boxborderw=boxborderw
            )
        else:
            video_stream = input_stream.video.filter(
                'drawtext',
                text=escaped_text,
                fontfile=font_path,
                fontsize=font_size,
                fontcolor=font_color,
                x=x_position,
                y=y_position
            )
        
        # 音声ストリームを取得（そのままコピー）
        audio_stream = input_stream.audio
        
        # 出力（映像と音声を結合）
        output = ffmpeg.output(
            video_stream,
            audio_stream,
            output_path,
            vcodec='libx264',
            acodec='aac',
            audio_bitrate='192k',
            **{'loglevel': 'warning', 'y': None}
        )
        
        ffmpeg.run(output, overwrite_output=True, capture_stderr=True)
        
        return True
    except ffmpeg.Error as e:
        st.error(f"最終動画の生成に失敗しました: FFmpegエラー")
        stderr_output = e.stderr.decode('utf-8') if e.stderr else "詳細なし"
        st.error(f"詳細: {stderr_output}")
        return False
    except Exception as e:
        st.error(f"最終動画の生成に失敗しました: {e}")
        st.error(f"詳細: {str(e)}")
        return False


# ============================
# Streamlit UI
# ============================

def main():
    st.set_page_config(
        page_title="Context Cut Pro",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 Context Cut Pro")
    st.subheader("AI動画自動切り抜き＆テロップ編集ツール")
    
    # セッションステートの初期化
    if 'video_path' not in st.session_state:
        st.session_state.video_path = None
    if 'transcription' not in st.session_state:
        st.session_state.transcription = None
    if 'collection_name' not in st.session_state:
        st.session_state.collection_name = None
    if 'video_duration' not in st.session_state:
        st.session_state.video_duration = 0
    if 'chromadb_client' not in st.session_state:
        st.session_state.chromadb_client = setup_chromadb()
    if 'selected_start' not in st.session_state:
        st.session_state.selected_start = 0.0
    if 'selected_end' not in st.session_state:
        st.session_state.selected_end = 10.0
    if 'show_scene_preview' not in st.session_state:
        st.session_state.show_scene_preview = False
    if 'preview_scene_start' not in st.session_state:
        st.session_state.preview_scene_start = 0.0
    if 'preview_scene_end' not in st.session_state:
        st.session_state.preview_scene_end = 0.0
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    if 'scene_preview_dialog_open' not in st.session_state:
        st.session_state.scene_preview_dialog_open = False
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'scene_selected' not in st.session_state:
        st.session_state.scene_selected = False
    
    # サイドバー: 動画取得
    with st.sidebar:
        st.header("📥 動画取得")
        
        video_source = st.radio(
            "動画ソースを選択",
            ["Google Drive URL", "Web URL（YouTube等）", "ローカルファイル"]
        )
        
        if video_source == "Google Drive URL":
            # 認証情報の状態確認
            st.subheader("🔐 認証情報の確認")
            
            cred_status = check_gcp_credentials()
            
            if cred_status["has_credentials"]:
                if cred_status["is_valid"]:
                    st.success("✅ Google Cloud認証情報: 有効")
                    with st.expander("📋 認証情報の詳細"):
                        st.write(f"**プロジェクトID**: `{cred_status['project_id']}`")
                        st.write(f"**サービスアカウント**: `{cred_status['client_email']}`")
                        st.info("✓ Google Drive APIへの接続テスト: 成功")
                else:
                    st.error(f"❌ 認証情報は設定されていますが、無効です")
                    st.error(f"エラー: {cred_status['error']}")
                    with st.expander("🔧 トラブルシューティング"):
                        st.markdown("""
                        **考えられる原因**:
                        - 認証情報が正しくない形式
                        - サービスアカウントが無効化されている
                        - Google Drive APIが有効化されていない
                        
                        **対処方法**:
                        1. GCPコンソールでサービスアカウントを確認
                        2. Google Drive APIが有効か確認
                        3. 新しいJSONキーを生成して再設定
                        """)
            else:
                st.warning("⚠️ Google Cloud認証情報が設定されていません")
                
                with st.expander("📖 認証情報の設定方法", expanded=True):
                    st.markdown("""
                    ### Google Drive連携を使用するには、GCP認証情報が必要です
                    
                    #### 🔧 設定手順:
                    
                    **Step 1: Google Cloud Platformでサービスアカウントを作成**
                    
                    1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
                    2. プロジェクトを作成または選択
                    3. 「APIとサービス」→「ライブラリ」→「Google Drive API」を検索して有効化
                    4. 「APIとサービス」→「認証情報」
                    5. 「認証情報を作成」→「サービスアカウント」
                    6. 名前を入力（例: `context-cut-pro`）
                    7. 役割: 「閲覧者」を選択
                    8. 「完了」をクリック
                    9. 作成したサービスアカウントをクリック
                    10. 「キー」タブ → 「鍵を追加」→「新しい鍵を作成」
                    11. **JSON** を選択してダウンロード
                    
                    **Step 2: Streamlit Cloudで認証情報を設定**
                    
                    1. Streamlit Cloudのアプリ画面で「Settings」（⚙️）をクリック
                    2. 「Secrets」を選択
                    3. 以下の形式でJSONキーをTOML形式に変換して貼り付け:
                    
                    ```toml
                    [gcp_service_account]
                    type = "service_account"
                    project_id = "your-project-id"
                    private_key_id = "your-private-key-id"
                    private_key = "-----BEGIN PRIVATE KEY-----\\nYour-Key-Here\\n-----END PRIVATE KEY-----\\n"
                    client_email = "your-service-account@your-project.iam.gserviceaccount.com"
                    client_id = "123456789..."
                    auth_uri = "https://accounts.google.com/o/oauth2/auth"
                    token_uri = "https://oauth2.googleapis.com/token"
                    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
                    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
                    ```
                    
                    4. 「Save」をクリック
                    5. アプリが自動的に再起動されます
                    
                    **Step 3: Google Driveで共有設定**
                    
                    - サービスアカウントのメールアドレス（`xxx@xxx.iam.gserviceaccount.com`）に、
                      対象の動画ファイルまたはフォルダを「閲覧者」として共有してください
                    
                    ---
                    
                    💡 **詳しい手順は、リポジトリの `DEPLOYMENT_GUIDE.md` を参照してください**
                    """)
                
                st.info("💡 認証情報を設定せずに、「ローカルファイル」または「Web URL」でも動画を取得できます")
            
            st.divider()
            
            # Google Drive URL入力（認証情報が有効な場合のみ）
            if cred_status["is_valid"]:
                st.subheader("📥 Google Drive URL")
                gdrive_url = st.text_input("Google Drive URL (ファイルまたはフォルダ)")
                
                if st.button("URLを解析"):
                    result = extract_google_drive_id(gdrive_url)
                    if result:
                        if result['type'] == 'file':
                            # ファイルの場合は直接ダウンロード
                            st.session_state.gdrive_result = result
                            st.session_state.gdrive_selected_file = result['id']
                            st.info("✅ ファイルURLを検出しました。「ダウンロード」ボタンをクリックしてください。")
                        elif result['type'] == 'folder':
                            # フォルダの場合は動画一覧を取得
                            st.session_state.gdrive_result = result
                            with st.spinner("フォルダ内の動画を検索中..."):
                                try:
                                    credentials_dict = dict(st.secrets["gcp_service_account"])
                                    credentials = service_account.Credentials.from_service_account_info(
                                        credentials_dict,
                                        scopes=['https://www.googleapis.com/auth/drive.readonly']
                                    )
                                    service = build('drive', 'v3', credentials=credentials)
                                    videos = list_videos_in_folder(result['id'], service)
                                    
                                    if videos:
                                        st.session_state.gdrive_folder_videos = videos
                                        st.success(f"✅ {len(videos)}件の動画ファイルが見つかりました。")
                                    else:
                                        st.warning("フォルダ内に動画ファイルが見つかりませんでした。")
                                except Exception as e:
                                    st.error(f"フォルダの読み込みに失敗しました: {e}")
                                    st.info("💡 サービスアカウントにフォルダの共有権限があるか確認してください")
                    else:
                        st.error("無効なGoogle Drive URLです。ファイルまたはフォルダのURLを入力してください。")
                
                # フォルダから動画を選択
                if 'gdrive_folder_videos' in st.session_state and st.session_state.gdrive_folder_videos:
                    st.subheader("📂 フォルダ内の動画を選択")
                    video_names = [f"{v['name']} ({int(v['size'])//1024//1024}MB)" if v['size'] else v['name'] 
                                  for v in st.session_state.gdrive_folder_videos]
                    selected_idx = st.selectbox("動画を選択", range(len(video_names)), 
                                               format_func=lambda i: video_names[i])
                    st.session_state.gdrive_selected_file = st.session_state.gdrive_folder_videos[selected_idx]['id']
                
                # ダウンロード実行
                if 'gdrive_selected_file' in st.session_state:
                    if st.button("ダウンロード"):
                        file_id = st.session_state.gdrive_selected_file
                        output_path = str(TEMP_VIDEOS_DIR / f"video_{file_id}.mp4")
                        if download_from_google_drive(file_id, output_path):
                            st.session_state.video_path = output_path
                            st.success("✅ ダウンロード完了!")
                            # セッション状態をクリア
                            if 'gdrive_folder_videos' in st.session_state:
                                del st.session_state.gdrive_folder_videos
                            if 'gdrive_selected_file' in st.session_state:
                                del st.session_state.gdrive_selected_file
            else:
                st.warning("⚠️ Google Drive機能を使用するには、上記の手順で認証情報を設定してください。")
                st.info("📌 認証情報なしでも、「Web URL（YouTube等）」または「ローカルファイル」は利用できます。")
        
        elif video_source == "Web URL（YouTube等）":
            web_url = st.text_input("動画URL")
            if st.button("ダウンロード"):
                output_path = str(TEMP_VIDEOS_DIR / "video_web.mp4")
                if download_from_web(web_url, output_path):
                    st.session_state.video_path = output_path
                    st.success("✅ ダウンロード完了!")
        
        elif video_source == "ローカルファイル":
            uploaded_file = st.file_uploader("動画ファイルをアップロード", type=['mp4', 'mov', 'avi', 'mkv'])
            if uploaded_file:
                output_path = str(TEMP_VIDEOS_DIR / uploaded_file.name)
                with open(output_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state.video_path = output_path
                st.success("✅ アップロード完了!")
        
        # 文字起こし実行
        st.header("🎤 AI文字起こし")
        if st.session_state.video_path:
            st.info("💡 シーン検索機能を使用する場合は文字起こしが必要です。\n文字起こしなしでも、カット範囲指定とテロップ編集は使用できます。")
            
            col_trans1, col_trans2 = st.columns(2)
            with col_trans1:
                if st.button("🎤 文字起こしを実行", use_container_width=True):
                    model = load_whisper_model("base")
                    if model:
                        transcription = transcribe_video(st.session_state.video_path, model)
                        if transcription:
                            st.session_state.transcription = transcription
                            st.session_state.video_duration = get_video_duration(st.session_state.video_path)
                            
                            # ChromaDBにインデックス化
                            video_name = Path(st.session_state.video_path).stem
                            collection_name = index_transcription_to_chromadb(
                                transcription,
                                video_name,
                                st.session_state.chromadb_client
                            )
                            st.session_state.collection_name = collection_name
            
            with col_trans2:
                if st.button("⏭️ 文字起こしをスキップ", use_container_width=True):
                    st.session_state.transcription = {"segments": []}  # 空の文字起こし
                    st.session_state.video_duration = get_video_duration(st.session_state.video_path)
                    st.session_state.skip_transcription = True
                    st.success("✅ 文字起こしをスキップしました。カット範囲指定とテロップ編集が使用できます。")
                    st.rerun()
        else:
            st.info("まず動画を取得してください。")
    
    # メインエリア
    if st.session_state.video_path and st.session_state.transcription is not None:
        
        # タブUIの選択状態を管理
        tab_names = ["🔍 シーン検索", "✂️ カット範囲指定", "💬 テロップ編集"]
        
        # タブの選択を制御
        if 'force_tab_index' in st.session_state:
            # Streamlit 1.31.0以降ではst.tabsに選択インデックスを渡せないため、
            # ページ全体をリロードする方法を使用
            st.session_state.active_tab = st.session_state.force_tab_index
            del st.session_state.force_tab_index
        
        tab1, tab2, tab3 = st.tabs(tab_names)
        
        # タブ1: シーン検索
        with tab1:
            st.header("🔍 自然言語シーン検索")
            
            # 文字起こしがスキップされた場合の警告
            if st.session_state.get('skip_transcription', False):
                st.warning("⚠️ 文字起こしがスキップされたため、シーン検索機能は使用できません。")
                st.info("💡 シーン検索を使用する場合は、サイドバーから「文字起こしを実行」を行ってください。\n\nまたは、「✂️ カット範囲指定」タブで手動で範囲を指定してください。")
            else:
                search_query = st.text_input(
                    "検索クエリを入力",
                    placeholder="例: 面白いシーン, 感動的な場面, 商品の説明"
                )
                
                n_results = st.slider("検索結果数", 1, 10, 5)
                
                if st.button("検索実行"):
                    if search_query and st.session_state.collection_name:
                        scenes = search_scenes(
                            search_query,
                            st.session_state.collection_name,
                            st.session_state.chromadb_client,
                            n_results
                        )
                        
                        if scenes:
                            # 検索結果をセッション状態に保存
                            st.session_state.search_results = scenes
                            st.success(f"✅ {len(scenes)}件のシーンが見つかりました!")
                        else:
                            st.session_state.search_results = []
                            st.warning("検索結果が見つかりませんでした。")
                
                # 検索結果の表示
                if st.session_state.search_results:
                    st.write(f"**{len(st.session_state.search_results)}件のシーン**")
                    
                    for i, scene in enumerate(st.session_state.search_results, 1):
                        with st.expander(f"シーン {i}: {scene['start']:.1f}s - {scene['end']:.1f}s"):
                            st.write(f"**テキスト:** {scene['text']}")
                            st.write(f"**開始:** {scene['start']:.2f}秒")
                            st.write(f"**終了:** {scene['end']:.2f}秒")
                            
                            # ボタンを横並びに配置
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                # シーンプレビューボタン
                                if st.button(f"🎬 プレビュー", key=f"preview_{i}", use_container_width=True):
                                    # プレビュー動画を生成
                                    with st.spinner("プレビューを生成中..."):
                                        preview_path = str(TEMP_VIDEOS_DIR / f"scene_preview_{i}.mp4")
                                        if create_preview_clip(
                                            st.session_state.video_path,
                                            scene['start'],
                                            scene['end'],
                                            preview_path
                                        ):
                                            # プレビュー用のセッション状態を設定
                                            st.session_state.preview_scene_start = scene['start']
                                            st.session_state.preview_scene_end = scene['end']
                                            st.session_state.preview_scene_id = i
                                            st.session_state.preview_scene_text = scene['text']
                                            st.session_state.current_scene_preview_path = preview_path
                                            st.session_state.scene_preview_dialog_open = True
                                            st.rerun()
                            
                            with col_btn2:
                                # シーンを選択ボタン
                                if st.button(f"✂️ 選択", key=f"select_{i}", use_container_width=True):
                                    st.session_state.selected_start = scene['start']
                                    st.session_state.selected_end = scene['end']
                                    st.session_state.scene_selected = True
                                    st.success(f"✅ シーンを選択しました！「カット範囲指定」タブを開いてください。")
                                    # 選択後にスクロールしてタブが見えるようにする
                                    st.rerun()
        
        # タブ2: カット範囲指定
        with tab2:
            st.header("✂️ カット範囲の指定")
            
            # シーン選択時のメッセージ表示
            if st.session_state.get('scene_selected', False):
                st.success(f"✅ シーンを選択しました！開始: {st.session_state.selected_start:.2f}秒、終了: {st.session_state.selected_end:.2f}秒")
                st.info("💡 スライダーまたは数値入力で範囲を調整できます。調整が終わったら「プレビューを生成」をクリックしてください。")
                # メッセージを一度だけ表示
                st.session_state.scene_selected = False
            
            # セッション状態から初期値を取得
            initial_start = float(st.session_state.selected_start)
            initial_end = float(st.session_state.selected_end)
            
            # 動画の長さを超えないように調整
            if initial_end > st.session_state.video_duration:
                initial_end = st.session_state.video_duration
            if initial_end <= initial_start:
                initial_end = min(initial_start + 5.0, st.session_state.video_duration)
            
            # Number Inputでの詳細設定（最初に表示）
            st.subheader("📏 詳細設定")
            col1, col2 = st.columns(2)
            
            with col1:
                start_time = st.number_input(
                    "開始時間（秒）",
                    min_value=0.0,
                    max_value=st.session_state.video_duration,
                    value=initial_start,
                    step=0.1,
                    key="cut_start_input",
                    format="%.2f"
                )
            
            with col2:
                end_time = st.number_input(
                    "終了時間（秒）",
                    min_value=0.0,
                    max_value=st.session_state.video_duration,
                    value=initial_end,
                    step=0.1,
                    key="cut_end_input",
                    format="%.2f"
                )
            
            # スライダーでの微調整
            st.subheader("🎯 スライダーで微調整")
            time_range = st.slider(
                "範囲選択",
                0.0,
                st.session_state.video_duration,
                (start_time, end_time),
                step=0.1,
                key="cut_range_slider"
            )
            
            # スライダーが変更された場合はそれを優先
            if time_range != (start_time, end_time):
                start_time, end_time = time_range
            
            st.write(f"📏 選択範囲: {end_time - start_time:.2f}秒")
            
            # 選択範囲を更新（次回のリロード時に反映）
            st.session_state.selected_start = start_time
            st.session_state.selected_end = end_time
            
            # プレビュー生成
            if st.button("プレビューを生成"):
                preview_path = str(TEMP_VIDEOS_DIR / "preview.mp4")
                if create_preview_clip(st.session_state.video_path, start_time, end_time, preview_path):
                    st.success("✅ プレビュー生成完了!")
                    st.session_state.preview_path = preview_path
                    st.session_state.clip_start = start_time
                    st.session_state.clip_end = end_time
            
            # プレビュー動画を小さく表示
            if 'preview_path' in st.session_state and st.session_state.preview_path:
                st.subheader("📹 プレビュー")
                
                # CSSで動画サイズを小さくする
                st.markdown(
                    """
                    <style>
                    [data-testid="stVideo"] {
                        max-width: 400px !important;
                        margin: 0 auto;
                    }
                    [data-testid="stVideo"] video {
                        max-width: 100% !important;
                        height: auto !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                st.video(st.session_state.preview_path)
        
        # タブ3: テロップ編集
        with tab3:
            st.header("💬 テロップ編集")
            
            if 'clip_start' not in st.session_state:
                st.warning("まず「カット範囲指定」タブでプレビューを生成してください。")
            else:
                # 2カラムレイアウト: 左側にプレビュー、右側に設定
                col_preview, col_settings = st.columns([1, 1])
                
                with col_settings:
                    # テキスト入力
                    subtitle_text = st.text_area(
                        "テロップテキスト",
                        placeholder="ここにテロップを入力してください",
                        height=100,
                        key="subtitle_text_input"
                    )
                    
                    # スタイル設定
                    st.subheader("📐 スタイル設定")
                    
                    # フォント選択
                    available_fonts = get_available_fonts()
                    
                    if not available_fonts:
                        st.error("利用可能なフォントがありません。")
                        selected_font = None
                    else:
                        selected_font = st.selectbox(
                            "フォント選択",
                            available_fonts,
                            index=0,
                            key="font_select"
                        )
                    
                    # フォントサイズ
                    font_size = st.slider("フォントサイズ", 24, 120, 48, key="font_size_slider")
                    
                    # 文字色
                    font_color = st.color_picker("文字色", "#FFFFFF", key="font_color_picker")
                    
                    # 背景デザイン
                    background_category = st.radio(
                        "背景カテゴリ",
                        ["シンプル", "吹き出し風"],
                        key="background_category",
                        horizontal=True
                    )
                    
                    if background_category == "シンプル":
                        background_type = st.selectbox(
                            "背景タイプ",
                            [
                                "なし（透明）",
                                "黒（半透明）",
                                "白（半透明）",
                                "黒（不透明）",
                                "白（不透明）",
                                "黄色（半透明）",
                                "青（半透明）",
                                "赤（半透明）",
                                "緑（半透明）"
                            ],
                            key="background_select_simple"
                        )
                    else:
                        background_type = st.selectbox(
                            "吹き出しデザイン",
                            [
                                "💬 楕円吹き出し（白）",
                                "💬 楕円吹き出し（黒）",
                                "🎈 風船吹き出し（白）",
                                "🎈 風船吹き出し（黒）",
                                "🗨️ 角丸長方形（白）",
                                "🗨️ 角丸長方形（黒）",
                                "⬟ 角張り長方形（白）",
                                "⬟ 角張り長方形（黒）",
                                "💍 ダイヤ形（白）",
                                "💍 ダイヤ形（黒）",
                                "⬣ 六角形（白）",
                                "⬣ 六角形（黒）",
                                "☁️ 雲形（白）",
                                "☁️ 雲形（黒）",
                                "💥 爆発形（白）",
                                "💥 爆発形（黒）",
                                "⭐ 放射線（白）",
                                "⭐ 放射線（黒）"
                            ],
                            key="background_select_balloon"
                        )
                    
                    # 位置設定
                    position_mode = st.radio(
                        "位置設定モード",
                        ["プリセット", "カスタム（詳細）"],
                        key="position_mode",
                        horizontal=True
                    )
                    
                    if position_mode == "プリセット":
                        position_preset = st.selectbox(
                            "テロップ位置",
                            ["下部中央", "上部中央", "中央", "左下", "右下", "左上", "右上"],
                            key="position_select"
                        )
                        
                        position_map = {
                            "下部中央": ("(w-text_w)/2", "h-text_h-20"),
                            "上部中央": ("(w-text_w)/2", "20"),
                            "中央": ("(w-text_w)/2", "(h-text_h)/2"),
                            "左下": ("20", "h-text_h-20"),
                            "右下": ("w-text_w-20", "h-text_h-20"),
                            "左上": ("20", "20"),
                            "右上": ("w-text_w-20", "20")
                        }
                        x_pos, y_pos = position_map[position_preset]
                    else:
                        # カスタム位置設定
                        st.write("**カスタム位置設定**")
                        st.info("💡 座標は動画サイズに対する相対値です。(w=動画幅, h=動画高さ, text_w=テキスト幅, text_h=テキスト高さ)")
                        
                        col_x, col_y = st.columns(2)
                        
                        with col_x:
                            x_pos_type = st.selectbox(
                                "X位置の基準",
                                ["左端からの距離", "中央揃え", "右端からの距離", "カスタム式"],
                                key="x_pos_type"
                            )
                            
                            if x_pos_type == "左端からの距離":
                                x_offset = st.number_input("左端からのピクセル数", 0, 1000, 20, key="x_offset")
                                x_pos = str(x_offset)
                            elif x_pos_type == "中央揃え":
                                x_pos = "(w-text_w)/2"
                            elif x_pos_type == "右端からの距離":
                                x_offset = st.number_input("右端からのピクセル数", 0, 1000, 20, key="x_offset_right")
                                x_pos = f"w-text_w-{x_offset}"
                            else:
                                x_pos = st.text_input(
                                    "X位置の式",
                                    "(w-text_w)/2",
                                    key="x_pos_custom",
                                    help="例: (w-text_w)/2 (中央), 50 (左から50px), w-text_w-50 (右から50px)"
                                )
                        
                        with col_y:
                            y_pos_type = st.selectbox(
                                "Y位置の基準",
                                ["上端からの距離", "中央揃え", "下端からの距離", "カスタム式"],
                                key="y_pos_type"
                            )
                            
                            if y_pos_type == "上端からの距離":
                                y_offset = st.number_input("上端からのピクセル数", 0, 1000, 20, key="y_offset")
                                y_pos = str(y_offset)
                            elif y_pos_type == "中央揃え":
                                y_pos = "(h-text_h)/2"
                            elif y_pos_type == "下端からの距離":
                                y_offset = st.number_input("下端からのピクセル数", 0, 1000, 20, key="y_offset_bottom")
                                y_pos = f"h-text_h-{y_offset}"
                            else:
                                y_pos = st.text_input(
                                    "Y位置の式",
                                    "h-text_h-20",
                                    key="y_pos_custom",
                                    help="例: (h-text_h)/2 (中央), 50 (上から50px), h-text_h-50 (下から50px)"
                                )
                        
                        st.write(f"**現在の座標式**: X=`{x_pos}`, Y=`{y_pos}`")
                    
                    # リアルタイムプレビュー生成ボタン
                    if st.button("🔄 プレビューを更新", key="update_preview"):
                        if subtitle_text and selected_font:
                            with st.spinner("プレビューを生成中..."):
                                preview_with_subtitle_path = str(TEMP_VIDEOS_DIR / "preview_with_subtitle.mp4")
                                success = generate_final_video_with_subtitle(
                                    st.session_state.video_path,
                                    st.session_state.clip_start,
                                    st.session_state.clip_end,
                                    preview_with_subtitle_path,
                                    subtitle_text,
                                    selected_font,
                                    font_size,
                                    font_color,
                                    background_type,
                                    x_pos,
                                    y_pos
                                )
                                if success:
                                    st.session_state.preview_with_subtitle_path = preview_with_subtitle_path
                                    st.success("✅ プレビュー更新完了！")
                        else:
                            st.warning("テロップテキストを入力してください。")
                
                with col_preview:
                    # リアルタイムプレビュー表示（小さいサイズ）
                    st.subheader("🎬 プレビュー")
                    
                    # CSSで動画サイズを小さくする
                    st.markdown(
                        """
                        <style>
                        [data-testid="stVideo"] {
                            max-width: 400px !important;
                            margin: 0 auto;
                        }
                        [data-testid="stVideo"] video {
                            max-width: 100% !important;
                            height: auto !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    if 'preview_with_subtitle_path' in st.session_state:
                        st.video(st.session_state.preview_with_subtitle_path)
                        st.info("💡 左側の設定を変更したら「プレビューを更新」をクリックしてください")
                    else:
                        # 元のプレビュー動画を表示（テロップなし）
                        if 'preview_path' in st.session_state:
                            st.video(st.session_state.preview_path)
                            st.info("💡 テロップを入力して「プレビューを更新」をクリックすると、テロップ付きプレビューが表示されます")
                        else:
                            st.info("💡 まず「カット範囲指定」タブでプレビューを生成してください")
                
                # フォントアップロード
                st.subheader("➕ 新しいフォントを追加")
                uploaded_font = st.file_uploader(
                    "フォントファイル (.ttf, .otf)",
                    type=['ttf', 'otf'],
                    key="font_uploader"
                )
                
                if uploaded_font:
                    if st.button("フォントを追加"):
                        if save_uploaded_font(uploaded_font):
                            st.success(f"✅ フォント '{uploaded_font.name}' を追加しました!")
                            st.rerun()
                
                # 動画生成
                st.divider()
                st.subheader("🎬 最終動画生成")
                
                if st.button("🎬 テロップ付き動画を生成", type="primary"):
                    if not subtitle_text:
                        st.warning("テロップテキストを入力してください。")
                    elif not selected_font:
                        st.warning("フォントを選択してください。")
                    else:
                        with st.spinner("動画を生成中... (数分かかる場合があります)"):
                            output_path = str(TEMP_VIDEOS_DIR / "final_output.mp4")
                            
                            success = generate_final_video_with_subtitle(
                                st.session_state.video_path,
                                st.session_state.clip_start,
                                st.session_state.clip_end,
                                output_path,
                                subtitle_text,
                                selected_font,
                                font_size,
                                font_color,
                                background_type,
                                x_pos,
                                y_pos
                            )
                            
                            if success:
                                st.success("✅ 動画生成完了!")
                                st.video(output_path)
                                
                                # ダウンロードボタン
                                with open(output_path, 'rb') as f:
                                    st.download_button(
                                        label="📥 動画をダウンロード",
                                        data=f,
                                        file_name="context_cut_pro_output.mp4",
                                        mime="video/mp4"
                                    )
    
    else:
        st.info("👈 サイドバーから動画を取得し、文字起こしを実行してください。")
    
    # シーンプレビューのダイアログ（ポップアップ）
    @st.dialog("🎬 シーンプレビュー & 範囲調整", width="large")
    def show_scene_preview_dialog():
        if 'current_scene_preview_path' in st.session_state:
            st.write(f"**シーン {st.session_state.preview_scene_id}**")
            
            if 'preview_scene_text' in st.session_state:
                st.info(f"💬 {st.session_state.preview_scene_text}")
            
            # 範囲調整スライダー
            st.subheader("🎯 範囲調整")
            
            # 初期値を取得
            if 'dialog_adjusted_start' not in st.session_state:
                st.session_state.dialog_adjusted_start = st.session_state.preview_scene_start
            if 'dialog_adjusted_end' not in st.session_state:
                st.session_state.dialog_adjusted_end = st.session_state.preview_scene_end
            
            # 動画の全体長さを取得
            video_duration = st.session_state.get('video_duration', 100.0)
            
            # 範囲調整スライダー
            time_range = st.slider(
                "開始・終了時間を調整",
                0.0,
                video_duration,
                (st.session_state.dialog_adjusted_start, st.session_state.dialog_adjusted_end),
                step=0.1,
                key="dialog_time_slider"
            )
            
            adjusted_start, adjusted_end = time_range
            
            # 調整後の時間を表示
            col_time1, col_time2, col_time3 = st.columns(3)
            with col_time1:
                st.metric("開始", f"{adjusted_start:.2f}秒")
            with col_time2:
                st.metric("終了", f"{adjusted_end:.2f}秒")
            with col_time3:
                st.metric("長さ", f"{adjusted_end - adjusted_start:.2f}秒")
            
            # 範囲が変更されたらプレビューを更新
            if (adjusted_start != st.session_state.dialog_adjusted_start or 
                adjusted_end != st.session_state.dialog_adjusted_end):
                
                if st.button("🔄 この範囲でプレビューを更新", use_container_width=True):
                    with st.spinner("プレビューを生成中..."):
                        preview_path = str(TEMP_VIDEOS_DIR / f"scene_preview_{st.session_state.preview_scene_id}_adjusted.mp4")
                        if create_preview_clip(
                            st.session_state.video_path,
                            adjusted_start,
                            adjusted_end,
                            preview_path
                        ):
                            st.session_state.current_scene_preview_path = preview_path
                            st.session_state.dialog_adjusted_start = adjusted_start
                            st.session_state.dialog_adjusted_end = adjusted_end
                            st.rerun()
            
            # プレビュー動画を表示
            st.subheader("📹 プレビュー")
            st.video(st.session_state.current_scene_preview_path, loop=True)
            
            # ボタン
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✖️ 閉じる", use_container_width=True, key="close_dialog"):
                    st.session_state.scene_preview_dialog_open = False
                    # 調整値をリセット
                    if 'dialog_adjusted_start' in st.session_state:
                        del st.session_state.dialog_adjusted_start
                    if 'dialog_adjusted_end' in st.session_state:
                        del st.session_state.dialog_adjusted_end
                    st.rerun()
            with col2:
                if st.button("✅ この範囲で選択", use_container_width=True, key="select_from_dialog"):
                    # 調整後の値を選択
                    st.session_state.selected_start = st.session_state.dialog_adjusted_start
                    st.session_state.selected_end = st.session_state.dialog_adjusted_end
                    st.session_state.scene_preview_dialog_open = False
                    st.session_state.scene_selected = True
                    # 調整値をリセット
                    if 'dialog_adjusted_start' in st.session_state:
                        del st.session_state.dialog_adjusted_start
                    if 'dialog_adjusted_end' in st.session_state:
                        del st.session_state.dialog_adjusted_end
                    st.rerun()
    
    # ダイアログを表示
    if st.session_state.get('scene_preview_dialog_open', False):
        show_scene_preview_dialog()
    
    # フッター
    st.markdown("---")
    st.markdown("**Context Cut Pro** - Powered by Streamlit, Whisper, ChromaDB, FFmpeg")


if __name__ == "__main__":
    main()
