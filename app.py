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


def transcribe_video(video_path: str, model) -> Optional[Dict]:
    """動画から音声を文字起こし"""
    try:
        st.info("動画を文字起こし中... (数分かかる場合があります)")
        result = model.transcribe(video_path, language='ja', verbose=False)
        return result
    except Exception as e:
        st.error(f"文字起こしに失敗しました: {e}")
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
        # フォントパスの取得
        font_path = str(FONTS_DIR / font_file)
        
        # 背景設定
        box_settings = ""
        if background_type == "黒（半透明）":
            box_settings = ":box=1:boxcolor=black@0.5:boxborderw=5"
        elif background_type == "白":
            box_settings = ":box=1:boxcolor=white@0.8:boxborderw=5"
        
        # drawtext フィルタの構築
        # テキストのエスケープ処理
        escaped_text = subtitle_text.replace("'", r"'\''").replace(":", r"\:")
        
        drawtext_filter = (
            f"drawtext=text='{escaped_text}':"
            f"fontfile={font_path}:"
            f"fontsize={font_size}:"
            f"fontcolor={font_color}:"
            f"x={x_position}:"
            f"y={y_position}"
            f"{box_settings}"
        )
        
        # FFmpegコマンドの実行
        (
            ffmpeg
            .input(video_path, ss=start_time, to=end_time)
            .filter('drawtext', 
                   text=subtitle_text,
                   fontfile=font_path,
                   fontsize=font_size,
                   fontcolor=font_color,
                   x=x_position,
                   y=y_position,
                   box=1 if background_type != "なし（透明）" else 0,
                   boxcolor='black@0.5' if background_type == "黒（半透明）" else 'white@0.8' if background_type == "白" else '',
                   boxborderw=5 if background_type != "なし（透明）" else 0
            )
            .output(output_path, 
                   vcodec='libx264',
                   acodec='aac',
                   loglevel='error')
            .overwrite_output()
            .run()
        )
        
        return True
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
    
    # サイドバー: 動画取得
    with st.sidebar:
        st.header("📥 動画取得")
        
        video_source = st.radio(
            "動画ソースを選択",
            ["Google Drive URL", "Web URL（YouTube等）", "ローカルファイル"]
        )
        
        if video_source == "Google Drive URL":
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
                                if "gcp_service_account" not in st.secrets:
                                    st.error("Google Cloud認証情報が設定されていません。")
                                else:
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
            if st.button("文字起こしを実行"):
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
        else:
            st.info("まず動画を取得してください。")
    
    # メインエリア
    if st.session_state.video_path and st.session_state.transcription:
        
        # タブUI
        tab1, tab2, tab3 = st.tabs(["🔍 シーン検索", "✂️ カット範囲指定", "💬 テロップ編集"])
        
        # タブ1: シーン検索
        with tab1:
            st.header("🔍 自然言語シーン検索")
            
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
                        st.success(f"✅ {len(scenes)}件のシーンが見つかりました!")
                        
                        for i, scene in enumerate(scenes, 1):
                            with st.expander(f"シーン {i}: {scene['start']:.1f}s - {scene['end']:.1f}s"):
                                st.write(f"**テキスト:** {scene['text']}")
                                st.write(f"**開始:** {scene['start']:.2f}秒")
                                st.write(f"**終了:** {scene['end']:.2f}秒")
                                
                                # シーンを選択ボタン
                                if st.button(f"このシーンを選択", key=f"select_{i}"):
                                    st.session_state.selected_start = scene['start']
                                    st.session_state.selected_end = scene['end']
                                    st.success("✅ シーンを選択しました！「カット範囲指定」タブで調整できます。")
                    else:
                        st.warning("検索結果が見つかりませんでした。")
        
        # タブ2: カット範囲指定
        with tab2:
            st.header("✂️ カット範囲の指定")
            
            col1, col2 = st.columns(2)
            
            with col1:
                start_time = st.number_input(
                    "開始時間（秒）",
                    min_value=0.0,
                    max_value=st.session_state.video_duration,
                    value=st.session_state.get('selected_start', 0.0),
                    step=0.1
                )
            
            with col2:
                end_time = st.number_input(
                    "終了時間（秒）",
                    min_value=0.0,
                    max_value=st.session_state.video_duration,
                    value=st.session_state.get('selected_end', min(10.0, st.session_state.video_duration)),
                    step=0.1
                )
            
            st.write(f"選択範囲: {end_time - start_time:.2f}秒")
            
            # スライダーでの微調整
            st.subheader("スライダーで微調整")
            time_range = st.slider(
                "範囲選択",
                0.0,
                st.session_state.video_duration,
                (start_time, end_time),
                step=0.1
            )
            
            start_time, end_time = time_range
            
            # プレビュー生成
            if st.button("プレビューを生成"):
                preview_path = str(TEMP_VIDEOS_DIR / "preview.mp4")
                if create_preview_clip(st.session_state.video_path, start_time, end_time, preview_path):
                    st.success("✅ プレビュー生成完了!")
                    st.video(preview_path)
                    st.session_state.preview_path = preview_path
                    st.session_state.clip_start = start_time
                    st.session_state.clip_end = end_time
        
        # タブ3: テロップ編集
        with tab3:
            st.header("💬 テロップ編集")
            
            if 'clip_start' not in st.session_state:
                st.warning("まず「カット範囲指定」タブでプレビューを生成してください。")
            else:
                # テキスト入力
                subtitle_text = st.text_area(
                    "テロップテキスト",
                    placeholder="ここにテロップを入力してください",
                    height=100
                )
                
                # スタイル設定
                st.subheader("📐 スタイル設定")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # フォント選択
                    available_fonts = get_available_fonts()
                    
                    if not available_fonts:
                        st.error("利用可能なフォントがありません。")
                    else:
                        selected_font = st.selectbox(
                            "フォント選択",
                            available_fonts,
                            index=0
                        )
                    
                    # フォントサイズ
                    font_size = st.slider("フォントサイズ", 24, 120, 48)
                    
                    # 文字色
                    font_color = st.color_picker("文字色", "#FFFFFF")
                
                with col2:
                    # 背景色
                    background_type = st.selectbox(
                        "背景",
                        ["なし（透明）", "黒（半透明）", "白"]
                    )
                    
                    # 位置設定（簡易版）
                    position_preset = st.selectbox(
                        "テロップ位置",
                        ["下部中央", "上部中央", "中央"]
                    )
                    
                    position_map = {
                        "下部中央": ("(w-text_w)/2", "h-text_h-20"),
                        "上部中央": ("(w-text_w)/2", "20"),
                        "中央": ("(w-text_w)/2", "(h-text_h)/2")
                    }
                    x_pos, y_pos = position_map[position_preset]
                
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
                st.subheader("🎬 最終動画生成")
                
                if st.button("🎬 テロップ付き動画を生成", type="primary"):
                    if not subtitle_text:
                        st.warning("テロップテキストを入力してください。")
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
    
    # フッター
    st.markdown("---")
    st.markdown("**Context Cut Pro** - Powered by Streamlit, Whisper, ChromaDB, FFmpeg")


if __name__ == "__main__":
    main()
