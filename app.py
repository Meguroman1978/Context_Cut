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

# 日本語フォントライブラリ（Google Fonts - 商用利用可能）
JAPANESE_FONTS = {
    "Noto Sans JP": "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf",
    "Noto Serif JP": "https://github.com/google/fonts/raw/main/ofl/notoserifjp/NotoSerifJP%5Bwght%5D.ttf",
    "M PLUS 1p": "https://github.com/google/fonts/raw/main/ofl/mplus1p/MPLUS1p-Regular.ttf",
    "M PLUS Rounded 1c": "https://github.com/google/fonts/raw/main/ofl/mplusrounded1c/MPLUSRounded1c-Regular.ttf",
    "Zen Kaku Gothic New": "https://github.com/google/fonts/raw/main/ofl/zenkakugothicnew/ZenKakuGothicNew-Regular.ttf",
    "Zen Maru Gothic": "https://github.com/google/fonts/raw/main/ofl/zenmarugothic/ZenMaruGothic-Regular.ttf",
    "Kosugi Maru": "https://github.com/google/fonts/raw/main/apache/kosugimaru/KosugiMaru-Regular.ttf",
    "Kosugi": "https://github.com/google/fonts/raw/main/apache/kosugi/Kosugi-Regular.ttf",
    "Sawarabi Gothic": "https://github.com/google/fonts/raw/main/ofl/sawarabigothic/SawarabiGothic-Regular.ttf",
    "Sawarabi Mincho": "https://github.com/google/fonts/raw/main/ofl/sawarabimincho/SawarabiMincho-Regular.ttf",
    "Hachi Maru Pop": "https://github.com/google/fonts/raw/main/ofl/hachimarupop/HachiMaruPop-Regular.ttf",
    "Yusei Magic": "https://github.com/google/fonts/raw/main/ofl/yuseimagic/YuseiMagic-Regular.ttf",
    "Reggae One": "https://github.com/google/fonts/raw/main/ofl/reggaeone/ReggaeOne-Regular.ttf",
    "Rampart One": "https://github.com/google/fonts/raw/main/ofl/rampartone/RampartOne-Regular.ttf",
    "Klee One": "https://github.com/google/fonts/raw/main/ofl/kleeone/KleeOne-Regular.ttf"
}

def download_japanese_fonts():
    """日本語フォントを一括ダウンロード"""
    import urllib.request
    import time
    
    downloaded_count = 0
    for font_name, font_url in JAPANESE_FONTS.items():
        font_filename = font_name.replace(" ", "_") + ".ttf"
        font_path = FONTS_DIR / font_filename
        
        if not font_path.exists():
            try:
                urllib.request.urlretrieve(font_url, str(font_path))
                downloaded_count += 1
                time.sleep(0.5)  # レート制限対策
            except Exception as e:
                print(f"フォント {font_name} のダウンロード失敗: {e}")
    
    return downloaded_count

# 初回起動時にフォントをダウンロード
if not (FONTS_DIR / "Noto_Sans_JP.ttf").exists():
    print("日本語フォントを初期化中...")
    downloaded = download_japanese_fonts()
    print(f"{downloaded}個のフォントをダウンロードしました")

DEFAULT_FONT = FONTS_DIR / "Noto_Sans_JP.ttf"

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


def get_japanese_fonts_dict() -> Dict[str, str]:
    """日本語フォント名とファイル名のマッピングを取得"""
    fonts_dict = {}
    for font_name in JAPANESE_FONTS.keys():
        font_filename = font_name.replace(" ", "_") + ".ttf"
        font_path = FONTS_DIR / font_filename
        if font_path.exists():
            fonts_dict[font_name] = font_filename
    return fonts_dict


def generate_font_preview(font_path: str, text: str = "あいうえお ABC 123", size: int = 36) -> 'Image':
    """フォントのプレビュー画像を生成"""
    from PIL import Image, ImageDraw, ImageFont
    
    try:
        # プレビュー画像を作成
        img = Image.new('RGB', (500, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # フォントを読み込み
        font = ImageFont.truetype(str(font_path), size)
        
        # テキストを描画
        draw.text((10, 30), text, font=font, fill='black')
        
        return img
    except Exception as e:
        # エラー時は空の画像を返す
        img = Image.new('RGB', (500, 100), color='lightgray')
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), f"プレビュー生成失敗: {e}", fill='red')
        return img


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
        st.info(f"🔄 Whisperモデル（{model_name}）をロード中... 初回は数分かかります。")
        model = whisper.load_model(model_name)
        st.success(f"✅ Whisperモデル（{model_name}）のロードが完了しました！")
        return model
    except Exception as e:
        st.error(f"❌ Whisperモデルのロードに失敗しました: {e}")
        return None


def check_video_has_audio(video_path: str) -> bool:
    """動画に音声トラックがあるかチェック"""
    try:
        probe = ffmpeg.probe(video_path)
        audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
        
        if len(audio_streams) > 0:
            # デバッグ情報を表示
            for i, stream in enumerate(audio_streams):
                codec = stream.get('codec_name', 'unknown')
                sample_rate = stream.get('sample_rate', 'unknown')
                channels = stream.get('channels', 'unknown')
                duration = stream.get('duration', 'unknown')
                st.info(f"🔍 音声トラック {i}: コーデック={codec}, サンプリングレート={sample_rate}Hz, チャンネル={channels}, 長さ={duration}秒")
            return True
        else:
            return False
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
        
        # 処理時間の目安を表示
        if duration > 600:  # 10分以上
            st.warning(f"⚠️ 動画が長いです（{duration/60:.1f}分）。処理に10分以上かかる可能性があります。")
            st.info("💡 **推奨**: 動画を短く切り取るか、tinyモデルを使用してください。")
        elif duration > 300:  # 5分以上
            st.info(f"🎤 動画を文字起こし中... （動画の長さ: {duration/60:.1f}分、5-10分程度かかります）")
        else:
            st.info(f"🎤 動画を文字起こし中... （動画の長さ: {duration:.1f}秒、1-3分程度かかります）")
        
        # 一時的な音声ファイルを作成（Whisperが処理しやすい形式に変換）
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name
        
        try:
            # FFmpegで音声を抽出してWAV形式に変換
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("⏳ ステップ 1/3: FFmpegで音声を抽出中...")
                progress_bar.progress(10)
                
                (
                    ffmpeg
                    .input(video_path)
                    .output(
                        tmp_audio_path,
                        acodec='pcm_s16le',  # PCM 16-bit
                        ac=1,                 # モノラル
                        ar='16000',          # 16kHz サンプリングレート
                        **{'map': '0:a:0'}   # 最初の音声ストリームを明示的に選択
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                progress_bar.progress(30)
                status_text.text("✅ 音声抽出完了！")
                
            except ffmpeg.Error as e:
                progress_bar.empty()
                status_text.empty()
                stderr_output = e.stderr.decode('utf-8') if e.stderr else 'エラー情報なし'
                st.error(f"❌ FFmpegでの音声抽出に失敗しました。")
                st.error(f"**FFmpegエラー詳細**:\n```\n{stderr_output}\n```")
                if os.path.exists(tmp_audio_path):
                    os.unlink(tmp_audio_path)
                return None
            
            # 音声ファイルのサイズチェック
            import os
            status_text.text("⏳ ステップ 2/3: 音声ファイルを検証中...")
            progress_bar.progress(40)
            
            if not os.path.exists(tmp_audio_path):
                progress_bar.empty()
                status_text.empty()
                st.error("❌ 音声ファイルが作成されませんでした。")
                return None
            
            audio_size = os.path.getsize(tmp_audio_path)
            audio_size_mb = audio_size / (1024 * 1024)
            st.info(f"🔍 抽出された音声: {audio_size:,} bytes ({audio_size_mb:.2f} MB)")
            
            if audio_size < 1000:  # 1KB未満
                progress_bar.empty()
                status_text.empty()
                st.error("❌ 抽出された音声データが小さすぎます。音声が含まれていない可能性があります。")
                st.info(f"💡 音声ファイルサイズ: {audio_size} bytes（最低1,000 bytes必要）")
                os.unlink(tmp_audio_path)
                return None
            
            # 大きなファイルの警告
            if audio_size_mb > 100:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ 音声ファイルが大きすぎます（{audio_size_mb:.1f} MB）。")
                st.error("**Streamlit Community Cloudの制限により、100MB以上の音声は処理できません。**")
                st.info("""
                💡 **対処方法**:
                1. 動画を短く切り取る（5分以内推奨）
                2. より軽量なモデル（tiny）を使用する
                3. 動画の音声ビットレートを下げる
                """)
                os.unlink(tmp_audio_path)
                return None
            elif audio_size_mb > 50:
                st.warning(f"⚠️ 音声ファイルが大きいです（{audio_size_mb:.1f} MB）。処理に5-10分以上かかる可能性があります。")
                st.info("💡 長い動画の場合は、tinyモデルの使用または事前に短く切り取ることをおすすめします。")
            
            # Whisperで文字起こし実行
            progress_bar.progress(50)
            status_text.text("⏳ ステップ 3/3: Whisperで音声認識中（これには数分かかります）...")
            
            import time
            start_time = time.time()
            
            try:
                result = model.transcribe(
                    tmp_audio_path, 
                    language='ja', 
                    verbose=False,
                    fp16=False,  # CPU互換性のため
                    temperature=0.0,  # より安定した結果を得る
                    condition_on_previous_text=False  # エラー回避
                )
                
                elapsed_time = time.time() - start_time
                progress_bar.progress(100)
                status_text.text(f"✅ 音声認識完了！（処理時間: {elapsed_time:.1f}秒）")
                
            except Exception as whisper_error:
                progress_bar.empty()
                status_text.empty()
                elapsed_time = time.time() - start_time
                st.error(f"❌ Whisperでの音声認識に失敗しました（{elapsed_time:.1f}秒後）: {whisper_error}")
                if os.path.exists(tmp_audio_path):
                    os.unlink(tmp_audio_path)
                raise whisper_error
            
            # 一時ファイルを削除
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)
            
        except ffmpeg.Error as e:
            # FFmpegエラーは既に上で処理済み
            return None
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
        error_type = type(e).__name__
        
        st.error(f"❌ 文字起こし処理中にエラーが発生しました（{error_type}）")
        st.error(f"**エラー詳細**: {error_msg}")
        
        if "cannot reshape tensor" in error_msg:
            st.info("""
            💡 **考えられる原因**: Whisperが音声データを処理できませんでした。
            
            **対処方法**:
            1. 動画に音声トラックが正しく含まれているか確認
            2. 別の動画形式（MP4, MOV, MKV）で試す
            3. 音声を再エンコードして修復:
               ```bash
               ffmpeg -i input.mp4 -c:v copy -c:a aac -b:a 128k output.mp4
               ```
            4. または、動画編集機能のみ使用する
            """)
        elif "ffmpeg" in error_msg.lower() or isinstance(e, ffmpeg.Error):
            st.info("""
            💡 **考えられる原因**: FFmpegでの音声抽出に失敗しました。
            
            **対処方法**:
            1. 動画ファイルが破損していないか確認
            2. 動画形式を変換してみる（MP4が最も安定）
            3. 動画プロパティで音声コーデックを確認（AAC, MP3推奨）
            """)
        else:
            st.info("""
            💡 **対処方法**:
            - 動画ファイルが破損していないか確認
            - 別の動画で試す
            - ファイルサイズが大きすぎる場合は短い動画で試す
            """)
        
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


def generate_search_suggestions(transcript_text: str, max_suggestions: int = 10) -> List[str]:
    """文字起こしテキストから検索クエリ候補を生成"""
    suggestions = []
    
    # 優先度の高い定型クエリ候補リスト
    priority_queries = [
        "商品の特徴について説明している箇所",
        "デザインについて説明をしている箇所",
        "使用方法について説明をしている箇所",
        "メンテナンス方法について説明をしている箇所",
        "保証について説明をしている箇所",
        "味・風味について説明している箇所",
        "色味について説明している箇所",
        "香りについて説明している箇所",
        "肌触り・テクスチャーについて説明している箇所",
        "着心地・フィット感について説明している箇所",
        "使いやすさについて説明している箇所",
        "携帯性（持ち運びやすさ）について説明している箇所",
        "静粛性・打鍵感について説明している箇所",
        "視認性（画面の明るさ、文字の見やすさ）について説明している箇所",
        "サイズ・寸法について説明している箇所",
        "重量について説明している箇所",
        "原材料・素材について説明している箇所",
        "成分・添加物について説明している箇所",
        "アレルギー物質について説明している箇所",
        "原産国・製造国について説明している箇所",
        "カラーバリエーションについて説明している箇所",
        "付属品・同梱物について説明している箇所",
        "製造年月日・消費期限について説明している箇所",
        "スペック・性能について説明している箇所",
        "耐久性・寿命について説明している箇所",
        "防水・防塵性能について説明している箇所",
        "静音性について説明している箇所",
        "省エネ性能・消費電力について説明している箇所",
        "認証・取得規格について説明している箇所",
        "互換性について説明している箇所",
        "動作環境について説明している箇所",
        "通信方式について説明している箇所",
        "処理速度について説明している箇所",
        "安全上の注意・警告について説明している箇所",
        "使用禁止事項について説明している箇所",
        "対象年齢について説明している箇所",
        "副作用・リスクについて説明している箇所",
        "免責事項（責任の範囲）について説明している箇所",
        "法的遵守事項について説明している箇所",
        "廃棄・リサイクル方法について説明している箇所",
        "開発ストーリー・コンセプトについて説明している箇所",
        "生産者・製造工程について説明している箇所",
        "サステナビリティ・環境配慮について説明している箇所",
        "受賞歴・メディア掲載について説明している箇所",
        "ターゲット層（こんな方におすすめ）について説明している箇所",
        "監修者・専門家のコメントについて説明している箇所",
        "組み立て・設置方法について説明している箇所",
        "初期設定（セットアップ）について説明している箇所",
        "トラブルシューティング（Q&A）について説明している箇所",
        "アップデート・更新について説明している箇所",
        "修理・交換対応について説明している箇所",
        "消耗品の購入・補充について説明している箇所",
        "返品・キャンセルポリシーについて説明している箇所",
        "配送・納期について説明している箇所",
        "カスタマーサポート窓口について説明している箇所"
    ]
    
    # キーワードマッピング（優先クエリとの関連性チェック用）
    keyword_patterns = {
        "商品": "商品の特徴について説明している箇所",
        "特徴": "商品の特徴について説明している箇所",
        "デザイン": "デザインについて説明をしている箇所",
        "使い方": "使用方法について説明をしている箇所",
        "使用方法": "使用方法について説明をしている箇所",
        "メンテナンス": "メンテナンス方法について説明をしている箇所",
        "手入れ": "メンテナンス方法について説明をしている箇所",
        "保証": "保証について説明をしている箇所",
        "味": "味・風味について説明している箇所",
        "風味": "味・風味について説明している箇所",
        "色": "色味について説明している箇所",
        "香り": "香りについて説明している箇所",
        "肌触り": "肌触り・テクスチャーについて説明している箇所",
        "テクスチャー": "肌触り・テクスチャーについて説明している箇所",
        "着心地": "着心地・フィット感について説明している箇所",
        "フィット": "着心地・フィット感について説明している箇所",
        "使いやすさ": "使いやすさについて説明している箇所",
        "携帯": "携帯性（持ち運びやすさ）について説明している箇所",
        "持ち運び": "携帯性（持ち運びやすさ）について説明している箇所",
        "サイズ": "サイズ・寸法について説明している箇所",
        "寸法": "サイズ・寸法について説明している箇所",
        "重量": "重量について説明している箇所",
        "重さ": "重量について説明している箇所",
        "原材料": "原材料・素材について説明している箇所",
        "素材": "原材料・素材について説明している箇所",
        "成分": "成分・添加物について説明している箇所",
        "添加物": "成分・添加物について説明している箇所",
        "アレルギー": "アレルギー物質について説明している箇所",
        "原産": "原産国・製造国について説明している箇所",
        "製造": "原産国・製造国について説明している箇所",
        "カラー": "カラーバリエーションについて説明している箇所",
        "色": "カラーバリエーションについて説明している箇所",
        "付属": "付属品・同梱物について説明している箇所",
        "同梱": "付属品・同梱物について説明している箇所",
        "消費期限": "製造年月日・消費期限について説明している箇所",
        "スペック": "スペック・性能について説明している箇所",
        "性能": "スペック・性能について説明している箇所",
        "耐久": "耐久性・寿命について説明している箇所",
        "寿命": "耐久性・寿命について説明している箇所",
        "防水": "防水・防塵性能について説明している箇所",
        "防塵": "防水・防塵性能について説明している箇所",
        "静音": "静音性について説明している箇所",
        "省エネ": "省エネ性能・消費電力について説明している箇所",
        "消費電力": "省エネ性能・消費電力について説明している箇所",
        "注意": "安全上の注意・警告について説明している箇所",
        "警告": "安全上の注意・警告について説明している箇所",
        "禁止": "使用禁止事項について説明している箇所",
        "年齢": "対象年齢について説明している箇所",
        "副作用": "副作用・リスクについて説明している箇所",
        "リスク": "副作用・リスクについて説明している箇所",
        "廃棄": "廃棄・リサイクル方法について説明している箇所",
        "リサイクル": "廃棄・リサイクル方法について説明している箇所",
        "ストーリー": "開発ストーリー・コンセプトについて説明している箇所",
        "コンセプト": "開発ストーリー・コンセプトについて説明している箇所",
        "組み立て": "組み立て・設置方法について説明している箇所",
        "設置": "組み立て・設置方法について説明している箇所",
        "設定": "初期設定（セットアップ）について説明している箇所",
        "セットアップ": "初期設定（セットアップ）について説明している箇所",
        "トラブル": "トラブルシューティング（Q&A）について説明している箇所",
        "修理": "修理・交換対応について説明している箇所",
        "交換": "修理・交換対応について説明している箇所",
        "返品": "返品・キャンセルポリシーについて説明している箇所",
        "キャンセル": "返品・キャンセルポリシーについて説明している箇所",
        "配送": "配送・納期について説明している箇所",
        "納期": "配送・納期について説明している箇所",
        "サポート": "カスタマーサポート窓口について説明している箇所",
        "問い合わせ": "カスタマーサポート窓口について説明している箇所",
        "料金": "料金について説明している箇所",
        "特徴": "特徴について説明している箇所",
        "機能": "機能について説明している箇所",
        "効果": "効果について説明している箇所",
        "注意": "注意点について説明している箇所",
        "ポイント": "重要なポイントを説明している箇所",
        "コツ": "コツについて説明している箇所",
        "手順": "手順について説明している箇所",
        "方法": "方法について説明している箇所",
        "やり方": "やり方について説明している箇所",
        "問題": "問題について説明している箇所",
        "解決": "解決方法について説明している箇所",
        "比較": "比較している箇所",
        "違い": "違いについて説明している箇所",
        "おすすめ": "おすすめについて説明している箇所",
        "メリット": "メリットについて説明している箇所",
        "デメリット": "デメリットについて説明している箇所",
    }
    
    # 文字起こしテキストから関連するキーワードを検出
    text_lower = transcript_text.lower()
    matched_queries = []
    
    # キーワードパターンに基づいて優先クエリを抽出
    for keyword, query in keyword_patterns.items():
        if keyword in text_lower and query not in matched_queries:
            matched_queries.append(query)
    
    # マッチしたクエリが少ない場合、汎用候補を追加
    if len(matched_queries) < 3:
        generic_suggestions = [
            "重要な説明をしている箇所",
            "詳しく説明している箇所",
            "具体例を挙げている箇所",
            "まとめている箇所",
            "強調している箇所"
        ]
        for gen_sug in generic_suggestions:
            if gen_sug not in matched_queries:
                matched_queries.append(gen_sug)
                if len(matched_queries) >= max_suggestions:
                    break
    
    # 最大数に制限
    return matched_queries[:max_suggestions]


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


def extract_video_thumbnail(video_path: str, time: float = 0.0) -> Optional['Image']:
    """動画から指定時間のサムネイル画像を抽出"""
    from PIL import Image
    import tempfile
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # FFmpegでフレームを抽出
        (
            ffmpeg
            .input(video_path, ss=time)
            .output(tmp_path, vframes=1, format='image2', vcodec='mjpeg')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        
        # 画像を読み込み
        img = Image.open(tmp_path)
        
        # リサイズ（600px幅に）
        aspect_ratio = img.height / img.width
        new_width = 600
        new_height = int(new_width * aspect_ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 一時ファイル削除
        import os
        os.unlink(tmp_path)
        
        return img
    except Exception as e:
        st.error(f"サムネイル抽出に失敗: {e}")
        return None


def get_background_settings(background_type: str):
    """背景タイプから設定を取得
    
    Returns:
        dict: 'mode' (simple/balloon), 'balloon_image' (画像パス or None), 'box', 'boxcolor', 'boxborderw'
    """
    # シンプル背景
    simple_backgrounds = {
        "なし（透明）": {'mode': 'simple', 'balloon_image': None, 'box': 0, 'boxcolor': "black@0.0", 'boxborderw': 0},
        "黒（半透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "black@0.5", 'boxborderw': 5},
        "白（半透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "white@0.8", 'boxborderw': 5},
        "黒（不透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "black@1.0", 'boxborderw': 5},
        "白（不透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "white@1.0", 'boxborderw': 5},
        "黄色（半透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "yellow@0.7", 'boxborderw': 5},
        "青（半透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "blue@0.7", 'boxborderw': 5},
        "赤（半透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "red@0.7", 'boxborderw': 5},
        "緑（半透明）": {'mode': 'simple', 'balloon_image': None, 'box': 1, 'boxcolor': "green@0.7", 'boxborderw': 5},
    }
    
    # 吹き出し画像背景
    balloon_backgrounds = {
        "💬 楕円吹き出し（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/oval_white.png'},
        "💬 楕円吹き出し（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/oval_black.png'},
        "🗨️ 角丸長方形（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/round_rect_white.png'},
        "🗨️ 角丸長方形（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/round_rect_black.png'},
        "☁️ 雲形（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/cloud_white.png'},
        "☁️ 雲形（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/cloud_black.png'},
        "⭐ 放射線（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/star_white.png'},
        "⭐ 放射線（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/star_black.png'},
        "⬛ 角張り長方形（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/square_white.png'},
        "⬛ 角張り長方形（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/square_black.png'},
        "💭 考え事（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/thought_white.png'},
        "💭 考え事（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/thought_black.png'},
        "💢 叫び（白）": {'mode': 'balloon', 'balloon_image': 'balloon_images/scream_white.png'},
        "💢 叫び（黒）": {'mode': 'balloon', 'balloon_image': 'balloon_images/scream_black.png'},
        "💥 爆発（黄）": {'mode': 'balloon', 'balloon_image': 'balloon_images/explosion_yellow.png'},
        "💥 爆発（赤）": {'mode': 'balloon', 'balloon_image': 'balloon_images/explosion_red.png'},
        "💗 ハート（ピンク）": {'mode': 'balloon', 'balloon_image': 'balloon_images/heart_pink.png'},
        "🗨️ 角丸長方形（青）": {'mode': 'balloon', 'balloon_image': 'balloon_images/round_rect_blue.png'},
        "🗨️ 角丸長方形（緑）": {'mode': 'balloon', 'balloon_image': 'balloon_images/round_rect_green.png'},
    }
    
    # 該当する背景を検索
    if background_type == "custom":
        # カスタム背景画像モード
        return {'mode': 'custom', 'balloon_image': None, 'box': 0, 'boxcolor': "black@0.0", 'boxborderw': 0}
    elif background_type.startswith("カスタム（"):
        # カスタム色の背景
        # 例: "カスタム（#FF5733）半透明" or "カスタム（#FF5733）不透明"
        import re
        color_match = re.search(r'#[0-9A-Fa-f]{6}', background_type)
        if color_match:
            color_hex = color_match.group()
            opacity = 0.7 if "半透明" in background_type else 1.0
            return {
                'mode': 'simple',
                'balloon_image': None,
                'box': 1,
                'boxcolor': f"{color_hex}@{opacity}",
                'boxborderw': 5
            }
        else:
            return {'mode': 'simple', 'balloon_image': None, 'box': 0, 'boxcolor': "black@0.0", 'boxborderw': 0}
    elif background_type in simple_backgrounds:
        return simple_backgrounds[background_type]
    elif background_type in balloon_backgrounds:
        return balloon_backgrounds[background_type]
    else:
        # デフォルト
        return {'mode': 'simple', 'balloon_image': None, 'box': 0, 'boxcolor': "black@0.0", 'boxborderw': 0}


def generate_professional_video(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    layers: List[Dict],
    effects: Dict,
    audio_settings: Dict
) -> bool:
    """プロフェッショナル動画編集（Phase 1-5統合版）"""
    try:
        import streamlit as st
        
        # 入力動画
        input_stream = ffmpeg.input(video_path, ss=start_time, to=end_time)
        video_stream = input_stream.video
        audio_stream = input_stream.audio
        
        # Phase 3: エフェクト適用
        speed = effects.get('speed', 1.0)
        brightness = effects.get('brightness', 0.0)
        contrast = effects.get('contrast', 1.0)
        saturation = effects.get('saturation', 1.0)
        
        # 速度調整
        if speed != 1.0:
            video_stream = video_stream.filter('setpts', f'{1/speed}*PTS')
            if speed <= 2.0:  # 2倍速以下の場合のみ音声も調整
                audio_stream = audio_stream.filter('atempo', speed)
        
        # カラーフィルター
        if brightness != 0.0 or contrast != 1.0 or saturation != 1.0:
            video_stream = video_stream.filter('eq', brightness=brightness, contrast=contrast, saturation=saturation)
        
        # Phase 2: ステッカー・画像オーバーレイ
        sticker_layers = [l for l in layers if l['type'] == 'sticker']
        for sticker in sticker_layers:
            sticker_path = str(Path(sticker['path']).absolute()).replace("\\", "/")
            sticker_stream = ffmpeg.input(sticker_path, loop=1, t=end_time - start_time)
            
            # スケール調整
            scale = sticker.get('scale', 1.0)
            if scale != 1.0:
                sticker_stream = sticker_stream.filter('scale', f'iw*{scale}', f'ih*{scale}')
            
            # アニメーション適用
            animation = sticker.get('animation', 'none')
            overlay_x = sticker['x']
            overlay_y = sticker['y']
            enable_expr = f"between(t,{sticker['start']},{sticker['end']})"
            
            # Phase 5: アニメーション
            if animation == 'fade_in':
                sticker_stream = sticker_stream.filter('fade', type='in', start_time=0, duration=0.5)
            elif animation == 'fade_out':
                duration = sticker['end'] - sticker['start']
                sticker_stream = sticker_stream.filter('fade', type='out', start_time=max(0, duration - 0.5), duration=0.5)
            elif animation == 'fade_in_out':
                duration = sticker['end'] - sticker['start']
                sticker_stream = sticker_stream.filter('fade', type='in', start_time=0, duration=0.5)
                sticker_stream = sticker_stream.filter('fade', type='out', start_time=max(0, duration - 0.5), duration=0.5)
            elif animation == 'slide_in_left':
                overlay_x = f"if(lt(t-{sticker['start']},0.5),-w+(t-{sticker['start']})*w/0.5,{overlay_x})"
            elif animation == 'slide_in_right':
                overlay_x = f"if(lt(t-{sticker['start']},0.5),main_w-(t-{sticker['start']})*w/0.5,{overlay_x})"
            elif animation == 'slide_in_top':
                overlay_y = f"if(lt(t-{sticker['start']},0.5),-h+(t-{sticker['start']})*h/0.5,{overlay_y})"
            elif animation == 'slide_in_bottom':
                overlay_y = f"if(lt(t-{sticker['start']},0.5),main_h-(t-{sticker['start']})*h/0.5,{overlay_y})"
            
            video_stream = video_stream.overlay(
                sticker_stream,
                x=overlay_x,
                y=overlay_y,
                enable=enable_expr,
                format='auto'
            )
        
        # Phase 1: テキストレイヤー
        text_layers = [l for l in layers if l['type'] == 'text']
        for text_layer in text_layers:
            # フォントパス（レイヤーに指定されたフォントを使用）
            font_file = text_layer.get('font_file', 'Noto_Sans_JP.ttf')
            font_path = str(FONTS_DIR / font_file).replace("\\", "/")
            
            # テキストのエスケープ
            escaped_text = text_layer['content'].replace("\\", "\\\\\\\\")
            escaped_text = escaped_text.replace("'", "'\\\\''")
            escaped_text = escaped_text.replace(":", "\\:")
            escaped_text = escaped_text.replace("\n", " ")
            
            # アニメーション適用
            animation = text_layer.get('animation', 'none')
            text_x = text_layer['x']
            text_y = text_layer['y']
            text_alpha = '1.0'
            
            # Phase 5: テキストアニメーション
            if animation == 'fade_in':
                # フェードイン: 最初の0.5秒で透明度を0→1
                text_alpha = f"if(lt(t-{text_layer['start']},0.5),(t-{text_layer['start']})/0.5,1)"
            elif animation == 'fade_out':
                # フェードアウト: 最後の0.5秒で透明度を1→0
                duration = text_layer['end'] - text_layer['start']
                text_alpha = f"if(gt(t-{text_layer['start']},{duration-0.5}),1-((t-{text_layer['start']})-{duration-0.5})/0.5,1)"
            elif animation == 'fade_in_out':
                duration = text_layer['end'] - text_layer['start']
                text_alpha = f"if(lt(t-{text_layer['start']},0.5),(t-{text_layer['start']})/0.5,if(gt(t-{text_layer['start']},{duration-0.5}),1-((t-{text_layer['start']})-{duration-0.5})/0.5,1))"
            elif animation == 'slide_in_left':
                text_x = f"if(lt(t-{text_layer['start']},0.5),-text_w+(t-{text_layer['start']})*text_w/0.5,{text_x})"
            elif animation == 'slide_in_right':
                text_x = f"if(lt(t-{text_layer['start']},0.5),w-(t-{text_layer['start']})*text_w/0.5,{text_x})"
            elif animation == 'slide_in_top':
                text_y = f"if(lt(t-{text_layer['start']},0.5),-text_h+(t-{text_layer['start']})*text_h/0.5,{text_y})"
            elif animation == 'slide_in_bottom':
                text_y = f"if(lt(t-{text_layer['start']},0.5),h-(t-{text_layer['start']})*text_h/0.5,{text_y})"
            
            enable_expr = f"between(t,{text_layer['start']},{text_layer['end']})"
            
            video_stream = video_stream.filter(
                'drawtext',
                text=escaped_text,
                fontfile=font_path,
                fontsize=text_layer['font_size'],
                fontcolor=text_layer['color'],
                x=text_x,
                y=text_y,
                alpha=text_alpha,
                enable=enable_expr
            )
        
        # Phase 4: オーディオミキシング
        bgm_path = audio_settings.get('bgm_path')
        if bgm_path and Path(bgm_path).exists():
            # BGMを読み込み
            bgm_stream = ffmpeg.input(bgm_path).audio
            
            # 音量調整
            original_volume = audio_settings.get('original_volume', 1.0)
            bgm_volume = audio_settings.get('bgm_volume', 0.5)
            
            audio_stream = audio_stream.filter('volume', original_volume)
            bgm_stream = bgm_stream.filter('volume', bgm_volume)
            
            # BGMを動画の長さに合わせてループ
            video_duration = end_time - start_time
            bgm_stream = bgm_stream.filter('aloop', loop=-1, size=int(video_duration * 44100))
            
            # 2つの音声をミックス
            audio_stream = ffmpeg.filter([audio_stream, bgm_stream], 'amix', inputs=2, duration='first')
        
        # 出力
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
        st.error(f"❌ プロフェッショナル動画生成に失敗しました: FFmpegエラー")
        stderr_output = e.stderr.decode('utf-8') if e.stderr else "詳細なし"
        st.error(f"詳細: {stderr_output}")
        return False
    except Exception as e:
        st.error(f"❌ プロフェッショナル動画生成に失敗しました: {e}")
        return False


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
    y_position: str = "h-text_h-20",
    auto_position: bool = True,
    auto_size: bool = False
) -> bool:
    """テロップ付き最終動画を生成（吹き出し画像対応）"""
    try:
        # フォントパスの取得（Windowsパスを/に変換）
        font_path = str(FONTS_DIR / font_file).replace("\\", "/")
        
        # テキストのエスケープ処理（FFmpegのdrawtextフィルタ用）
        escaped_text = subtitle_text.replace("\\", "\\\\\\\\")
        escaped_text = escaped_text.replace("'", "'\\\\''")  
        escaped_text = escaped_text.replace(":", "\\:")
        escaped_text = escaped_text.replace("\n", " ")
        
        # 背景設定を取得
        bg_settings = get_background_settings(background_type)
        
        # FFmpegコマンドの実行
        input_stream = ffmpeg.input(video_path, ss=start_time, to=end_time)
        video_stream = input_stream.video
        
        # カスタム背景画像モードの場合
        if bg_settings['mode'] == 'custom':
            # セッションステートからカスタム背景情報を取得
            import streamlit as st
            custom_bg_path = st.session_state.get('custom_bg_path')
            bg_scale = st.session_state.get('bg_scale', 1.0)
            # テロップ編集で設定された位置を優先使用
            bg_x_pos = st.session_state.get('telop_bg_x_pos', st.session_state.get('bg_x_pos', '(main_w-overlay_w)/2'))
            bg_y_pos = st.session_state.get('telop_bg_y_pos', st.session_state.get('bg_y_pos', 'main_h-overlay_h-80'))
            text_scale = st.session_state.get('text_scale', 1.0)
            
            if custom_bg_path and Path(custom_bg_path).exists():
                custom_bg_path = str(Path(custom_bg_path).absolute()).replace("\\", "/")
                
                # カスタム背景画像を読み込み、スケール調整
                bg_stream = ffmpeg.input(custom_bg_path)
                if bg_scale != 1.0:
                    bg_stream = bg_stream.filter('scale', f'iw*{bg_scale}', f'ih*{bg_scale}')
                
                # 背景画像を動画に重ねる
                video_stream = video_stream.overlay(
                    bg_stream,
                    x=bg_x_pos,
                    y=bg_y_pos,
                    format='auto'
                )
                
                # テキストスケールを適用したフォントサイズ
                adjusted_font_size = int(font_size * text_scale)
                
                # テキストを描画（ユーザー指定の位置）
                video_stream = video_stream.filter(
                    'drawtext',
                    text=escaped_text,
                    fontfile=font_path,
                    fontsize=adjusted_font_size,
                    fontcolor=font_color,
                    x=x_position,
                    y=y_position
                )
            else:
                # カスタム背景が見つからない場合は透明背景として処理
                adjusted_font_size = int(font_size * st.session_state.get('text_scale', 1.0))
                video_stream = video_stream.filter(
                    'drawtext',
                    text=escaped_text,
                    fontfile=font_path,
                    fontsize=adjusted_font_size,
                    fontcolor=font_color,
                    x=x_position,
                    y=y_position
                )
        
        # 吹き出し画像モードの場合
        elif bg_settings['mode'] == 'balloon' and bg_settings['balloon_image']:
            balloon_path = str(Path(bg_settings['balloon_image']).absolute()).replace("\\", "/")
            
            # 吹き出し画像を読み込み
            balloon_stream = ffmpeg.input(balloon_path)
            
            # 吹き出しのスケール調整を適用
            import streamlit as st
            balloon_scale = st.session_state.get('balloon_scale', 1.0)
            if balloon_scale != 1.0:
                balloon_stream = balloon_stream.filter('scale', f'iw*{balloon_scale}', f'ih*{balloon_scale}')
            
            # 背景位置をセッションステートから取得（ユーザー選択を反映）
            balloon_x_pos = st.session_state.get('telop_bg_x_pos', '(main_w-overlay_w)/2')
            balloon_y_pos = st.session_state.get('telop_bg_y_pos', 'main_h-overlay_h-80')
            
            # 吹き出し画像を動画に重ねる（ユーザー指定位置）
            video_stream = video_stream.overlay(
                balloon_stream,
                x=balloon_x_pos,
                y=balloon_y_pos,
                format='auto'
            )
            
            # 自動位置調整が有効の場合、吹き出しの中央にテキストを配置
            if auto_position:
                # 吹き出しの位置名を取得（9分割グリッド）
                bg_position_name = st.session_state.get('telop_bg_position_name', '下中')
                
                # 吹き出し画像のサイズ（デフォルト400x400pxをスケール調整）
                balloon_width = int(400 * balloon_scale)
                balloon_height = int(400 * balloon_scale)
                balloon_half_w = balloon_width // 2
                balloon_half_h = balloon_height // 2
                
                # 位置名に基づいてテキストの中心座標を計算
                # overlay座標系 → drawtext座標系への変換
                text_position_map = {
                    "左上": (f'20+{balloon_half_w}-(text_w/2)', f'20+{balloon_half_h}-(text_h/2)'),
                    "上中": ('(w-text_w)/2', f'20+{balloon_half_h}-(text_h/2)'),
                    "右上": (f'w-20-{balloon_half_w}-(text_w/2)', f'20+{balloon_half_h}-(text_h/2)'),
                    "左中": (f'20+{balloon_half_w}-(text_w/2)', '(h-text_h)/2'),
                    "中央": ('(w-text_w)/2', '(h-text_h)/2'),
                    "右中": (f'w-20-{balloon_half_w}-(text_w/2)', '(h-text_h)/2'),
                    "左下": (f'20+{balloon_half_w}-(text_w/2)', f'h-20-{balloon_half_h}-(text_h/2)'),
                    "下中": ('(w-text_w)/2', f'h-80-{balloon_half_h}-(text_h/2)'),
                    "右下": (f'w-20-{balloon_half_w}-(text_w/2)', f'h-20-{balloon_half_h}-(text_h/2)')
                }
                
                text_x, text_y = text_position_map.get(bg_position_name, ('(w-text_w)/2', f'h-80-{balloon_half_h}-(text_h/2)'))
            else:
                text_x = x_position
                text_y = y_position
            
            # 自動サイズ調整が有効の場合、フォントサイズを調整
            if auto_size:
                adjusted_font_size = int(font_size * 0.65)  # 65%に縮小
            else:
                adjusted_font_size = font_size
            
            # テキストスケールも適用
            import streamlit as st
            text_scale = st.session_state.get('text_scale', 1.0)
            adjusted_font_size = int(adjusted_font_size * text_scale)
            
            # テキストを描画
            video_stream = video_stream.filter(
                'drawtext',
                text=escaped_text,
                fontfile=font_path,
                fontsize=adjusted_font_size,
                fontcolor=font_color,
                x=text_x,
                y=text_y
            )
        # シンプル背景モード
        else:
            # テキストスケールを適用
            import streamlit as st
            text_scale = st.session_state.get('text_scale', 1.0)
            adjusted_font_size = int(font_size * text_scale)
            
            if bg_settings['box'] > 0:
                video_stream = video_stream.filter(
                    'drawtext',
                    text=escaped_text,
                    fontfile=font_path,
                    fontsize=adjusted_font_size,
                    fontcolor=font_color,
                    x=x_position,
                    y=y_position,
                    box=bg_settings['box'],
                    boxcolor=bg_settings['boxcolor'],
                    boxborderw=bg_settings['boxborderw']
                )
            else:
                video_stream = video_stream.filter(
                    'drawtext',
                    text=escaped_text,
                    fontfile=font_path,
                    fontsize=adjusted_font_size,
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
            
            # モデル選択オプション
            st.write("**Whisperモデル選択**")
            model_choice = st.radio(
                "処理速度と精度のバランスを選択",
                ["🚀 高速（tiny）- 推奨", "⚖️ バランス（base）", "🎯 高精度（small）"],
                index=0,
                horizontal=True,
                help="tinyモデルは処理が高速ですが精度がやや低いです。長い動画や処理が重い場合はtinyを推奨します。"
            )
            
            # モデル名を取得
            if "高速" in model_choice:
                model_name = "tiny"
            elif "バランス" in model_choice:
                model_name = "base"
            else:
                model_name = "small"
            
            col_trans1, col_trans2 = st.columns(2)
            with col_trans1:
                if st.button("🎤 文字起こしを実行", use_container_width=True):
                    model = load_whisper_model(model_name)
                    if model:
                        transcription = transcribe_video(st.session_state.video_path, model)
                        if transcription:
                            st.session_state.transcription = transcription
                            st.session_state.video_duration = get_video_duration(st.session_state.video_path)
                            
                            # 文字起こしテキストを結合して保存（検索クエリ候補生成用）
                            transcript_segments = [seg['text'] for seg in transcription['segments']]
                            st.session_state.transcript_text = ' '.join(transcript_segments)
                            
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
        tab_names = ["🔍 シーン検索", "✂️ カット範囲指定", "💬 テロップ編集", "🎬 プロ編集"]
        
        # タブの選択を制御
        if 'force_tab_index' in st.session_state:
            # Streamlit 1.31.0以降ではst.tabsに選択インデックスを渡せないため、
            # ページ全体をリロードする方法を使用
            st.session_state.active_tab = st.session_state.force_tab_index
            del st.session_state.force_tab_index
        
        tab1, tab2, tab3, tab4 = st.tabs(tab_names)
        
        # タブ1: シーン検索
        with tab1:
            st.header("🔍 自然言語シーン検索")
            
            # 文字起こしがスキップされた場合の警告
            if st.session_state.get('skip_transcription', False):
                st.warning("⚠️ 文字起こしがスキップされたため、シーン検索機能は使用できません。")
                st.info("💡 シーン検索を使用する場合は、サイドバーから「文字起こしを実行」を行ってください。\n\nまたは、「✂️ カット範囲指定」タブで手動で範囲を指定してください。")
            else:
                # 検索クエリ候補がクリックされた場合、それを入力欄に設定
                if 'selected_suggestion' in st.session_state:
                    # セッションステートに直接設定することで、text_inputに反映される
                    st.session_state.search_query_input = st.session_state.selected_suggestion
                    del st.session_state.selected_suggestion
                
                search_query = st.text_input(
                    "検索クエリを入力",
                    placeholder="例: 商品の特徴に関して説明している箇所、商品のメンテナンス方法に関して説明している箇所",
                    key="search_query_input"
                )
                
                # 検索クエリ候補の自動生成と表示
                if 'transcript_text' in st.session_state and st.session_state.transcript_text:
                    if 'search_suggestions' not in st.session_state:
                        # 文字起こしから検索クエリ候補を生成
                        st.session_state.search_suggestions = generate_search_suggestions(
                            st.session_state.transcript_text
                        )
                    
                    if st.session_state.search_suggestions:
                        st.write("💡 **検索クエリ候補**（クリックで自動入力）")
                        
                        # 候補をボタンで表示
                        cols = st.columns(2)
                        for idx, suggestion in enumerate(st.session_state.search_suggestions):
                            col_idx = idx % 2
                            with cols[col_idx]:
                                if st.button(
                                    f"🔍 {suggestion}",
                                    key=f"suggestion_{idx}",
                                    use_container_width=True
                                ):
                                    # クリックされた候補を保存してリロード
                                    st.session_state.selected_suggestion = suggestion
                                    st.rerun()
                        
                        st.markdown("---")
                
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
                st.info("💡 スライダーに選択した時間が自動入力されています。必要に応じて調整してください。")
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
            
            # スライダーでの範囲指定（詳細設定は削除）
            st.subheader("🎯 スライダーで範囲を指定")
            
            # 現在の選択範囲を大きく表示
            st.markdown(f"""
                <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #0066cc;">📍 現在の選択範囲</h3>
                    <p style="font-size: 24px; margin: 10px 0 0 0; color: #333;">
                        <strong>{initial_start:.2f}秒</strong> 〜 <strong>{initial_end:.2f}秒</strong> 
                        （長さ: <strong>{initial_end - initial_start:.2f}秒</strong>）
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            # スライダーの範囲を選択範囲の前後30秒に限定（より直感的に）
            # エラー回避のため、範囲を安全に計算
            try:
                slider_buffer = 30.0
                slider_min = max(0.0, initial_start - slider_buffer)
                slider_max = min(st.session_state.video_duration, initial_end + slider_buffer)
                
                # slider_maxがslider_minより小さい場合の対処
                if slider_max <= slider_min:
                    slider_max = slider_min + 10.0
                
                # initial_startとinitial_endがslider範囲外の場合の対処
                if initial_start < slider_min:
                    slider_min = initial_start
                if initial_end > slider_max:
                    slider_max = initial_end
                
                # スライダーの上にラベルを追加
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 14px; color: #666;">
                        <span>🔻 範囲: <strong>{slider_min:.2f}秒</strong></span>
                        <span>🔺 範囲: <strong>{slider_max:.2f}秒</strong></span>
                    </div>
                """, unsafe_allow_html=True)
                
                # スライダーのデフォルト値を設定
                time_range = st.slider(
                    "開始・終了時間を調整（スライダーを動かして微調整）",
                    min_value=slider_min,
                    max_value=slider_max,
                    value=(initial_start, initial_end),
                    step=0.1,
                    key="cut_range_slider"
                )
                
                start_time, end_time = time_range
                
                # スライダー調整後の値を表示
                if (start_time != initial_start) or (end_time != initial_end):
                    st.warning(f"⚠️ スライダーを調整しました: {start_time:.2f}秒 〜 {end_time:.2f}秒")
            
            except Exception as e:
                st.error(f"スライダーの初期化エラー: {e}")
                # フォールバック: 動画全体の範囲でスライダーを作成
                time_range = st.slider(
                    "開始・終了時間を調整",
                    min_value=0.0,
                    max_value=st.session_state.video_duration,
                    value=(initial_start, initial_end),
                    step=0.1,
                    key="cut_range_slider_fallback"
                )
                start_time, end_time = time_range
            
            # 選択範囲を表示
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("開始時間", f"{start_time:.2f}秒")
            with col2:
                st.metric("終了時間", f"{end_time:.2f}秒")
            with col3:
                st.metric("範囲", f"{end_time - start_time:.2f}秒")
            
            # 選択範囲を更新（次回のリロード時に反映）
            st.session_state.selected_start = start_time
            st.session_state.selected_end = end_time
            
            # プレビュー生成
            if st.button("プレビューを生成"):
                preview_path = str(TEMP_VIDEOS_DIR / "preview.mp4")
                st.info(f"📹 プレビュー生成中: {start_time:.2f}秒 〜 {end_time:.2f}秒")
                if create_preview_clip(st.session_state.video_path, start_time, end_time, preview_path):
                    st.success(f"✅ プレビュー生成完了! 範囲: {start_time:.2f}秒 〜 {end_time:.2f}秒")
                    st.session_state.preview_path = preview_path
                    st.session_state.clip_start = start_time
                    st.session_state.clip_end = end_time
                else:
                    st.error(f"❌ プレビュー生成失敗: {start_time:.2f}秒 〜 {end_time:.2f}秒")
            
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
                    
                    # テキストスケール調整（追加の拡大縮小機能）
                    text_scale = st.slider(
                        "📏 テキストスケール（%）",
                        min_value=50,
                        max_value=200,
                        value=100,
                        step=5,
                        key="text_scale_slider",
                        help="フォントサイズをさらに拡大・縮小します（100%=デフォルト）"
                    )
                    st.session_state.text_scale = text_scale / 100.0
                    
                    # 文字色
                    font_color = st.color_picker("文字色", "#FFFFFF", key="font_color_picker")
                    
                    st.markdown("---")
                    
                    # テキスト表示位置設定（背景デザインの前に移動）
                    st.subheader("📍 テキスト表示位置設定")
                    position_mode = st.radio(
                        "位置設定モード",
                        ["プリセット", "テキスト表示位置選択", "カスタム（詳細）"],
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
                    
                    elif position_mode == "テキスト表示位置選択":
                        st.write("**テキスト表示位置を選択**")
                        st.info("📍 ボタンをクリックしてテキストの表示位置を選択してください。")
                        
                        # ボタンで位置を選択
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("↖️ 左上", key="pos_tl", use_container_width=True):
                                st.session_state.visual_position = "左上"
                                st.rerun()
                            if st.button("⬅️ 左中", key="pos_ml", use_container_width=True):
                                st.session_state.visual_position = "左中"
                                st.rerun()
                            if st.button("↙️ 左下", key="pos_bl", use_container_width=True):
                                st.session_state.visual_position = "左下"
                                st.rerun()
                        
                        with col2:
                            if st.button("⬆️ 上中", key="pos_tc", use_container_width=True):
                                st.session_state.visual_position = "上中"
                                st.rerun()
                            if st.button("⏺️ 中央", key="pos_cc", use_container_width=True):
                                st.session_state.visual_position = "中央"
                                st.rerun()
                            if st.button("⬇️ 下中", key="pos_bc", use_container_width=True):
                                st.session_state.visual_position = "下中"
                                st.rerun()
                        
                        with col3:
                            if st.button("↗️ 右上", key="pos_tr", use_container_width=True):
                                st.session_state.visual_position = "右上"
                                st.rerun()
                            if st.button("➡️ 右中", key="pos_mr", use_container_width=True):
                                st.session_state.visual_position = "右中"
                                st.rerun()
                            if st.button("↘️ 右下", key="pos_br", use_container_width=True):
                                st.session_state.visual_position = "右下"
                                st.rerun()
                        
                        # 選択された位置を表示
                        selected_pos = st.session_state.get('visual_position', '下中')
                        st.success(f"✅ 選択中: **{selected_pos}**")
                        
                        # 位置マッピング（9分割）
                        visual_position_map = {
                            "左上": ("20", "20"),
                            "上中": ("(w-text_w)/2", "20"),
                            "右上": ("w-text_w-20", "20"),
                            "左中": ("20", "(h-text_h)/2"),
                            "中央": ("(w-text_w)/2", "(h-text_h)/2"),
                            "右中": ("w-text_w-20", "(h-text_h)/2"),
                            "左下": ("20", "h-text_h-20"),
                            "下中": ("(w-text_w)/2", "h-text_h-20"),
                            "右下": ("w-text_w-20", "h-text_h-20")
                        }
                        x_pos, y_pos = visual_position_map[selected_pos]
                    
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
                    
                    st.markdown("---")
                    
                    # 背景デザイン（先に定義）
                    background_category = st.radio(
                        "背景カテゴリ",
                        ["シンプル", "吹き出し風", "カスタム画像"],
                        key="background_category",
                        horizontal=True
                    )
                    
                    if background_category == "シンプル":
                        # 背景の有無を選択
                        use_background = st.radio(
                            "背景を使用",
                            ["なし（透明）", "あり"],
                            key="use_simple_background",
                            horizontal=True
                        )
                        
                        if use_background == "あり":
                            # 色選択
                            bg_color_choice = st.radio(
                                "背景色",
                                ["⚪ 白", "⚫ 黒", "🎨 カスタム"],
                                key="simple_bg_color_choice",
                                horizontal=True
                            )
                            
                            if bg_color_choice == "🎨 カスタム":
                                # カラーピッカー
                                custom_bg_color = st.color_picker(
                                    "背景色を選択",
                                    "#FFFF00",
                                    key="custom_simple_bg_color"
                                )
                                st.session_state.simple_bg_custom_color = custom_bg_color
                            
                            # 透明度選択
                            bg_opacity = st.radio(
                                "透明度",
                                ["半透明", "不透明"],
                                key="simple_bg_opacity",
                                horizontal=True
                            )
                            
                            # background_typeを構築
                            if bg_color_choice == "⚪ 白":
                                if bg_opacity == "半透明":
                                    background_type = "白（半透明）"
                                else:
                                    background_type = "白（不透明）"
                            elif bg_color_choice == "⚫ 黒":
                                if bg_opacity == "半透明":
                                    background_type = "黒（半透明）"
                                else:
                                    background_type = "黒（不透明）"
                            else:  # カスタム
                                if bg_opacity == "半透明":
                                    background_type = f"カスタム（{custom_bg_color}）半透明"
                                else:
                                    background_type = f"カスタム（{custom_bg_color}）不透明"
                        else:
                            background_type = "なし（透明）"
                    elif background_category == "吹き出し風":
                        # 吹き出しの形状を選択
                        balloon_shape = st.selectbox(
                            "吹き出しの形状",
                            [
                                "💬 楕円吹き出し",
                                "🗨️ 角丸長方形",
                                "☁️ 雲形",
                                "⭐ 放射線",
                                "⬛ 角張り長方形",
                                "💭 考え事",
                                "💢 叫び",
                                "💥 爆発",
                                "💗 ハート"
                            ],
                            key="balloon_shape_select"
                        )
                        
                        # 吹き出しの色を選択（白と黒のみ）
                        balloon_color_choice = st.radio(
                            "吹き出しの色",
                            ["⚪ 白", "⚫ 黒"],
                            key="balloon_color_choice",
                            horizontal=True
                        )
                        
                        # 色に応じてサフィックスを設定
                        if balloon_color_choice == "⚪ 白":
                            balloon_color_suffix = "（白）"
                        else:  # ⚫ 黒
                            balloon_color_suffix = "（黒）"
                        
                        # background_typeを構築
                        background_type = balloon_shape + balloon_color_suffix
                        
                        # 吹き出し背景のサイズ調整機能を追加
                        st.write("**🔧 吹き出しのサイズ調整**")
                        balloon_scale = st.slider(
                            "🎈 吹き出しサイズ（%）",
                            min_value=30,
                            max_value=200,
                            value=100,
                            step=5,
                            key="balloon_scale_slider",
                            help="吹き出し背景の大きさを調整します。マウスでスライダーをドラッグしてください。"
                        )
                        st.session_state.balloon_scale = balloon_scale / 100.0
                        
                        # プレビュー用のサイズ表示
                        if balloon_scale != 100:
                            if balloon_scale < 100:
                                st.info(f"📉 元のサイズの{balloon_scale}%に縮小されます")
                            else:
                                st.info(f"📈 元のサイズの{balloon_scale}%に拡大されます")
                        
                        # 吹き出し背景の自動調整オプション
                        st.write("**⚙️ 自動調整オプション**")
                        auto_position = st.checkbox(
                            "🎯 テキストの表示位置を吹き出しの中央に合わせる",
                            value=False,
                            key="auto_position_checkbox",
                            help="有効にすると、テキストを吹き出しの中央に自動配置します（手動位置指定より優先されます）"
                        )
                        
                        auto_size = st.checkbox(
                            "📊 テキストサイズを背景のサイズに合わせて自動調整",
                            value=False,
                            key="auto_size_checkbox",
                            help="吹き出し背景のサイズに応じてフォントサイズを自動調整します（吹き出し幅60-70%のサイズ）"
                        )
                    else:  # カスタム画像
                        st.write("**📤 カスタム背景画像をアップロード**")
                        custom_bg_file = st.file_uploader(
                            "PNG画像をアップロード（透過PNG推奨）",
                            type=['png', 'jpg', 'jpeg'],
                            key="custom_bg_uploader"
                        )
                        
                        if custom_bg_file:
                            # アップロードされた画像を保存
                            custom_bg_path = TEMP_VIDEOS_DIR / f"custom_bg_{custom_bg_file.name}"
                            with open(custom_bg_path, 'wb') as f:
                                f.write(custom_bg_file.getbuffer())
                            st.session_state.custom_bg_path = str(custom_bg_path)
                            st.success(f"✅ {custom_bg_file.name} をアップロードしました！")
                            
                            # プレビュー表示
                            st.image(custom_bg_path, caption="アップロードした背景画像", width=200)
                            
                            # 背景画像のサイズ調整
                            st.write("**🔧 背景画像のサイズ調整**")
                            bg_scale = st.slider(
                                "背景画像のスケール（%）",
                                min_value=10,
                                max_value=200,
                                value=100,
                                step=5,
                                key="bg_scale_slider",
                                help="背景画像のサイズを調整します"
                            )
                            st.session_state.bg_scale = bg_scale / 100.0
                            
                            # 背景画像の位置選択
                            st.write("**📍 背景画像の位置選択**")
                            bg_position_mode = st.radio(
                                "位置設定",
                                ["プリセット", "ビジュアル選択"],
                                key="bg_position_mode",
                                horizontal=True
                            )
                            
                            if bg_position_mode == "プリセット":
                                bg_position_preset = st.selectbox(
                                    "背景位置",
                                    ["下部中央", "上部中央", "中央", "左下", "右下", "左上", "右上"],
                                    key="bg_position_select"
                                )
                                bg_position_map = {
                                    "下部中央": ("(main_w-overlay_w)/2", "main_h-overlay_h-80"),
                                    "上部中央": ("(main_w-overlay_w)/2", "20"),
                                    "中央": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
                                    "左下": ("20", "main_h-overlay_h-20"),
                                    "右下": ("main_w-overlay_w-20", "main_h-overlay_h-20"),
                                    "左上": ("20", "20"),
                                    "右上": ("main_w-overlay_w-20", "20")
                                }
                                bg_x_pos, bg_y_pos = bg_position_map[bg_position_preset]
                            else:  # ビジュアル選択
                                st.write("**背景画像の位置を選択:**")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("↖️ 左上", key="bg_pos_tl", use_container_width=True):
                                        st.session_state.bg_visual_position = "左上"
                                        st.rerun()
                                    if st.button("⬅️ 左中", key="bg_pos_ml", use_container_width=True):
                                        st.session_state.bg_visual_position = "左中"
                                        st.rerun()
                                    if st.button("↙️ 左下", key="bg_pos_bl", use_container_width=True):
                                        st.session_state.bg_visual_position = "左下"
                                        st.rerun()
                                with col2:
                                    if st.button("⬆️ 上中", key="bg_pos_tc", use_container_width=True):
                                        st.session_state.bg_visual_position = "上中"
                                        st.rerun()
                                    if st.button("⏺️ 中央", key="bg_pos_cc", use_container_width=True):
                                        st.session_state.bg_visual_position = "中央"
                                        st.rerun()
                                    if st.button("⬇️ 下中", key="bg_pos_bc", use_container_width=True):
                                        st.session_state.bg_visual_position = "下中"
                                        st.rerun()
                                with col3:
                                    if st.button("↗️ 右上", key="bg_pos_tr", use_container_width=True):
                                        st.session_state.bg_visual_position = "右上"
                                        st.rerun()
                                    if st.button("➡️ 右中", key="bg_pos_mr", use_container_width=True):
                                        st.session_state.bg_visual_position = "右中"
                                        st.rerun()
                                    if st.button("↘️ 右下", key="bg_pos_br", use_container_width=True):
                                        st.session_state.bg_visual_position = "右下"
                                        st.rerun()
                                
                                selected_bg_pos = st.session_state.get('bg_visual_position', '下中')
                                st.success(f"✅ 選択中: **{selected_bg_pos}**")
                                
                                bg_visual_position_map = {
                                    "左上": ("20", "20"),
                                    "上中": ("(main_w-overlay_w)/2", "20"),
                                    "右上": ("main_w-overlay_w-20", "20"),
                                    "左中": ("20", "(main_h-overlay_h)/2"),
                                    "中央": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
                                    "右中": ("main_w-overlay_w-20", "(main_h-overlay_h)/2"),
                                    "左下": ("20", "main_h-overlay_h-20"),
                                    "下中": ("(main_w-overlay_w)/2", "main_h-overlay_h-80"),
                                    "右下": ("main_w-overlay_w-20", "main_h-overlay_h-20")
                                }
                                bg_x_pos, bg_y_pos = bg_visual_position_map[selected_bg_pos]
                            
                            st.session_state.bg_x_pos = bg_x_pos
                            st.session_state.bg_y_pos = bg_y_pos
                            
                            background_type = "custom"
                        else:
                            st.warning("背景画像をアップロードしてください")
                            background_type = "なし（透明）"
                    
                    # シンプル背景とカスタム画像ではauto_positionを無効化
                    if background_category != "吹き出し風":
                        auto_position = False
                        auto_size = False
                    
                    # 背景位置選択（吹き出しとカスタム背景の場合のみ表示）
                    if background_category in ["吹き出し風", "カスタム画像"]:
                        st.subheader("🎨 背景位置選択")
                        bg_position_mode = st.radio(
                            "背景位置設定モード",
                            ["プリセット", "背景位置選択"],
                            key="bg_position_mode_telop",
                            horizontal=True
                        )
                        
                        if bg_position_mode == "プリセット":
                            bg_position_preset = st.selectbox(
                                "背景位置",
                                ["下部中央", "上部中央", "中央", "左上", "左中", "左下", "右上", "右中", "右下"],
                                key="bg_position_preset_telop"
                            )
                            
                            bg_position_map = {
                                "下部中央": ("(main_w-overlay_w)/2", "main_h-overlay_h-80"),
                                "上部中央": ("(main_w-overlay_w)/2", "20"),
                                "中央": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
                                "左上": ("20", "20"),
                                "左中": ("20", "(main_h-overlay_h)/2"),
                                "左下": ("20", "main_h-overlay_h-20"),
                                "右上": ("main_w-overlay_w-20", "20"),
                                "右中": ("main_w-overlay_w-20", "(main_h-overlay_h)/2"),
                                "右下": ("main_w-overlay_w-20", "main_h-overlay_h-20")
                            }
                            bg_x_pos, bg_y_pos = bg_position_map[bg_position_preset]
                            # 位置名も保存（テキスト自動配置用）
                            bg_position_name_map = {
                                "下部中央": "下中",
                                "上部中央": "上中",
                                "中央": "中央",
                                "左上": "左上",
                                "左中": "左中",
                                "左下": "左下",
                                "右上": "右上",
                                "右中": "右中",
                                "右下": "右下"
                            }
                            st.session_state.telop_bg_position_name = bg_position_name_map.get(bg_position_preset, "下中")
                        
                        else:  # 背景位置選択
                            st.write("**背景位置を選択**")
                            st.info("📍 ボタンをクリックして背景の配置位置を選択してください。")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("↖️ 左上", key="bg_pos_tl_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "左上"
                                    st.rerun()
                                if st.button("⬅️ 左中", key="bg_pos_ml_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "左中"
                                    st.rerun()
                                if st.button("↙️ 左下", key="bg_pos_bl_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "左下"
                                    st.rerun()
                            
                            with col2:
                                if st.button("⬆️ 上中", key="bg_pos_tc_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "上中"
                                    st.rerun()
                                if st.button("⏺️ 中央", key="bg_pos_cc_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "中央"
                                    st.rerun()
                                if st.button("⬇️ 下中", key="bg_pos_bc_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "下中"
                                    st.rerun()
                            
                            with col3:
                                if st.button("↗️ 右上", key="bg_pos_tr_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "右上"
                                    st.rerun()
                                if st.button("➡️ 右中", key="bg_pos_mr_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "右中"
                                    st.rerun()
                                if st.button("↘️ 右下", key="bg_pos_br_telop", use_container_width=True):
                                    st.session_state.bg_visual_position_telop = "右下"
                                    st.rerun()
                            
                            selected_bg_pos = st.session_state.get('bg_visual_position_telop', '下中')
                            st.success(f"✅ 選択中: **{selected_bg_pos}**")
                            
                            bg_visual_position_map = {
                                "左上": ("20", "20"),
                                "上中": ("(main_w-overlay_w)/2", "20"),
                                "右上": ("main_w-overlay_w-20", "20"),
                                "左中": ("20", "(main_h-overlay_h)/2"),
                                "中央": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
                                "右中": ("main_w-overlay_w-20", "(main_h-overlay_h)/2"),
                                "左下": ("20", "main_h-overlay_h-20"),
                                "下中": ("(main_w-overlay_w)/2", "main_h-overlay_h-80"),
                                "右下": ("main_w-overlay_w-20", "main_h-overlay_h-20")
                            }
                            bg_x_pos, bg_y_pos = bg_visual_position_map[selected_bg_pos]
                        
                        # セッションステートに保存
                        st.session_state.telop_bg_x_pos = bg_x_pos
                        st.session_state.telop_bg_y_pos = bg_y_pos
                        # 位置名も保存（テキスト自動配置用）
                        if bg_position_mode == "背景位置選択":
                            st.session_state.telop_bg_position_name = selected_bg_pos
                    
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
                                    y_pos,
                                    auto_position=auto_position,
                                    auto_size=auto_size
                                )
                                if success:
                                    st.session_state.preview_with_subtitle_path = preview_with_subtitle_path
                                    st.success("✅ プレビュー更新完了！")
                        else:
                            st.warning("テロップテキストを入力してください。")
                
                with col_preview:
                    # リアルタイムプレビュー表示（スクロール追従する浮遊プレビュー）
                    st.subheader("🎬 プレビュー")
                    
                    # CSSで動画サイズを小さくし、スクロール追従を追加
                    st.markdown(
                        """
                        <style>
                        /* プレビュー動画のサイズ調整 */
                        [data-testid="stVideo"] {
                            max-width: 400px !important;
                            margin: 0 auto;
                        }
                        [data-testid="stVideo"] video {
                            max-width: 100% !important;
                            height: auto !important;
                        }
                        
                        /* プレビューカラムをスクロール追従させる（PIP風） */
                        div[data-testid="column"]:has(> div > div > div > [data-testid="stVideo"]) {
                            position: sticky !important;
                            top: 20px !important;
                            align-self: flex-start !important;
                            z-index: 100 !important;
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
                                y_pos,
                                auto_position=auto_position,
                                auto_size=auto_size
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
        
        # タブ4: プロフェッショナル編集
        with tab4:
            st.header("🎬 プロフェッショナル動画編集")
            st.info("💡 **全Phase統合版**: タイムライン、マルチレイヤー、ステッカー、エフェクト、BGM、アニメーション")
            
            if 'clip_start' not in st.session_state:
                st.warning("⚠️ まず「カット範囲指定」タブでプレビューを生成してください。")
                st.info("プロフェッショナル編集を使用するには、動画の基本範囲を先に設定する必要があります。")
            else:
                # セッションステートの初期化
                if 'pro_layers' not in st.session_state:
                    st.session_state.pro_layers = []
                if 'pro_effects' not in st.session_state:
                    st.session_state.pro_effects = {
                        'speed': 1.0,
                        'brightness': 0.0,
                        'contrast': 1.0,
                        'saturation': 1.0
                    }
                if 'pro_audio' not in st.session_state:
                    st.session_state.pro_audio = {
                        'bgm_path': None,
                        'bgm_volume': 0.5,
                        'original_volume': 1.0
                    }
                
                # 2カラムレイアウト: 左側に編集ツール、右側にプレビュー
                col_tools, col_preview = st.columns([1.5, 1])
                
                with col_tools:
                    # タイムライン情報
                    st.subheader("⏱️ タイムライン")
                    clip_start = st.session_state.clip_start
                    clip_end = st.session_state.clip_end
                    clip_duration = clip_end - clip_start
                    
                    col_t1, col_t2, col_t3 = st.columns(3)
                    with col_t1:
                        st.metric("開始", f"{clip_start:.1f}秒")
                    with col_t2:
                        st.metric("終了", f"{clip_end:.1f}秒")
                    with col_t3:
                        st.metric("長さ", f"{clip_duration:.1f}秒")
                    
                    # タイムライン範囲微調整
                    with st.expander("🎯 タイムライン範囲の微調整", expanded=False):
                        st.write("動画の開始・終了時間を0.1秒単位で調整できます")
                        
                        new_start = st.number_input(
                            "開始時間（秒）",
                            min_value=0.0,
                            max_value=st.session_state.video_duration,
                            value=float(clip_start),
                            step=0.1,
                            key="pro_timeline_start"
                        )
                        
                        new_end = st.number_input(
                            "終了時間（秒）",
                            min_value=new_start + 0.1,
                            max_value=st.session_state.video_duration,
                            value=float(clip_end),
                            step=0.1,
                            key="pro_timeline_end"
                        )
                        
                        if st.button("⏱️ タイムラインを適用"):
                            st.session_state.clip_start = new_start
                            st.session_state.clip_end = new_end
                            st.success(f"✅ タイムラインを更新: {new_start:.1f}秒 〜 {new_end:.1f}秒")
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # Phase 1: マルチレイヤーテキスト
                    st.subheader("📝 Phase 1: テキストレイヤー")
                    
                    with st.expander("➕ 新しいテキストレイヤーを追加", expanded=False):
                        text_content = st.text_area("テキスト内容", "ここにテキストを入力", height=100, key="new_text_content")
                        
                        # フォント選択（プレビュー付き）
                        st.write("**🎨 フォント選択**")
                        japanese_fonts = get_japanese_fonts_dict()
                        
                        if japanese_fonts:
                            selected_font_name = st.selectbox(
                                "フォント",
                                list(japanese_fonts.keys()),
                                key="new_text_font_select"
                            )
                            selected_font_file = japanese_fonts[selected_font_name]
                            
                            # フォントプレビュー
                            font_path = FONTS_DIR / selected_font_file
                            if font_path.exists():
                                preview_img = generate_font_preview(str(font_path), text_content if text_content else "あいうえお ABC 123")
                                st.image(preview_img, caption=f"{selected_font_name} のプレビュー", use_container_width=True)
                        else:
                            st.warning("日本語フォントが見つかりません。デフォルトフォントを使用します。")
                            selected_font_file = "Noto_Sans_JP.ttf"
                        
                        st.markdown("---")
                        
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            text_start = st.number_input("開始時間（秒）", 0.0, clip_duration, 0.0, 0.1, key="new_text_start")
                        with col_t2:
                            text_end = st.number_input("終了時間（秒）", text_start, clip_duration, min(text_start + 3.0, clip_duration), 0.1, key="new_text_end")
                        
                        col_t3, col_t4 = st.columns(2)
                        with col_t3:
                            text_size = st.slider("フォントサイズ", 24, 120, 48, key="new_text_size")
                        with col_t4:
                            text_color = st.color_picker("文字色", "#FFFFFF", key="new_text_color")
                        
                        # 位置調整（プリセット or 数値入力）
                        st.write("**📍 位置設定**")
                        position_mode = st.radio(
                            "位置設定方法",
                            ["🎯 プリセット", "🔢 数値指定（ピクセル）"],
                            key="new_text_position_mode",
                            horizontal=True
                        )
                        
                        if position_mode == "🎯 プリセット":
                            text_position = st.selectbox(
                                "位置",
                                ["下部中央", "上部中央", "中央", "左上", "右上", "左下", "右下"],
                                key="new_text_position"
                            )
                            position_map = {
                                "下部中央": ("(w-text_w)/2", "h-text_h-50"),
                                "上部中央": ("(w-text_w)/2", "50"),
                                "中央": ("(w-text_w)/2", "(h-text_h)/2"),
                                "左上": ("50", "50"),
                                "右上": ("w-text_w-50", "50"),
                                "左下": ("50", "h-text_h-50"),
                                "右下": ("w-text_w-50", "h-text_h-50")
                            }
                            x, y = position_map[text_position]
                        else:
                            # 数値で直接指定
                            st.info("💡 座標は左上角が(0, 0)です。動画サイズを考慮して指定してください。")
                            col_x, col_y = st.columns(2)
                            with col_x:
                                text_x_px = st.number_input("X座標（px）", 0, 2000, 100, 10, key="new_text_x_px")
                            with col_y:
                                text_y_px = st.number_input("Y座標（px）", 0, 2000, 500, 10, key="new_text_y_px")
                            
                            x = str(text_x_px)
                            y = str(text_y_px)
                        
                        if st.button("➕ テキストレイヤーを追加", type="primary"):
                            st.session_state.pro_layers.append({
                                'type': 'text',
                                'content': text_content,
                                'start': text_start,
                                'end': text_end,
                                'x': x,
                                'y': y,
                                'font_size': text_size,
                                'color': text_color,
                                'font_file': selected_font_file,
                                'animation': 'none'
                            })
                            st.success(f"✅ テキストレイヤーを追加しました！")
                            st.rerun()
                    
                    # 既存レイヤーの表示
                    if st.session_state.pro_layers:
                        st.write(f"**📚 レイヤー一覧** ({len(st.session_state.pro_layers)}個)")
                        
                        for i, layer in enumerate(st.session_state.pro_layers):
                            with st.expander(f"{'📝' if layer['type'] == 'text' else '🖼️' if layer['type'] == 'sticker' else '🎵'} レイヤー {i+1}: {layer['type'].upper()}", expanded=False):
                                col_l1, col_l2 = st.columns([3, 1])
                                
                                with col_l1:
                                    if layer['type'] == 'text':
                                        st.text_area("内容", layer['content'], height=60, key=f"layer_content_{i}", disabled=True)
                                        st.write(f"⏱️ {layer['start']:.1f}秒 〜 {layer['end']:.1f}秒")
                                        st.write(f"🎨 サイズ: {layer['font_size']}px, 色: {layer['color']}")
                                    elif layer['type'] == 'sticker':
                                        st.write(f"📁 ファイル: {Path(layer['path']).name}")
                                        st.write(f"⏱️ {layer['start']:.1f}秒 〜 {layer['end']:.1f}秒")
                                        st.write(f"📐 位置: X={layer['x']}, Y={layer['y']}")
                                        if layer.get('scale', 1.0) != 1.0:
                                            st.write(f"🔍 スケール: {layer['scale']*100:.0f}%")
                                
                                with col_l2:
                                    if st.button("🗑️ 削除", key=f"delete_layer_{i}"):
                                        st.session_state.pro_layers.pop(i)
                                        st.success("削除しました")
                                        st.rerun()
                    
                    st.markdown("---")
                    
                    # Phase 2: ステッカー
                    st.subheader("🖼️ Phase 2: ステッカー・画像")
                    
                    with st.expander("➕ 画像/ステッカーを追加", expanded=False):
                        sticker_file = st.file_uploader("画像をアップロード（PNG, JPG, GIF）", type=['png', 'jpg', 'jpeg', 'gif'], key="new_sticker")
                        
                        if sticker_file:
                            # 画像を保存
                            sticker_path = TEMP_VIDEOS_DIR / f"sticker_{len(st.session_state.pro_layers)}_{sticker_file.name}"
                            with open(sticker_path, 'wb') as f:
                                f.write(sticker_file.getbuffer())
                            
                            st.image(sticker_path, caption="アップロードした画像", width=200)
                            
                            col_s1, col_s2 = st.columns(2)
                            with col_s1:
                                sticker_start = st.number_input("開始時間（秒）", 0.0, clip_duration, 0.0, 0.1, key="new_sticker_start")
                            with col_s2:
                                sticker_end = st.number_input("終了時間（秒）", sticker_start, clip_duration, min(sticker_start + 3.0, clip_duration), 0.1, key="new_sticker_end")
                            
                            # 位置調整
                            st.write("**📍 位置設定**")
                            sticker_position_mode = st.radio(
                                "位置設定方法",
                                ["🎯 プリセット", "🔢 数値指定（ピクセル）"],
                                key="new_sticker_position_mode",
                                horizontal=True
                            )
                            
                            if sticker_position_mode == "🎯 プリセット":
                                sticker_position = st.selectbox(
                                    "位置",
                                    ["下部中央", "上部中央", "中央", "左上", "右上", "左下", "右下"],
                                    key="new_sticker_position"
                                )
                                sticker_position_map = {
                                    "下部中央": ("(main_w-overlay_w)/2", "main_h-overlay_h-50"),
                                    "上部中央": ("(main_w-overlay_w)/2", "50"),
                                    "中央": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
                                    "左上": ("50", "50"),
                                    "右上": ("main_w-overlay_w-50", "50"),
                                    "左下": ("50", "main_h-overlay_h-50"),
                                    "右下": ("main_w-overlay_w-50", "main_h-overlay_h-50")
                                }
                                sticker_x, sticker_y = sticker_position_map[sticker_position]
                            else:
                                st.info("💡 座標は左上角が(0, 0)です。動画サイズを考慮して指定してください。")
                                col_sx, col_sy = st.columns(2)
                                with col_sx:
                                    sticker_x_px = st.number_input("X座標（px）", 0, 2000, 100, 10, key="new_sticker_x_px")
                                with col_sy:
                                    sticker_y_px = st.number_input("Y座標（px）", 0, 2000, 500, 10, key="new_sticker_y_px")
                                
                                sticker_x = str(sticker_x_px)
                                sticker_y = str(sticker_y_px)
                            
                            sticker_scale = st.slider("サイズ（%）", 10, 200, 100, 5, key="new_sticker_scale")
                            
                            if st.button("➕ ステッカーを追加", type="primary"):
                                st.session_state.pro_layers.append({
                                    'type': 'sticker',
                                    'path': str(sticker_path),
                                    'start': sticker_start,
                                    'end': sticker_end,
                                    'x': sticker_x,
                                    'y': sticker_y,
                                    'scale': sticker_scale / 100.0,
                                    'animation': 'none'
                                })
                                st.success(f"✅ ステッカーを追加しました！")
                                st.rerun()
                    
                    st.markdown("---")
                    
                    # Phase 3: エフェクト
                    st.subheader("⚡ Phase 3: エフェクト")
                    
                    with st.expander("⚡ 動画エフェクトを設定", expanded=False):
                        st.write("**速度調整**")
                        speed = st.slider(
                            "再生速度",
                            0.25, 4.0, 
                            st.session_state.pro_effects['speed'],
                            0.25,
                            help="0.25x（超スロー）〜 4.0x（早送り）",
                            key="effect_speed"
                        )
                        st.session_state.pro_effects['speed'] = speed
                        
                        if speed < 1.0:
                            st.info(f"🐌 スローモーション: {speed}x速度")
                        elif speed > 1.0:
                            st.info(f"⚡ 早送り: {speed}x速度")
                        
                        st.markdown("---")
                        st.write("**カラーフィルター**")
                        
                        brightness = st.slider(
                            "明るさ",
                            -1.0, 1.0,
                            st.session_state.pro_effects['brightness'],
                            0.1,
                            key="effect_brightness"
                        )
                        st.session_state.pro_effects['brightness'] = brightness
                        
                        contrast = st.slider(
                            "コントラスト",
                            0.0, 3.0,
                            st.session_state.pro_effects['contrast'],
                            0.1,
                            key="effect_contrast"
                        )
                        st.session_state.pro_effects['contrast'] = contrast
                        
                        saturation = st.slider(
                            "彩度",
                            0.0, 3.0,
                            st.session_state.pro_effects['saturation'],
                            0.1,
                            key="effect_saturation"
                        )
                        st.session_state.pro_effects['saturation'] = saturation
                        
                        # エフェクトプリセット
                        st.markdown("---")
                        st.write("**クイックプリセット**")
                        
                        col_p1, col_p2, col_p3 = st.columns(3)
                        with col_p1:
                            if st.button("🌅 ヴィンテージ"):
                                st.session_state.pro_effects['brightness'] = -0.1
                                st.session_state.pro_effects['contrast'] = 1.2
                                st.session_state.pro_effects['saturation'] = 0.7
                                st.rerun()
                        with col_p2:
                            if st.button("🌈 ビビッド"):
                                st.session_state.pro_effects['brightness'] = 0.1
                                st.session_state.pro_effects['contrast'] = 1.3
                                st.session_state.pro_effects['saturation'] = 1.5
                                st.rerun()
                        with col_p3:
                            if st.button("🌑 モノクロ"):
                                st.session_state.pro_effects['saturation'] = 0.0
                                st.rerun()
                        
                        if st.button("🔄 エフェクトをリセット"):
                            st.session_state.pro_effects = {
                                'speed': 1.0,
                                'brightness': 0.0,
                                'contrast': 1.0,
                                'saturation': 1.0
                            }
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # Phase 4: オーディオ
                    st.subheader("🎵 Phase 4: オーディオ")
                    
                    with st.expander("🎵 BGMを追加", expanded=False):
                        bgm_file = st.file_uploader("BGM音楽ファイル（MP3, WAV）", type=['mp3', 'wav'], key="new_bgm")
                        
                        if bgm_file:
                            # BGMを保存
                            bgm_path = TEMP_VIDEOS_DIR / f"bgm_{bgm_file.name}"
                            with open(bgm_path, 'wb') as f:
                                f.write(bgm_file.getbuffer())
                            
                            st.audio(bgm_path)
                            st.session_state.pro_audio['bgm_path'] = str(bgm_path)
                            st.success(f"✅ BGM: {bgm_file.name}")
                        
                        if st.session_state.pro_audio['bgm_path']:
                            st.write("**音量バランス**")
                            
                            bgm_volume = st.slider(
                                "BGM音量",
                                0.0, 1.0,
                                st.session_state.pro_audio['bgm_volume'],
                                0.1,
                                key="audio_bgm_volume"
                            )
                            st.session_state.pro_audio['bgm_volume'] = bgm_volume
                            
                            original_volume = st.slider(
                                "元の音声音量",
                                0.0, 1.0,
                                st.session_state.pro_audio['original_volume'],
                                0.1,
                                key="audio_original_volume"
                            )
                            st.session_state.pro_audio['original_volume'] = original_volume
                            
                            if st.button("🗑️ BGMを削除"):
                                st.session_state.pro_audio['bgm_path'] = None
                                st.rerun()
                    
                    st.markdown("---")
                    
                    # Phase 5: アニメーション
                    st.subheader("✨ Phase 5: アニメーション")
                    
                    with st.expander("✨ レイヤーにアニメーションを追加", expanded=False):
                        if not st.session_state.pro_layers:
                            st.info("まずテキストまたはステッカーレイヤーを追加してください")
                        else:
                            layer_options = [f"レイヤー {i+1}: {layer['type']}" for i, layer in enumerate(st.session_state.pro_layers)]
                            selected_layer_idx = st.selectbox("アニメーションを追加するレイヤー", range(len(layer_options)), format_func=lambda i: layer_options[i], key="anim_layer_select")
                            
                            animation_type = st.selectbox(
                                "アニメーションタイプ",
                                ["none", "fade_in", "fade_out", "fade_in_out", "slide_in_left", "slide_in_right", "slide_in_top", "slide_in_bottom"],
                                format_func=lambda x: {
                                    "none": "なし",
                                    "fade_in": "フェードイン",
                                    "fade_out": "フェードアウト",
                                    "fade_in_out": "フェードイン＆アウト",
                                    "slide_in_left": "左からスライドイン",
                                    "slide_in_right": "右からスライドイン",
                                    "slide_in_top": "上からスライドイン",
                                    "slide_in_bottom": "下からスライドイン"
                                }[x],
                                key="anim_type"
                            )
                            
                            if st.button("✨ アニメーションを適用"):
                                st.session_state.pro_layers[selected_layer_idx]['animation'] = animation_type
                                st.success(f"✅ レイヤー{selected_layer_idx+1}にアニメーション「{animation_type}」を適用しました！")
                                st.rerun()
                    
                    st.markdown("---")
                    
                    # プレビュー生成ボタン
                    st.subheader("🎬 プレビュー")
                    
                    if st.button("🔄 プレビューを生成", type="primary", use_container_width=True):
                        with st.spinner("🎬 プロフェッショナル編集を適用中... (数分かかる場合があります)"):
                            output_path = str(TEMP_VIDEOS_DIR / "pro_preview.mp4")
                            
                            # プロフェッショナル編集を適用
                            success = generate_professional_video(
                                st.session_state.video_path,
                                st.session_state.clip_start,
                                st.session_state.clip_end,
                                output_path,
                                st.session_state.pro_layers,
                                st.session_state.pro_effects,
                                st.session_state.pro_audio
                            )
                            
                            if success:
                                st.session_state.pro_preview_path = output_path
                                st.success("✅ プレビュー生成完了！")
                                st.rerun()
                
                with col_preview:
                    st.subheader("📺 プレビュー")
                    
                    # スティッキープレビュー用CSS
                    st.markdown("""
                        <style>
                        div[data-testid="column"]:has(> div > .pro-preview) {
                            position: sticky !important;
                            top: 20px !important;
                            align-self: flex-start !important;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('<div class="pro-preview">', unsafe_allow_html=True)
                    
                    if 'pro_preview_path' in st.session_state and st.session_state.pro_preview_path:
                        st.video(st.session_state.pro_preview_path)
                        
                        # 最終動画生成
                        st.markdown("---")
                        st.subheader("💾 最終動画を生成")
                        
                        if st.button("🎬 最終動画を生成", type="primary", use_container_width=True):
                            with st.spinner("🎬 最終動画を生成中..."):
                                final_output_path = str(TEMP_VIDEOS_DIR / "pro_final_output.mp4")
                                
                                success = generate_professional_video(
                                    st.session_state.video_path,
                                    st.session_state.clip_start,
                                    st.session_state.clip_end,
                                    final_output_path,
                                    st.session_state.pro_layers,
                                    st.session_state.pro_effects,
                                    st.session_state.pro_audio
                                )
                                
                                if success:
                                    st.success("✅ 最終動画生成完了！")
                                    st.video(final_output_path)
                                    
                                    # ダウンロードボタン
                                    with open(final_output_path, 'rb') as f:
                                        st.download_button(
                                            label="📥 動画をダウンロード",
                                            data=f,
                                            file_name="context_cut_pro_professional.mp4",
                                            mime="video/mp4",
                                            use_container_width=True
                                        )
                    else:
                        st.info("💡 左側で編集を行い、「プレビューを生成」ボタンをクリックしてください")
                        
                        # 編集状況サマリー
                        st.markdown("---")
                        st.write("**📊 編集状況**")
                        st.metric("テキストレイヤー", len([l for l in st.session_state.pro_layers if l['type'] == 'text']))
                        st.metric("ステッカーレイヤー", len([l for l in st.session_state.pro_layers if l['type'] == 'sticker']))
                        st.metric("BGM", "あり" if st.session_state.pro_audio['bgm_path'] else "なし")
                        st.metric("エフェクト", "適用中" if st.session_state.pro_effects['speed'] != 1.0 or st.session_state.pro_effects['brightness'] != 0.0 else "なし")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.info("👈 サイドバーから動画を取得し、文字起こしを実行してください。")
    
    # シーンプレビューのダイアログ（ポップアップ）
    @st.dialog("🎬 シーンプレビュー & 範囲調整", width="large")
    def show_scene_preview_dialog():
        # CSSでダイアログサイズを1/4に縮小
        st.markdown("""
            <style>
            [data-testid="stDialog"] {
                max-width: 450px !important;
            }
            [data-testid="stDialog"] video {
                max-width: 100% !important;
                width: 300px !important;
                margin: 0 auto;
                display: block;
            }
            </style>
        """, unsafe_allow_html=True)
        
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
                    # スライダーの値をクリアして新しい値を反映させる
                    if 'cut_range_slider' in st.session_state:
                        del st.session_state.cut_range_slider
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
