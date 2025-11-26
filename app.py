"""
Context Cut Pro - 切り抜き動画生成＆編集ツール
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
TEMP_IMAGES_DIR = Path("./temp_images")  # 画像/ステッカー用一時ディレクトリ
TEMP_AUDIOS_DIR = Path("./temp_audios")  # 音声用一時ディレクトリ
CHROMADB_DIR = Path("./chromadb_data")
TEXT_BACKGROUNDS_DIR = Path("./text_backgrounds")  # テキストレイヤー背景画像用

# ディレクトリの作成
for dir_path in [FONTS_DIR, TEMP_VIDEOS_DIR, TEMP_IMAGES_DIR, TEMP_AUDIOS_DIR, CHROMADB_DIR, TEXT_BACKGROUNDS_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Google Fonts カテゴリー別フォントリスト（日本語対応フォント全種類）
# 5つのカテゴリーに分類: 普通、スタイリッシュ、漫画風、古風・和風、その他

# カテゴリー1: 普通（読みやすく汎用的なゴシック・明朝体）
FONTS_NORMAL = {
    "M PLUS 1p": "https://github.com/google/fonts/raw/main/ofl/mplus1p/MPLUS1p-Regular.ttf",
    "M PLUS Rounded 1c": "https://github.com/google/fonts/raw/main/ofl/mplusrounded1c/MPLUSRounded1c-Regular.ttf",
    "Kosugi": "https://github.com/google/fonts/raw/main/apache/kosugi/Kosugi-Regular.ttf",
    "Kosugi Maru": "https://github.com/google/fonts/raw/main/apache/kosugimaru/KosugiMaru-Regular.ttf",
    "Sawarabi Gothic": "https://github.com/google/fonts/raw/main/ofl/sawarabigothic/SawarabiGothic-Regular.ttf",
    "Sawarabi Mincho": "https://github.com/google/fonts/raw/main/ofl/sawarabimincho/SawarabiMincho-Regular.ttf",
    "BIZ UDGothic": "https://github.com/google/fonts/raw/main/ofl/bizudgothic/BIZUDGothic-Regular.ttf",
    "BIZ UDPGothic": "https://github.com/google/fonts/raw/main/ofl/bizudpgothic/BIZUDPGothic-Regular.ttf",
    "BIZ UDMincho": "https://github.com/google/fonts/raw/main/ofl/bizudmincho/BIZUDMincho-Regular.ttf",
    "BIZ UDPMincho": "https://github.com/google/fonts/raw/main/ofl/bizudpmincho/BIZUDPMincho-Regular.ttf",
    "Kiwi Maru": "https://github.com/google/fonts/raw/main/ofl/kiwimaru/KiwiMaru-Regular.ttf",
    "Noto Sans JP": "https://github.com/google/fonts/raw/main/ofl/notosansjp/static/NotoSansJP-Regular.ttf",
    "Noto Serif JP": "https://github.com/google/fonts/raw/main/ofl/notoserifjp/static/NotoSerifJP-Regular.ttf",
    "RocknRoll One": "https://github.com/google/fonts/raw/main/ofl/rocknrollone/RocknRollOne-Regular.ttf",
    "Shippori Antique": "https://github.com/google/fonts/raw/main/ofl/shipporiantique/ShipporiAntique-Regular.ttf",
}

# カテゴリー2: スタイリッシュ（モダン・都会的・洗練されたデザイン）
FONTS_STYLISH = {
    "Zen Kaku Gothic New": "https://github.com/google/fonts/raw/main/ofl/zenkakugothicnew/ZenKakuGothicNew-Regular.ttf",
    "Zen Kaku Gothic Antique": "https://github.com/google/fonts/raw/main/ofl/zenkakugothicantique/ZenKakuGothicAntique-Regular.ttf",
    "Zen Maru Gothic": "https://github.com/google/fonts/raw/main/ofl/zenmarugothic/ZenMaruGothic-Regular.ttf",
    "Stick": "https://github.com/google/fonts/raw/main/apache/stick/Stick-Regular.ttf",
    "Zen Dots": "https://github.com/google/fonts/raw/main/ofl/zendots/ZenDots-Regular.ttf",
    "Zen Kurenaido": "https://github.com/google/fonts/raw/main/ofl/zenkurenaido/ZenKurenaido-Regular.ttf",
    "Zen Loop": "https://github.com/google/fonts/raw/main/ofl/zenloop/ZenLoop-Regular.ttf",
    "DotGothic16": "https://github.com/google/fonts/raw/main/ofl/dotgothic16/DotGothic16-Regular.ttf",
    "Train One": "https://github.com/google/fonts/raw/main/ofl/trainone/TrainOne-Regular.ttf",
    "Dela Gothic One": "https://github.com/google/fonts/raw/main/ofl/delagothicone/DelaGothicOne-Regular.ttf",
    "Zen Old Mincho": "https://github.com/google/fonts/raw/main/ofl/zenoldmincho/ZenOldMincho-Regular.ttf",
    "New Tegomin": "https://github.com/google/fonts/raw/main/ofl/newtegomin/NewTegomin-Regular.ttf",
}

# カテゴリー3: 漫画風（ポップ・可愛い・インパクト）
FONTS_COMIC = {
    "Mochiy Pop One": "https://github.com/google/fonts/raw/main/ofl/mochiypopone/MochiyPopOne-Regular.ttf",
    "Mochiy Pop P One": "https://github.com/google/fonts/raw/main/ofl/mochiypoppone/MochiyPopPOne-Regular.ttf",
    "Hachi Maru Pop": "https://github.com/google/fonts/raw/main/ofl/hachimarupop/HachiMaruPop-Regular.ttf",
    "Potta One": "https://github.com/google/fonts/raw/main/ofl/pottaone/PottaOne-Regular.ttf",
    "Reggae One": "https://github.com/google/fonts/raw/main/ofl/reggaeone/ReggaeOne-Regular.ttf",
    "Rampart One": "https://github.com/google/fonts/raw/main/ofl/rampartone/RampartOne-Regular.ttf",
    "Darumadrop One": "https://github.com/google/fonts/raw/main/ofl/darumadropone/DarumadropOne-Regular.ttf",
    "Cherry Bomb One": "https://github.com/google/fonts/raw/main/ofl/cherrybombone/CherryBombOne-Regular.ttf",
    "Slackside One": "https://github.com/google/fonts/raw/main/ofl/slacksideone/SlacksideOne-Regular.ttf",
    "Yusei Magic": "https://github.com/google/fonts/raw/main/ofl/yuseimagic/YuseiMagic-Regular.ttf",
}

# カテゴリー4: 古風・和風（伝統的・書道風・和の雰囲気）
FONTS_TRADITIONAL = {
    "Shippori Mincho": "https://github.com/google/fonts/raw/main/ofl/shipporimincho/ShipporiMincho-Regular.ttf",
    "Shippori Mincho B1": "https://github.com/google/fonts/raw/main/ofl/shipporiminchob1/ShipporiMinchoB1-Regular.ttf",
    "Zen Antique": "https://github.com/google/fonts/raw/main/ofl/zenantique/ZenAntique-Regular.ttf",
    "Zen Antique Soft": "https://github.com/google/fonts/raw/main/ofl/zenantiquesoft/ZenAntiqueSoft-Regular.ttf",
    "Kaisei Tokumin": "https://github.com/google/fonts/raw/main/ofl/kaiseitokumin/KaiseiTokumin-Regular.ttf",
    "Kaisei Opti": "https://github.com/google/fonts/raw/main/ofl/kaiseiopti/KaiseiOpti-Regular.ttf",
    "Kaisei HarunoUmi": "https://github.com/google/fonts/raw/main/ofl/kaiseiharunoumi/KaiseiHarunoUmi-Regular.ttf",
    "Kaisei Decol": "https://github.com/google/fonts/raw/main/ofl/kaiseidecol/KaiseiDecol-Regular.ttf",
    "Yuji Syuku": "https://github.com/google/fonts/raw/main/ofl/yujisyuku/YujiSyuku-Regular.ttf",
    "Yuji Boku": "https://github.com/google/fonts/raw/main/ofl/yujiboku/YujiBoku-Regular.ttf",
    "Yuji Mai": "https://github.com/google/fonts/raw/main/ofl/yujimai/YujiMai-Regular.ttf",
    "Yuji Hentaigana Akari": "https://github.com/google/fonts/raw/main/ofl/yujihentaiganaakari/YujiHentaiganaAkari-Regular.ttf",
    "Yuji Hentaigana Akebono": "https://github.com/google/fonts/raw/main/ofl/yujihentaiganaakebono/YujiHentaiganaAkebono-Regular.ttf",
    "Shizuru": "https://github.com/google/fonts/raw/main/ofl/shizuru/Shizuru-Regular.ttf",
}

# カテゴリー5: その他（手書き風・ユニーク・特殊）
FONTS_OTHERS = {
    "Klee One": "https://github.com/google/fonts/raw/main/ofl/kleeone/KleeOne-Regular.ttf",
    "Yomogi": "https://github.com/google/fonts/raw/main/ofl/yomogi/Yomogi-Regular.ttf",
    "Yatra One": "https://github.com/google/fonts/raw/main/ofl/yatraone/YatraOne-Regular.ttf",
    "Kiwi Maru Light": "https://github.com/google/fonts/raw/main/ofl/kiwimaru/KiwiMaru-Light.ttf",
    "Kiwi Maru Medium": "https://github.com/google/fonts/raw/main/ofl/kiwimaru/KiwiMaru-Medium.ttf",
}

# すべてのフォントを統合（後方互換性のため）
GOOGLE_FONTS_JAPANESE = {}
for category_fonts in [FONTS_NORMAL, FONTS_STYLISH, FONTS_COMIC, FONTS_TRADITIONAL, FONTS_OTHERS]:
    GOOGLE_FONTS_JAPANESE.update(category_fonts)

JAPANESE_FONTS = GOOGLE_FONTS_JAPANESE

# カテゴリー情報
FONT_CATEGORIES = {
    "📖 普通": FONTS_NORMAL,
    "✨ スタイリッシュ": FONTS_STYLISH,
    "🎨 漫画風": FONTS_COMIC,
    "🏯 古風・和風": FONTS_TRADITIONAL,
    "🌟 その他": FONTS_OTHERS
}

def download_font(font_name: str, font_url: str) -> bool:
    """単一フォントをオンデマンドでダウンロード"""
    import urllib.request
    
    font_filename = font_name.replace(" ", "_") + ".ttf"
    font_path = FONTS_DIR / font_filename
    
    if font_path.exists():
        return True
    
    try:
        urllib.request.urlretrieve(font_url, str(font_path))
        return True
    except Exception as e:
        st.error(f"フォント {font_name} のダウンロード失敗: {e}")
        return False


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
if not (FONTS_DIR / "M_PLUS_1p.ttf").exists():
    print("日本語フォントを初期化中...")
    downloaded = download_japanese_fonts()
    print(f"{downloaded}個のフォントをダウンロードしました")

DEFAULT_FONT = FONTS_DIR / "M_PLUS_1p.ttf"

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
    """Web URLから動画をダウンロード（yt-dlp使用）
    
    参考: https://github.com/zararashraf/youtube-video-downloader-api
    """
    
    # 出力パスから拡張子を除去（yt-dlpが自動的に付与）
    output_template = str(Path(output_path).with_suffix(''))
    
    # シンプルで堅牢なフォールバック戦略
    strategies = [
        {
            'name': '📺 標準HD（720p）',
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        },
        {
            'name': '📱 標準画質（480p）',
            'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        },
        {
            'name': '🎬 単一ファイル（best）',
            'format': 'best',
        }
    ]
    
    for idx, strategy in enumerate(strategies):
        try:
            st.info(f"🔄 試行 {idx+1}/{len(strategies)}: {strategy['name']}")
            
            # シンプルで堅牢なyt-dlp設定
            ydl_opts = {
                'format': strategy['format'],
                'outtmpl': output_template,
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 5,
                'fragment_retries': 5,
                'nocheckcertificate': True,
                'noplaylist': True,
                'restrictfilenames': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # ダウンロード実行
                result = ydl.download([url])
                
                if result != 0:
                    raise Exception(f"yt-dlpがエラーコード {result} を返しました")
            
            # ダウンロードされたファイルを確認
            possible_extensions = ['.mp4', '.webm', '.mkv']
            downloaded_file = None
            
            for ext in possible_extensions:
                check_path = Path(output_template + ext)
                if check_path.exists() and check_path.stat().st_size > 0:
                    downloaded_file = check_path
                    break
            
            if not downloaded_file:
                if idx < len(strategies) - 1:
                    st.warning(f"⚠️ 次の方法を試します...")
                    continue
                else:
                    return False
            
            # 出力パスにリネーム
            if str(downloaded_file) != output_path:
                shutil.move(str(downloaded_file), output_path)
            
            file_size = Path(output_path).stat().st_size
            if file_size == 0:
                return False
            
            st.success(f"✅ ダウンロード完了！ ({file_size/1024/1024:.1f}MB)")
            return True
            
        except Exception as e:
            if idx < len(strategies) - 1:
                continue
            else:
                return False
    
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


def extract_text_from_video_frames(video_path: str, use_easyocr: bool = True) -> List[Dict]:
    """動画フレームからOCRでテキストを抽出（高速版）
    
    Args:
        video_path: 動画ファイルのパス
        use_easyocr: EasyOCRを使用する（日本語対応が良い）
        
    Returns:
        抽出されたテキストとタイムスタンプのリスト
        [{"text": "抽出テキスト", "timestamp": 10.5, "confidence": 0.95}, ...]
    """
    try:
        import cv2
        import numpy as np
        
        # EasyOCRまたはTesseractを選択
        if use_easyocr:
            try:
                import easyocr
                st.info("🔄 EasyOCR (日本語対応) を初期化中...")
                reader = easyocr.Reader(['ja', 'en'], gpu=False)
                st.success("✅ EasyOCR初期化完了")
            except Exception as e:
                st.warning(f"EasyOCRの初期化に失敗: {e}")
                st.info("Tesseractにフォールバック...")
                use_easyocr = False
        
        if not use_easyocr:
            try:
                import pytesseract
                # Tesseractの設定（日本語対応）
                tesseract_config = '--oem 3 --psm 6 -l jpn+eng'
            except Exception as e:
                st.error(f"OCRライブラリが利用できません: {e}")
                return []
        
        # 動画を開く
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            st.error("動画を開けませんでした")
            return []
        
        # 動画情報を取得
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        st.info(f"📹 動画情報: {duration:.1f}秒, {fps:.1f}fps, {total_frames}フレーム")
        
        # 🚀 高速化: サンプリング間隔を5秒に変更（従来の5倍高速）
        sample_interval = max(1, int(fps * 5))  # 5秒ごと
        
        ocr_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        frame_count = 0
        processed_count = 0
        last_text = ""  # 重複テキストを避ける
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # サンプリング間隔ごとに処理
            if frame_count % sample_interval == 0:
                timestamp = frame_count / fps
                
                # 進捗表示
                progress = int((frame_count / total_frames) * 100)
                progress_bar.progress(progress)
                status_text.text(f"🔍 OCR処理中... {timestamp:.1f}秒 / {duration:.1f}秒")
                
                # 🚀 高速化: シンプルなグレースケール変換のみ（前処理を最小化）
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # OCR実行
                try:
                    if use_easyocr:
                        # EasyOCRで読み取り
                        results = reader.readtext(gray)
                        for (bbox, text, confidence) in results:
                            # 🚀 高速化: 信頼度閾値を0.6に上げて処理削減
                            if confidence > 0.6 and text.strip() and len(text.strip()) > 1:
                                # 重複チェック（前後3件と比較）
                                is_duplicate = False
                                for recent in ocr_results[-3:]:
                                    if recent['text'] == text.strip():
                                        is_duplicate = True
                                        break
                                
                                if not is_duplicate:
                                    ocr_results.append({
                                        "text": text.strip(),
                                        "timestamp": timestamp,
                                        "confidence": confidence
                                    })
                    else:
                        # Tesseractで読み取り
                        text = pytesseract.image_to_string(gray, config=tesseract_config)
                        text = text.strip()
                        if text and len(text) > 1 and text != last_text:
                            ocr_results.append({
                                "text": text,
                                "timestamp": timestamp,
                                "confidence": 0.8  # Tesseractは信頼度を返さない
                            })
                            last_text = text
                except Exception as e:
                    # OCRエラーはスキップ
                    pass
                
                processed_count += 1
            
            frame_count += 1
        
        cap.release()
        progress_bar.empty()
        status_text.empty()
        
        # 結果をまとめる
        if ocr_results:
            st.success(f"✅ OCR完了: {len(ocr_results)}個のテキストを抽出しました")
            # 最初の数件をプレビュー表示
            st.write("**抽出されたテキストのサンプル:**")
            for i, result in enumerate(ocr_results[:5]):
                st.caption(f"{result['timestamp']:.1f}秒: {result['text'][:50]}...")
        else:
            st.warning("⚠️ 動画内からテキストが検出されませんでした")
        
        return ocr_results
        
    except Exception as e:
        st.error(f"OCR処理中にエラーが発生しました: {e}")
        return []


def combine_transcription_and_ocr(transcription: Dict, ocr_results: List[Dict]) -> Dict:
    """音声文字起こしとOCRテキストを統合
    
    Args:
        transcription: Whisperの文字起こし結果
        ocr_results: OCRで抽出したテキスト
        
    Returns:
        統合された文字起こしデータ
    """
    if not ocr_results:
        return transcription
    
    try:
        # 元のセグメントをコピー
        combined = transcription.copy()
        segments = combined.get('segments', [])
        
        # OCRテキストを近い時刻のセグメントに追加
        for ocr_item in ocr_results:
            ocr_text = ocr_item['text']
            ocr_time = ocr_item['timestamp']
            
            # 最も近いセグメントを見つける
            closest_segment = None
            min_time_diff = float('inf')
            
            for segment in segments:
                seg_start = segment['start']
                seg_end = segment['end']
                
                # セグメント内または近接している場合
                if seg_start <= ocr_time <= seg_end:
                    closest_segment = segment
                    break
                
                # 時間差を計算
                time_diff = min(abs(ocr_time - seg_start), abs(ocr_time - seg_end))
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_segment = segment
            
            # 3秒以内のセグメントに追加
            if closest_segment and min_time_diff < 3.0:
                # OCRテキストを追加（重複チェック）
                if 'ocr_text' not in closest_segment:
                    closest_segment['ocr_text'] = []
                if ocr_text not in closest_segment['ocr_text']:
                    closest_segment['ocr_text'].append(ocr_text)
            else:
                # 新しいセグメントとして追加
                new_segment = {
                    'start': ocr_time,
                    'end': ocr_time + 1.0,
                    'text': '',  # 音声テキストは空
                    'ocr_text': [ocr_text]
                }
                segments.append(new_segment)
        
        # セグメントを時刻順にソート
        segments.sort(key=lambda x: x['start'])
        combined['segments'] = segments
        
        # 全テキストを更新（音声 + OCR）
        all_texts = []
        for segment in segments:
            if segment.get('text'):
                all_texts.append(segment['text'])
            if segment.get('ocr_text'):
                all_texts.extend(segment['ocr_text'])
        
        combined['text'] = ' '.join(all_texts)
        
        return combined
        
    except Exception as e:
        st.warning(f"文字起こしとOCRの統合に失敗: {e}")
        return transcription


def setup_chromadb() -> chromadb.Client:
    """ChromaDBクライアントをセットアップ"""
    try:
        # ディレクトリが存在しない場合は作成
        CHROMADB_DIR.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.Client(Settings(
            persist_directory=str(CHROMADB_DIR),
            anonymized_telemetry=False
        ))
        return client
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        st.error(f"❌ ChromaDBのセットアップに失敗しました: {str(e)}\n\n詳細:\n```\n{error_detail}\n```")
        return None


def index_transcription_to_chromadb(transcription: Dict, video_name: str, client: chromadb.Client):
    """文字起こし結果をChromaDBにインデックス化"""
    # 🆕 clientがNoneの場合のチェック
    if client is None:
        st.session_state.index_error_msg = "❌ ChromaDBクライアントが初期化されていません。ページをリロードしてください。"
        return None
    
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
            # 音声テキスト
            text = segment['text'].strip()
            
            # OCRテキストがあれば結合
            ocr_texts = segment.get('ocr_text', [])
            if ocr_texts:
                combined_text = text + " " + " ".join(ocr_texts)
                combined_text = combined_text.strip()
            else:
                combined_text = text
            
            if combined_text:
                documents.append(combined_text)
                # 🆕 OCRテキストもmetadataに保存
                metadata = {
                    'start': float(segment['start']),  # 🆕 明示的にfloatに変換
                    'end': float(segment['end']),      # 🆕 明示的にfloatに変換
                    'segment_id': int(i),              # 🆕 明示的にintに変換
                    'has_ocr': bool(len(ocr_texts) > 0),  # 🆕 明示的にboolに変換
                    'ocr_count': int(len(ocr_texts))    # 🆕 明示的にintに変換
                }
                # OCRテキストをJSON文字列として保存
                if ocr_texts:
                    import json
                    metadata['ocr_text'] = json.dumps(ocr_texts, ensure_ascii=False)
                
                metadatas.append(metadata)
                ids.append(f"segment_{i}")
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # OCR統計を表示（st.rerun()前に表示するため、session_stateに保存）
            ocr_segments = sum(1 for meta in metadatas if meta.get('has_ocr', False))
            success_msg = f"✅ {len(documents)}件のセグメントをインデックス化しました"
            if ocr_segments > 0:
                success_msg += f"（うち{ocr_segments}件にOCRテキスト含む）"
            st.session_state.index_success_msg = success_msg
            return collection_name
        else:
            st.session_state.index_error_msg = "インデックス化可能なテキストが見つかりませんでした。"
            return None
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        st.session_state.index_error_msg = f"インデックス化に失敗しました: {str(e)}\n\n詳細:\n{error_detail}"
        return None


def search_scenes(query: str, collection_name: str, client: chromadb.Client, n_results: int = 5) -> List[Dict]:
    """自然言語クエリでシーンを検索"""
    try:
        import json
        collection = client.get_collection(name=collection_name)
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        scenes = []
        if results['metadatas'] and len(results['metadatas']) > 0:
            for i, metadata in enumerate(results['metadatas'][0]):
                scene = {
                    'text': results['documents'][0][i],
                    'start': metadata['start'],
                    'end': metadata['end'],
                    'segment_id': metadata['segment_id']
                }
                
                # 🆕 OCRテキストを復元
                if 'ocr_text' in metadata and metadata['ocr_text']:
                    try:
                        scene['ocr_text'] = json.loads(metadata['ocr_text'])
                    except:
                        pass
                
                scenes.append(scene)
        
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
    
    # キーワードパターンに基づいて優先クエリを抽出（実際に動画に含まれる内容のみ）
    for keyword, query in keyword_patterns.items():
        if keyword in text_lower and query not in matched_queries:
            matched_queries.append(query)
    
    # ⚠️ 重要: 汎用候補は追加しない
    # 動画に実際に含まれる内容のみを表示し、無理に候補を増やさない
    # マッチした候補が0個の場合は空のリストを返す
    
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
        
        # エフェクト
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
        
        # ステッカー・画像
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
            
            # アニメーション
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
        
        # テキストレイヤー
        text_layers = [l for l in layers if l['type'] == 'text']
        for text_layer in text_layers:
            # テキスト位置の計算（プリセットまたは数値指定）
            is_preset = text_layer.get('is_preset_position', False)
            position_preset = text_layer.get('position_preset')
            
            # 🎯 プリセット位置の場合、drawtextとoverlayで同じ位置計算を使用
            if is_preset and position_preset:
                # drawtextフィルター用のテキスト位置
                if position_preset == "下部中央":
                    text_x = "(w-text_w)/2"
                    text_y = "h-text_h-50"
                elif position_preset == "上部中央":
                    text_x = "(w-text_w)/2"
                    text_y = "50"
                elif position_preset == "中央":
                    text_x = "(w-text_w)/2"
                    text_y = "(h-text_h)/2"
                elif position_preset == "左上":
                    text_x = "50"
                    text_y = "50"
                elif position_preset == "右上":
                    text_x = "w-text_w-50"
                    text_y = "50"
                elif position_preset == "左下":
                    text_x = "50"
                    text_y = "h-text_h-50"
                elif position_preset == "右下":
                    text_x = "w-text_w-50"
                    text_y = "h-text_h-50"
                else:
                    # フォールバック: 中央
                    text_x = "(w-text_w)/2"
                    text_y = "(h-text_h)/2"
            else:
                # 数値指定の場合
                text_x = text_layer['x']
                text_y = text_layer['y']
            
            # 背景画像がある場合、先に背景を配置
            bg_image_path = text_layer.get('background_image')
            if bg_image_path and Path(bg_image_path).exists():
                bg_stream = ffmpeg.input(str(Path(bg_image_path).absolute()).replace("\\", "/"), loop=1, t=end_time - start_time)
                
                # 背景画像のスケール調整
                bg_scale = text_layer.get('background_scale', 1.0)
                if bg_scale != 1.0:
                    bg_stream = bg_stream.filter('scale', f'iw*{bg_scale}', f'ih*{bg_scale}')
                
                # 背景の透明度調整
                bg_opacity = text_layer.get('background_opacity', 1.0)
                if bg_opacity < 1.0:
                    bg_stream = bg_stream.filter('format', 'yuva420p').filter('colorchannelmixer', aa=bg_opacity)
                
                # 🎯 背景画像の位置: テキストと完全に同じ位置プリセットを使用
                bg_x_offset = text_layer.get('background_x_offset', 0)
                bg_y_offset = text_layer.get('background_y_offset', 0)
                
                # プリセット位置の場合、背景もテキストと同じ位置に
                if is_preset and position_preset:
                    # overlayフィルター用の背景位置（テキストと同じ位置ロジック）
                    if position_preset == "下部中央":
                        bg_x = f"(main_w-overlay_w)/2+{bg_x_offset}"
                        bg_y = f"main_h-overlay_h-50+{bg_y_offset}"
                    elif position_preset == "上部中央":
                        bg_x = f"(main_w-overlay_w)/2+{bg_x_offset}"
                        bg_y = f"50+{bg_y_offset}"
                    elif position_preset == "中央":
                        bg_x = f"(main_w-overlay_w)/2+{bg_x_offset}"
                        bg_y = f"(main_h-overlay_h)/2+{bg_y_offset}"
                    elif position_preset == "左上":
                        bg_x = f"50+{bg_x_offset}"
                        bg_y = f"50+{bg_y_offset}"
                    elif position_preset == "右上":
                        bg_x = f"main_w-overlay_w-50+{bg_x_offset}"
                        bg_y = f"50+{bg_y_offset}"
                    elif position_preset == "左下":
                        bg_x = f"50+{bg_x_offset}"
                        bg_y = f"main_h-overlay_h-50+{bg_y_offset}"
                    elif position_preset == "右下":
                        bg_x = f"main_w-overlay_w-50+{bg_x_offset}"
                        bg_y = f"main_h-overlay_h-50+{bg_y_offset}"
                    else:
                        bg_x = f"(main_w-overlay_w)/2+{bg_x_offset}"
                        bg_y = f"(main_h-overlay_h)/2+{bg_y_offset}"
                else:
                    # 数値指定の場合: テキスト位置に背景を合わせる
                    try:
                        text_x_num = int(str(text_x))
                        text_y_num = int(str(text_y))
                        # 背景の中心にテキストが来るように調整
                        bg_x = f"{text_x_num + bg_x_offset}"
                        bg_y = f"{text_y_num + bg_y_offset}"
                    except:
                        bg_x = f"{text_x}+{bg_x_offset}"
                        bg_y = f"{text_y}+{bg_y_offset}"
                
                bg_enable_expr = f"between(t,{text_layer['start']},{text_layer['end']})"
                
                video_stream = video_stream.overlay(
                    bg_stream,
                    x=bg_x,
                    y=bg_y,
                    enable=bg_enable_expr,
                    format='auto'
                )
            
            # フォントパス（レイヤーに指定されたフォントを使用）
            font_file = text_layer.get('font_file', 'Noto_Sans_JP.ttf')
            font_path = str(FONTS_DIR / font_file).replace("\\", "/")
            
            # テキストのエスケープ
            escaped_text = text_layer['content'].replace("\\", "\\\\\\\\")
            escaped_text = escaped_text.replace("'", "'\\\\''")
            escaped_text = escaped_text.replace(":", "\\:")
            escaped_text = escaped_text.replace("\n", " ")
            
            # アニメーション適用（text_x, text_yは既に上で計算済み）
            animation = text_layer.get('animation', 'none')
            text_alpha = '1.0'
            
            # テキストアニメーション
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
        
        # オーディオ処理
        video_duration = end_time - start_time
        
        # 🆕 元動画の音声に自動フェード効果を適用
        auto_audio_fade = audio_settings.get('auto_audio_fade', True)
        if auto_audio_fade and video_duration > 4.0:  # 4秒以上の動画のみ適用
            # フェードイン（開始2秒）
            audio_stream = audio_stream.filter('afade', type='in', start_time=0, duration=2.0)
            # フェードアウト（終了2秒）
            if video_duration > 2.0:
                fade_out_start = video_duration - 2.0
                audio_stream = audio_stream.filter('afade', type='out', start_time=fade_out_start, duration=2.0)
        
        bgm_path = audio_settings.get('bgm_path')
        if bgm_path and Path(bgm_path).exists():
            # BGMを読み込み
            bgm_stream = ffmpeg.input(bgm_path).audio
            
            # BGMのタイミング設定を取得
            bgm_start = audio_settings.get('bgm_start', 0.0)
            bgm_end = audio_settings.get('bgm_end')
            
            if bgm_end is None or bgm_end > video_duration:
                bgm_end = video_duration
            
            # BGMの再生時間を計算
            bgm_duration = bgm_end - bgm_start
            
            # 音量調整
            original_volume = audio_settings.get('original_volume', 1.0)
            bgm_volume = audio_settings.get('bgm_volume', 0.5)
            
            audio_stream = audio_stream.filter('volume', original_volume)
            bgm_stream = bgm_stream.filter('volume', bgm_volume)
            
            # フェードイン・フェードアウト効果
            fade_in_duration = audio_settings.get('bgm_fade_in', 0.0)
            fade_out_duration = audio_settings.get('bgm_fade_out', 0.0)
            
            if fade_in_duration > 0:
                bgm_stream = bgm_stream.filter('afade', type='in', start_time=0, duration=fade_in_duration)
            
            if fade_out_duration > 0 and bgm_duration > fade_out_duration:
                fade_out_start = bgm_duration - fade_out_duration
                bgm_stream = bgm_stream.filter('afade', type='out', start_time=fade_out_start, duration=fade_out_duration)
            
            # BGMを指定された長さに合わせてループ
            if bgm_duration > 0:
                bgm_stream = bgm_stream.filter('aloop', loop=-1, size=int(bgm_duration * 44100))
                
                # BGMの再生タイミングを調整（adelayフィルターを使用）
                if bgm_start > 0:
                    # 開始時間分だけ遅延させる
                    delay_ms = int(bgm_start * 1000)
                    bgm_stream = bgm_stream.filter('adelay', f'{delay_ms}|{delay_ms}')
            
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
    st.subheader("切り抜き動画生成＆編集ツール")
    
    # カスタムCSS: プレビュー動画を1/4サイズに縮小 & レイヤー一覧にグレー背景
    st.markdown("""
        <style>
        /* プレビュー動画のサイズを縮小 */
        .pro-preview video {
            max-width: 400px !important;
            width: 400px !important;
            height: auto !important;
        }
        
        /* ダイアログ内のプレビューも小さく */
        [data-testid="stDialog"] video {
            max-width: 300px !important;
            width: 300px !important;
            margin: 0 auto;
            display: block;
        }
        
        /* レイヤー一覧エリアにグレー背景 */
        .layer-list-container {
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
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
        
        st.warning("⚠️ **重要**: YouTubeからの直接ダウンロードは現在制限されています")
        st.info("💡 **推奨方法**: ローカルファイルのアップロードをご利用ください")
        
        video_source = st.radio(
            "動画ソースを選択",
            ["ローカルファイル（推奨）", "Google Drive URL", "Web URL（YouTube等・制限あり）"]
        )
        
        if video_source == "ローカルファイル（推奨）":
            st.success("✅ これが最も確実な方法です！")
            uploaded_file = st.file_uploader(
                "動画ファイルをアップロード", 
                type=['mp4', 'mov', 'avi', 'mkv', 'webm'],
                help="MP4, MOV, AVI, MKV, WebM形式に対応しています"
            )
            if uploaded_file:
                output_path = str(TEMP_VIDEOS_DIR / uploaded_file.name)
                with open(output_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state.video_path = output_path
                st.success(f"✅ アップロード完了! ({uploaded_file.size/1024/1024:.1f}MB)")
                st.info("👇 下にスクロールして、AI文字起こしの設定を行ってください。")
        
        elif video_source == "Google Drive URL":
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
                            # 🆕 新しい動画がダウンロードされた場合、古い状態をクリア
                            if st.session_state.get('video_path') != output_path:
                                st.session_state.transcription = None
                                st.session_state.collection_name = None
                                st.session_state.search_results = []
                                st.session_state.skip_transcription = False
                            
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
        
        elif video_source == "Web URL（YouTube等・制限あり）":
            st.warning("⚠️ **YouTubeからの直接ダウンロードは不安定です**")
            st.info("💡 失敗した場合は、SaveFrom.netなどで手動ダウンロード→ローカルファイルアップロードをご利用ください")
            
            web_url = st.text_input(
                "動画URL", 
                placeholder="https://www.youtube.com/watch?v=...",
                help="yt-dlpで動画をダウンロードします"
            )
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("📥 ダウンロード実行", type="primary"):
                    if not web_url:
                        st.error("❌ URLを入力してください")
                    else:
                        st.info("🔄 ダウンロード中...")
                        output_path = str(TEMP_VIDEOS_DIR / "video_web.mp4")
                        if download_from_web(web_url, output_path):
                            # 🆕 新しい動画がダウンロードされた場合、古い状態をクリア
                            if st.session_state.get('video_path') != output_path:
                                st.session_state.transcription = None
                                st.session_state.collection_name = None
                                st.session_state.search_results = []
                                st.session_state.skip_transcription = False
                            
                            st.session_state.video_path = output_path
                            st.success("✅ ダウンロード完了! 🎉")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ ダウンロードに失敗しました")
                            st.markdown("""
                            ### 📌 代替方法
                            
                            **https://ja.savefrom.net/1-youtube-video-downloader-175dk.html を使ってローカルに動画をダウンロードした上で、手動でアップロードしてください。**
                            
                            **手順:**
                            1. [SaveFrom.net](https://ja.savefrom.net/1-youtube-video-downloader-175dk.html) にアクセス
                            2. YouTube URLを貼り付けてダウンロード
                            3. 上部の「動画取得方法」で「**ローカルファイル（推奨）**」を選択
                            4. ダウンロードしたMP4ファイルをアップロード
                            """)
            
            with col2:
                if st.button("📂 ローカルファイルに切り替え", type="primary"):
                    st.rerun()
        
        elif video_source == "ローカルファイル":
            uploaded_file = st.file_uploader("動画ファイルをアップロード", type=['mp4', 'mov', 'avi', 'mkv'])
            if uploaded_file:
                output_path = str(TEMP_VIDEOS_DIR / uploaded_file.name)
                # 🆕 新しい動画がアップロードされた場合、古い状態をクリア
                if st.session_state.get('video_path') != output_path:
                    st.session_state.transcription = None
                    st.session_state.collection_name = None
                    st.session_state.search_results = []
                    st.session_state.skip_transcription = False
                
                with open(output_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state.video_path = output_path
                st.success(f"✅ アップロード完了! ({uploaded_file.size/1024/1024:.1f}MB)")
                st.info("👇 この下の「🎤 AI文字起こし」セクションで処理を続けてください。")
    
    # メインエリア
    if st.session_state.video_path:
        # 🆕 インデックス化の成功/失敗メッセージを表示
        if 'index_success_msg' in st.session_state:
            st.success(st.session_state.index_success_msg)
            del st.session_state.index_success_msg
        if 'index_error_msg' in st.session_state:
            st.error(st.session_state.index_error_msg)
            del st.session_state.index_error_msg
        
        # 文字起こし実行セクション（メインエリアに配置）
        if st.session_state.transcription is None:
            st.header("🎤 AI文字起こし")
            st.info("💡 シーン検索機能を使用する場合は文字起こしが必要です。\n文字起こしなしでも、カット範囲指定とテロップ編集は使用できます。")
            
            # OCRオプション
            st.write("**📝 テキスト抽出オプション**")
            enable_ocr = st.checkbox(
                "🔍 動画内のテキストもOCRで抽出（字幕、テロップなど）",
                value=False,
                help="有効にすると、音声だけでなく動画内に表示されるテキストも検索対象になります。処理時間が増加します。"
            )
            
            if enable_ocr:
                st.info("✨ OCRを有効にすると、動画内の字幕・テロップ・スライド文字なども検索できます")
                ocr_method = st.radio(
                    "OCR方式を選択",
                    ["🌟 EasyOCR（推奨・日本語精度が高い）", "⚡ Tesseract（高速）"],
                    index=0,
                    horizontal=True,
                    help="EasyOCRは日本語の認識精度が高いですが、初回は数分かかります。"
                )
                use_easyocr = "EasyOCR" in ocr_method
            else:
                use_easyocr = True  # デフォルト
            
            # モデル選択オプション
            st.write("**🎤 Whisper音声認識モデル**")
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
                    # 音声文字起こし
                    model = load_whisper_model(model_name)
                    if model:
                        transcription = transcribe_video(st.session_state.video_path, model)
                        if transcription:
                            # OCR処理を実行（有効な場合）
                            if enable_ocr:
                                st.info("🔄 OCR処理を開始します...")
                                ocr_results = extract_text_from_video_frames(
                                    st.session_state.video_path, 
                                    use_easyocr=use_easyocr
                                )
                                
                                # 音声とOCRを統合
                                if ocr_results:
                                    transcription = combine_transcription_and_ocr(transcription, ocr_results)
                                    st.success(f"✅ OCRテキストを統合しました（{len(ocr_results)}件）")
                            
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
                            st.rerun()
            
            with col_trans2:
                if st.button("⏭️ 文字起こしをスキップ", use_container_width=True):
                    st.session_state.transcription = {"segments": []}  # 空の文字起こし
                    st.session_state.video_duration = get_video_duration(st.session_state.video_path)
                    st.session_state.skip_transcription = True
                    st.success("✅ 文字起こしをスキップしました。カット範囲指定とテロップ編集が使用できます。")
                    st.rerun()
        
        # 文字起こし完了後のメイン画面
        elif st.session_state.transcription is not None:
            st.success("✅ 動画の取得と文字起こしが完了しました！")
            st.info("💡 下のタブから「シーン検索」または「動画編集」を選択してください")
    
    if st.session_state.video_path and st.session_state.transcription is not None:
        
        # タブUIの選択状態を管理
        tab_names = ["🔍 シーン検索", "🎬 動画編集"]
        
        # タブの選択を制御
        if 'force_tab_index' in st.session_state:
            # Streamlit 1.31.0以降ではst.tabsに選択インデックスを渡せないため、
            # ページ全体をリロードする方法を使用
            st.session_state.active_tab = st.session_state.force_tab_index
            del st.session_state.force_tab_index
        
        tab1, tab2 = st.tabs(tab_names)
        
        # タブ1: シーン検索
        with tab1:
            st.header("🔍 自然言語シーン検索")
            
            # 🆕 デバッグ情報（開発用）
            with st.expander("🔧 デバッグ情報", expanded=False):
                st.write(f"**video_path設定済み:** {bool(st.session_state.get('video_path'))}")
                if st.session_state.get('video_path'):
                    st.write(f"**video_path:** `{st.session_state.video_path}`")
                    st.write(f"**video_name (stem):** `{Path(st.session_state.video_path).stem}`")
                st.write(f"**transcription設定済み:** {bool(st.session_state.get('transcription'))}")
                st.write(f"**collection_name:** {st.session_state.get('collection_name', 'None')}")
                st.write(f"**chromadb_client設定済み:** {st.session_state.get('chromadb_client') is not None}")
                st.write(f"**skip_transcription:** {st.session_state.get('skip_transcription', False)}")
                if st.session_state.get('transcription'):
                    st.write(f"**セグメント数:** {len(st.session_state.transcription.get('segments', []))}")
            
            # 文字起こしがスキップされた場合の警告
            if st.session_state.get('skip_transcription', False):
                st.warning("⚠️ 文字起こしがスキップされたため、シーン検索機能は使用できません。")
                st.info("💡 シーン検索を使用する場合は、サイドバーから「文字起こしを実行」を行ってください。\n\nまたは、「動画編集」タブで手動で範囲を指定してください。")
                search_query = ""  # 空の検索クエリを設定
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
                        # 文字起こしから検索クエリ候補を生成（動画に含まれる内容のみ）
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
                    else:
                        # 候補が生成できない場合の警告メッセージ
                        st.info("ℹ️ この動画には、検索クエリを生成するのに十分な量の情報が含まれていません。\n\n💡 手動で検索キーワードを入力してください。")
                        st.markdown("---")
                
                n_results = st.slider("検索結果数", 1, 10, 5)
                
                if st.button("検索実行"):
                    if not search_query:
                        st.warning("⚠️ 検索クエリを入力してください。")
                    elif not st.session_state.get('collection_name'):
                        st.error("❌ ChromaDBのコレクション名が設定されていません。文字起こしを再実行してください。")
                    else:
                        try:
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
                        except Exception as e:
                            st.error(f"❌ 検索中にエラーが発生しました: {str(e)}")
                            st.session_state.search_results = []
                
                # 検索結果の表示
                if st.session_state.get('search_results'):
                    st.write(f"**{len(st.session_state.search_results)}件のシーン**")
                    
                    for i, scene in enumerate(st.session_state.search_results, 1):
                        with st.expander(f"シーン {i}: {scene['start']:.1f}s - {scene['end']:.1f}s"):
                            st.write(f"**テキスト:** {scene['text']}")
                            st.write(f"**開始:** {scene['start']:.2f}秒")
                            st.write(f"**終了:** {scene['end']:.2f}秒")
                            
                            # 🆕 OCRテキストを最後尾に表示
                            if 'ocr_text' in scene and scene['ocr_text']:
                                st.write("---")
                                st.write("**🔍 OCRで検出されたテキスト:**")
                                for ocr_text in scene['ocr_text']:
                                    st.caption(f"📝 {ocr_text}")
                            
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
                                    st.session_state.clip_start = scene['start']  # 動画編集用
                                    st.session_state.clip_end = scene['end']  # 動画編集用
                                    st.session_state.scene_selected = True
                                    st.session_state.show_edit_guidance = True  # 動画編集タブで案内を表示
                                    st.session_state.switch_to_edit_tab = True  # タブ切り替えフラグ
                                    st.success(f"✅ シーンを選択しました！")
                                    st.rerun()
        
        # タブ2: 動画編集
        with tab2:
            st.header("🎬 動画編集")
            
            # タブ切り替え案内メッセージ（目立つように）
            if st.session_state.get('switch_to_edit_tab', False):
                st.balloons()  # アニメーション効果
                st.success("✅ シーンを選択しました！ここで編集を開始できます。")
                st.session_state.switch_to_edit_tab = False
            
            # シーン選択後の案内メッセージ
            elif st.session_state.get('show_edit_guidance', False):
                st.success("✅ シーンが選択されました！このタブで編集を開始できます。")
                st.session_state.show_edit_guidance = False
            
            # シーン選択またはカット範囲指定から範囲を取得
            has_clip_range = 'clip_start' in st.session_state and 'clip_end' in st.session_state
            has_selected_range = 'selected_start' in st.session_state and 'selected_end' in st.session_state
            
            if not has_clip_range and not has_selected_range:
                st.warning("⚠️ まず「🔍 シーン検索」でシーンを選択してください。")
                st.info("💡 シーン検索で気に入ったシーンの「✂️ 選択」ボタンをクリックすると、ここで編集できます。")
            else:
                # clip_startとclip_endが未設定の場合、selected_startとselected_endを使用
                if not has_clip_range and has_selected_range:
                    st.session_state.clip_start = st.session_state.selected_start
                    st.session_state.clip_end = st.session_state.selected_end
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
                        'original_volume': 1.0,
                        'bgm_start': 0.0,
                        'bgm_end': None,  # None means use full video duration
                        'bgm_fade_in': 0.0,  # フェードイン時間（秒）
                        'bgm_fade_out': 0.0  # フェードアウト時間（秒）
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
                        
                        # スライダーでの調整（ラベル選択式）
                        st.write("**🎬 スライダーで範囲を調整:**")
                        
                        # 調整範囲を計算（前後30秒）
                        slider_buffer = 30.0
                        slider_min = max(0.0, float(clip_start) - slider_buffer)
                        slider_max = min(st.session_state.video_duration, float(clip_end) + slider_buffer)
                        
                        # スライダーのデフォルト値は常に現在のclip_start/clip_endを使用
                        time_range = st.slider(
                            "開始・終了時間を調整",
                            min_value=slider_min,
                            max_value=slider_max,
                            value=(float(clip_start), float(clip_end)),
                            step=0.1,
                            key="pro_timeline_slider"
                        )
                        
                        new_start, new_end = time_range
                        
                        # スライダー調整後の値を表示
                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            st.metric("開始時間", f"{new_start:.2f}秒")
                        with col_m2:
                            st.metric("終了時間", f"{new_end:.2f}秒")
                        with col_m3:
                            st.metric("長さ", f"{new_end - new_start:.2f}秒")
                        
                        # タイムライン適用ボタン
                        if st.button("⏱️ タイムラインを適用", type="primary", use_container_width=True):
                            st.session_state.clip_start = new_start
                            st.session_state.clip_end = new_end
                            st.success(f"✅ タイムラインを更新: {new_start:.1f}秒 〜 {new_end:.1f}秒")
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # レイヤー一覧
                    # 既存レイヤーとBGMの表示
                    total_items = len(st.session_state.pro_layers)
                    if st.session_state.pro_audio.get('bgm_path'):
                        total_items += 1
                    
                    if total_items > 0:
                        st.markdown('<div class="layer-list-container">', unsafe_allow_html=True)
                        st.write(f"**📚 レイヤー一覧** ({total_items}個)")
                        
                        # レイヤー概要を表示
                        st.caption(f"💡 動画全体: 0.0秒 〜 {clip_duration:.1f}秒")
                        
                        # 個別レイヤーの詳細と微調整
                        for i, layer in enumerate(st.session_state.pro_layers):
                            anim = layer.get('animation', 'none')
                            anim_icon = ""
                            if anim != 'none':
                                anim_map = {
                                    'fade_in': '📈',
                                    'fade_out': '📉',
                                    'fade_in_out': '🔄',
                                    'slide_in_left': '⬅️',
                                    'slide_in_right': '➡️',
                                    'slide_in_top': '⬆️',
                                    'slide_in_bottom': '⬇️'
                                }
                                anim_icon = f" {anim_map.get(anim, '✨')}"
                            
                            with st.expander(f"{'📝' if layer['type'] == 'text' else '🖼️'} レイヤー {i+1}: {layer['type'].upper()}{anim_icon}", expanded=False):
                                col_l1, col_l2 = st.columns([3, 1])
                                
                                with col_l1:
                                    if layer['type'] == 'text':
                                        # テキスト内容の編集
                                        new_content = st.text_area("内容", layer['content'], height=60, key=f"layer_content_{i}")
                                        
                                        # サイズと色の編集
                                        col_size, col_color = st.columns(2)
                                        with col_size:
                                            new_font_size = st.number_input("フォントサイズ", min_value=10, max_value=200, value=layer['font_size'], step=5, key=f"layer_font_size_{i}")
                                        with col_color:
                                            new_color = st.color_picker("テキスト色", value=layer['color'], key=f"layer_color_{i}")
                                        
                                        # 🆕 表示位置の編集
                                        st.write("**📐 表示位置設定**")
                                        is_preset = layer.get('is_preset_position', False)
                                        position_mode = st.radio(
                                            "位置指定方法",
                                            ["プリセット", "座標指定"],
                                            index=0 if is_preset else 1,
                                            key=f"layer_pos_mode_{i}",
                                            horizontal=True
                                        )
                                        
                                        new_is_preset = (position_mode == "プリセット")
                                        new_position_preset = layer.get('position_preset', '下部中央')
                                        new_x = layer.get('x', 100)
                                        new_y = layer.get('y', 100)
                                        
                                        if position_mode == "プリセット":
                                            position_options = ["下部中央", "上部中央", "中央", "左上", "右上", "左下", "右下"]
                                            current_preset = layer.get('position_preset', '下部中央')
                                            new_position_preset = st.selectbox(
                                                "位置を選択",
                                                position_options,
                                                index=position_options.index(current_preset) if current_preset in position_options else 0,
                                                key=f"layer_pos_preset_{i}"
                                            )
                                        else:
                                            col_x, col_y = st.columns(2)
                                            with col_x:
                                                try:
                                                    current_x = int(float(layer.get('x', 100)))
                                                except (ValueError, TypeError):
                                                    current_x = 100
                                                new_x = st.number_input("X座標", min_value=0, max_value=2000, value=current_x, step=10, key=f"layer_text_x_{i}")
                                            with col_y:
                                                try:
                                                    current_y = int(float(layer.get('y', 100)))
                                                except (ValueError, TypeError):
                                                    current_y = 100
                                                new_y = st.number_input("Y座標", min_value=0, max_value=2000, value=current_y, step=10, key=f"layer_text_y_{i}")
                                        
                                        # 背景画像の編集
                                        st.write("**🖼️ 背景画像設定**")
                                        bg_mode = st.radio(
                                            "背景画像",
                                            ["なし", "プリセット", "カスタム"],
                                            index=0 if not layer.get('background_image') else (1 if "text_backgrounds/" in layer.get('background_image', '') else 2),
                                            key=f"layer_bg_mode_{i}",
                                            horizontal=True
                                        )
                                        
                                        new_bg_image = None
                                        new_bg_size = layer.get('background_size', 1.2)
                                        new_bg_opacity = layer.get('background_opacity', 1.0)
                                        
                                        if bg_mode == "プリセット":
                                            bg_files = list(TEXT_BACKGROUNDS_DIR.glob("*.png")) + list(TEXT_BACKGROUNDS_DIR.glob("*.jpg"))
                                            if bg_files:
                                                bg_names = [f.stem for f in bg_files]
                                                current_bg = Path(layer.get('background_image', '')).stem if layer.get('background_image') else None
                                                default_idx = bg_names.index(current_bg) if current_bg in bg_names else 0
                                                selected_bg = st.selectbox("背景を選択", bg_names, index=default_idx, key=f"layer_bg_preset_{i}")
                                                new_bg_image = str([f for f in bg_files if f.stem == selected_bg][0])
                                        elif bg_mode == "カスタム":
                                            uploaded_bg = st.file_uploader("背景画像をアップロード", type=['png', 'jpg', 'jpeg'], key=f"layer_bg_upload_{i}")
                                            if uploaded_bg:
                                                bg_path = TEMP_IMAGES_DIR / f"text_bg_layer_{i}_{uploaded_bg.name}"
                                                with open(bg_path, 'wb') as f:
                                                    f.write(uploaded_bg.read())
                                                new_bg_image = str(bg_path)
                                            elif layer.get('background_image'):
                                                new_bg_image = layer['background_image']
                                        
                                        if bg_mode != "なし":
                                            new_bg_size = st.slider("背景サイズ", 0.5, 3.0, new_bg_size, 0.1, key=f"layer_bg_size_{i}")
                                            new_bg_opacity = st.slider("背景透明度", 0.0, 1.0, new_bg_opacity, 0.05, key=f"layer_bg_opacity_{i}")
                                        
                                        # 変更があれば更新ボタンを表示
                                        changes_detected = (
                                            new_content != layer['content'] or
                                            new_font_size != layer['font_size'] or
                                            new_color != layer['color'] or
                                            new_is_preset != layer.get('is_preset_position', False) or
                                            (new_is_preset and new_position_preset != layer.get('position_preset', '下部中央')) or
                                            (not new_is_preset and (new_x != layer.get('x', 100) or new_y != layer.get('y', 100))) or
                                            (bg_mode == "なし" and layer.get('background_image')) or
                                            (bg_mode != "なし" and new_bg_image and new_bg_image != layer.get('background_image')) or
                                            new_bg_size != layer.get('background_size', 1.2) or
                                            new_bg_opacity != layer.get('background_opacity', 1.0)
                                        )
                                        
                                        if changes_detected:
                                            if st.button("💾 変更を保存", key=f"save_text_layer_{i}", type="primary"):
                                                st.session_state.pro_layers[i]['content'] = new_content
                                                st.session_state.pro_layers[i]['font_size'] = new_font_size
                                                st.session_state.pro_layers[i]['color'] = new_color
                                                # 🆕 位置設定の保存
                                                st.session_state.pro_layers[i]['is_preset_position'] = new_is_preset
                                                if new_is_preset:
                                                    st.session_state.pro_layers[i]['position_preset'] = new_position_preset
                                                else:
                                                    st.session_state.pro_layers[i]['x'] = new_x
                                                    st.session_state.pro_layers[i]['y'] = new_y
                                                # 背景画像の保存
                                                if bg_mode == "なし":
                                                    st.session_state.pro_layers[i]['background_image'] = None
                                                else:
                                                    st.session_state.pro_layers[i]['background_image'] = new_bg_image
                                                    st.session_state.pro_layers[i]['background_size'] = new_bg_size
                                                    st.session_state.pro_layers[i]['background_opacity'] = new_bg_opacity
                                                st.success(f"✅ レイヤー{i+1}を更新しました")
                                                st.rerun()
                                    elif layer['type'] == 'sticker':
                                        # ファイルの再アップロード
                                        st.write(f"📁 現在のファイル: {Path(layer['path']).name}")
                                        new_sticker_file = st.file_uploader("新しいファイルに変更", type=['png', 'jpg', 'jpeg', 'gif'], key=f"layer_sticker_file_{i}")
                                        
                                        new_sticker_path = layer['path']
                                        if new_sticker_file:
                                            new_path = TEMP_IMAGES_DIR / f"layer_sticker_{i}_{new_sticker_file.name}"
                                            with open(new_path, 'wb') as f:
                                                f.write(new_sticker_file.read())
                                            new_sticker_path = str(new_path)
                                        
                                        # 位置の編集
                                        st.write("**📐 位置設定**")
                                        col_x, col_y = st.columns(2)
                                        with col_x:
                                            # 文字列や浮動小数点数を安全に整数に変換
                                            try:
                                                current_x = int(float(layer.get('x', 0)))
                                            except (ValueError, TypeError):
                                                current_x = 0
                                            new_x = st.number_input("X位置", min_value=0, max_value=2000, value=current_x, step=10, key=f"layer_sticker_x_{i}")
                                        with col_y:
                                            try:
                                                current_y = int(float(layer.get('y', 0)))
                                            except (ValueError, TypeError):
                                                current_y = 0
                                            new_y = st.number_input("Y位置", min_value=0, max_value=2000, value=current_y, step=10, key=f"layer_sticker_y_{i}")
                                        
                                        # スケールの編集
                                        new_scale = st.slider("スケール（%）", min_value=10, max_value=300, value=int(layer.get('scale', 1.0) * 100), step=5, key=f"layer_sticker_scale_{i}") / 100.0
                                        
                                        # アニメーションの編集
                                        st.write("**✨ アニメーション**")
                                        animation_options = {
                                            'none': 'なし',
                                            'fade_in': 'フェードイン',
                                            'fade_out': 'フェードアウト',
                                            'fade_in_out': 'フェードイン＆アウト',
                                            'slide_in_left': '左からスライドイン',
                                            'slide_in_right': '右からスライドイン',
                                            'slide_in_top': '上からスライドイン',
                                            'slide_in_bottom': '下からスライドイン'
                                        }
                                        current_anim = layer.get('animation', 'none')
                                        new_animation = st.selectbox(
                                            "アニメーション効果",
                                            list(animation_options.keys()),
                                            index=list(animation_options.keys()).index(current_anim),
                                            format_func=lambda x: animation_options[x],
                                            key=f"layer_sticker_anim_{i}"
                                        )
                                        
                                        # 変更があれば更新ボタンを表示
                                        changes_detected = (
                                            new_sticker_path != layer['path'] or
                                            new_x != current_x or
                                            new_y != current_y or
                                            new_scale != layer.get('scale', 1.0) or
                                            new_animation != layer.get('animation', 'none')
                                        )
                                        
                                        if changes_detected:
                                            if st.button("💾 変更を保存", key=f"save_sticker_layer_{i}", type="primary"):
                                                st.session_state.pro_layers[i]['path'] = new_sticker_path
                                                st.session_state.pro_layers[i]['x'] = new_x
                                                st.session_state.pro_layers[i]['y'] = new_y
                                                st.session_state.pro_layers[i]['scale'] = new_scale
                                                st.session_state.pro_layers[i]['animation'] = new_animation
                                                st.success(f"✅ レイヤー{i+1}を更新しました")
                                                st.rerun()
                                    
                                    # アニメーション情報を表示
                                    if anim != 'none':
                                        anim_names = {
                                            'fade_in': 'フェードイン',
                                            'fade_out': 'フェードアウト',
                                            'fade_in_out': 'フェードイン＆アウト',
                                            'slide_in_left': '左からスライドイン',
                                            'slide_in_right': '右からスライドイン',
                                            'slide_in_top': '上からスライドイン',
                                            'slide_in_bottom': '下からスライドイン'
                                        }
                                        st.info(f"✨ アニメーション: {anim_names.get(anim, anim)}")
                                    
                                    # タイムライン微調整スライダー
                                    st.write("**⏱️ タイムライン微調整**")
                                    layer_time_range = st.slider(
                                        "表示時間",
                                        min_value=0.0,
                                        max_value=clip_duration,
                                        value=(layer['start'], layer['end']),
                                        step=0.1,
                                        key=f"layer_time_{i}"
                                    )
                                    
                                    if layer_time_range != (layer['start'], layer['end']):
                                        if st.button("⏱️ 時間を更新", key=f"update_layer_time_{i}"):
                                            st.session_state.pro_layers[i]['start'] = layer_time_range[0]
                                            st.session_state.pro_layers[i]['end'] = layer_time_range[1]
                                            st.success(f"✅ レイヤー{i+1}の時間を更新しました")
                                            st.rerun()
                                    else:
                                        st.write(f"⏱️ {layer['start']:.1f}秒 〜 {layer['end']:.1f}秒")
                                
                                with col_l2:
                                    if st.button("🗑️ 削除", key=f"delete_layer_{i}"):
                                        st.session_state.pro_layers.pop(i)
                                        st.success("削除しました")
                                        st.rerun()
                        
                        # BGMの詳細表示と編集
                        if st.session_state.pro_audio.get('bgm_path'):
                            st.markdown("---")
                            with st.expander("🎵 BGM編集", expanded=False):
                                bgm_start = st.session_state.pro_audio.get('bgm_start', 0.0)
                                bgm_end = st.session_state.pro_audio.get('bgm_end', clip_duration)
                                
                                st.write(f"📁 現在のファイル: {Path(st.session_state.pro_audio['bgm_path']).name}")
                                
                                # 新しいBGMファイルのアップロード
                                new_bgm_file = st.file_uploader("新しいBGMに変更", type=['mp3', 'wav', 'm4a', 'aac'], key="bgm_replace_file")
                                new_bgm_path = st.session_state.pro_audio['bgm_path']
                                if new_bgm_file:
                                    new_path = TEMP_AUDIOS_DIR / f"bgm_{new_bgm_file.name}"
                                    with open(new_path, 'wb') as f:
                                        f.write(new_bgm_file.read())
                                    new_bgm_path = str(new_path)
                                
                                # 表示時間の編集
                                st.write("**⏱️ 再生時間設定**")
                                bgm_time_range = st.slider(
                                    "BGM再生範囲（秒）",
                                    min_value=0.0,
                                    max_value=clip_duration,
                                    value=(bgm_start, bgm_end),
                                    step=0.1,
                                    key="bgm_time_range_edit"
                                )
                                new_bgm_start, new_bgm_end = bgm_time_range
                                
                                # 音量の編集
                                st.write("**🔊 音量設定**")
                                col_bgm_vol, col_orig_vol = st.columns(2)
                                with col_bgm_vol:
                                    new_bgm_volume = st.slider(
                                        "BGM音量（%）",
                                        min_value=0,
                                        max_value=100,
                                        value=int(st.session_state.pro_audio.get('bgm_volume', 0.5) * 100),
                                        step=5,
                                        key="bgm_volume_edit"
                                    ) / 100.0
                                with col_orig_vol:
                                    new_original_volume = st.slider(
                                        "元音声音量（%）",
                                        min_value=0,
                                        max_value=100,
                                        value=int(st.session_state.pro_audio.get('original_volume', 1.0) * 100),
                                        step=5,
                                        key="original_volume_edit"
                                    ) / 100.0
                                
                                # フェード効果の編集
                                st.write("**✨ フェード効果**")
                                col_fade_in, col_fade_out = st.columns(2)
                                with col_fade_in:
                                    new_fade_in = st.slider(
                                        "フェードイン（秒）",
                                        min_value=0.0,
                                        max_value=5.0,
                                        value=st.session_state.pro_audio.get('bgm_fade_in', 0.0),
                                        step=0.1,
                                        key="bgm_fade_in_edit"
                                    )
                                with col_fade_out:
                                    new_fade_out = st.slider(
                                        "フェードアウト（秒）",
                                        min_value=0.0,
                                        max_value=5.0,
                                        value=st.session_state.pro_audio.get('bgm_fade_out', 0.0),
                                        step=0.1,
                                        key="bgm_fade_out_edit"
                                    )
                                
                                # 変更があれば更新ボタンを表示
                                bgm_changes = (
                                    new_bgm_path != st.session_state.pro_audio['bgm_path'] or
                                    new_bgm_start != bgm_start or
                                    new_bgm_end != bgm_end or
                                    new_bgm_volume != st.session_state.pro_audio.get('bgm_volume', 0.5) or
                                    new_original_volume != st.session_state.pro_audio.get('original_volume', 1.0) or
                                    new_fade_in != st.session_state.pro_audio.get('bgm_fade_in', 0.0) or
                                    new_fade_out != st.session_state.pro_audio.get('bgm_fade_out', 0.0)
                                )
                                
                                col_save, col_remove = st.columns(2)
                                with col_save:
                                    if bgm_changes:
                                        if st.button("💾 変更を保存", key="save_bgm", type="primary", use_container_width=True):
                                            st.session_state.pro_audio['bgm_path'] = new_bgm_path
                                            st.session_state.pro_audio['bgm_start'] = new_bgm_start
                                            st.session_state.pro_audio['bgm_end'] = new_bgm_end
                                            st.session_state.pro_audio['bgm_volume'] = new_bgm_volume
                                            st.session_state.pro_audio['original_volume'] = new_original_volume
                                            st.session_state.pro_audio['bgm_fade_in'] = new_fade_in
                                            st.session_state.pro_audio['bgm_fade_out'] = new_fade_out
                                            st.success("✅ BGM設定を更新しました")
                                            st.rerun()
                                with col_remove:
                                    if st.button("🗑️ BGMを削除", key="remove_bgm", use_container_width=True):
                                        st.session_state.pro_audio['bgm_path'] = None
                                        st.session_state.pro_audio['bgm_start'] = 0.0
                                        st.session_state.pro_audio['bgm_end'] = clip_duration
                                        st.success("✅ BGMを削除しました")
                                        st.rerun()
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown("---")

                    st.subheader("📝 テキストレイヤー")
                    
                    with st.expander("➕ 新しいテキストレイヤーを追加", expanded=False):
                        text_content = st.text_area("テキスト内容", "ここにテキストを入力", height=100, key="new_text_content")
                        
                        # フォント選択（カテゴリー別・視覚的プレビュー付き）
                        st.write("**🎨 フォント選択**")
                        
                        # カスタムプレビューテキスト
                        preview_text = "ふぉんと・フォント・Font、本当！？"
                        
                        # セッション状態でフォント選択を管理
                        if 'selected_font_for_new_layer' not in st.session_state:
                            st.session_state.selected_font_for_new_layer = list(GOOGLE_FONTS_JAPANESE.keys())[0]
                        
                        # カテゴリー選択タブ
                        category_tabs = st.tabs(list(FONT_CATEGORIES.keys()))
                        
                        for tab_idx, (category_name, category_fonts) in enumerate(FONT_CATEGORIES.items()):
                            with category_tabs[tab_idx]:
                                st.caption(f"{len(category_fonts)}種類のフォント")
                                
                                # 3列レイアウトで表示
                                font_list = list(category_fonts.keys())
                                cols_per_row = 3
                                
                                for i in range(0, len(font_list), cols_per_row):
                                    cols = st.columns(cols_per_row)
                                    for j, col in enumerate(cols):
                                        if i + j < len(font_list):
                                            font_name = font_list[i + j]
                                            font_url = category_fonts[font_name]
                                            
                                            with col:
                                                font_file = font_name.replace(" ", "_") + ".ttf"
                                                font_path = FONTS_DIR / font_file
                                                
                                                # フォントが存在する場合のみプレビュー生成
                                                if font_path.exists():
                                                    preview_img = generate_font_preview(str(font_path), preview_text, size=24)
                                                    
                                                    # ボタンとして画像を表示
                                                    if st.button(f"{font_name}", key=f"font_cat_{tab_idx}_{i}_{j}", use_container_width=True):
                                                        st.session_state.selected_font_for_new_layer = font_name
                                                        st.rerun()
                                                    
                                                    # 選択されたフォントにはハイライト
                                                    if st.session_state.selected_font_for_new_layer == font_name:
                                                        st.image(preview_img, use_container_width=True)
                                                        st.success("✓ 選択中")
                                                    else:
                                                        st.image(preview_img, use_container_width=True)
                                                else:
                                                    # フォントが未ダウンロードの場合
                                                    if st.button(f"📥 {font_name}", key=f"font_dl_cat_{tab_idx}_{i}_{j}", use_container_width=True):
                                                        # オンデマンドでダウンロード
                                                        with st.spinner(f"{font_name} をダウンロード中..."):
                                                            if download_font(font_name, font_url):
                                                                st.session_state.selected_font_for_new_layer = font_name
                                                                st.success(f"✅ {font_name} をダウンロードしました")
                                                                st.rerun()
                                                    st.caption("クリックでダウンロード")
                        
                        # 選択中のフォントを大きく表示
                        selected_font_name = st.session_state.selected_font_for_new_layer
                        selected_font_file = selected_font_name.replace(" ", "_") + ".ttf"
                        
                        st.info(f"**選択中のフォント**: {selected_font_name}")
                        
                        # フォントプレビュー（背景画像がある場合は組み合わせて表示）
                        font_path = FONTS_DIR / selected_font_file
                        if font_path.exists():
                            # 背景画像が選択されている場合
                            if st.session_state.get('preview_with_background') and st.session_state.get('preview_bg_path'):
                                try:
                                    from PIL import Image, ImageDraw, ImageFont
                                    
                                    # 背景画像を読み込み
                                    bg_img = Image.open(st.session_state.preview_bg_path)
                                    
                                    # 適切なサイズにリサイズ（最大幅800px）
                                    max_width = 800
                                    if bg_img.width > max_width:
                                        ratio = max_width / bg_img.width
                                        new_size = (max_width, int(bg_img.height * ratio))
                                        bg_img = bg_img.resize(new_size, Image.LANCZOS)
                                    
                                    # RGB変換（透過がある場合）
                                    if bg_img.mode != 'RGB':
                                        # 白背景で合成
                                        white_bg = Image.new('RGB', bg_img.size, (255, 255, 255))
                                        if bg_img.mode == 'RGBA':
                                            white_bg.paste(bg_img, mask=bg_img.split()[3])
                                        else:
                                            white_bg.paste(bg_img)
                                        bg_img = white_bg
                                    
                                    # テキストを中央に描画
                                    draw = ImageDraw.Draw(bg_img)
                                    font_size = 40
                                    font = ImageFont.truetype(str(font_path), font_size)
                                    
                                    preview_text_to_draw = text_content if text_content else preview_text
                                    
                                    # テキストのバウンディングボックスを取得
                                    bbox = draw.textbbox((0, 0), preview_text_to_draw, font=font)
                                    text_width = bbox[2] - bbox[0]
                                    text_height = bbox[3] - bbox[1]
                                    
                                    # 中央に配置
                                    x = (bg_img.width - text_width) // 2
                                    y = (bg_img.height - text_height) // 2
                                    
                                    # 影を追加（見やすくするため）
                                    shadow_offset = 2
                                    draw.text((x + shadow_offset, y + shadow_offset), preview_text_to_draw, font=font, fill=(0, 0, 0))
                                    # テキストを描画
                                    draw.text((x, y), preview_text_to_draw, font=font, fill=(255, 255, 255))
                                    
                                    st.image(bg_img, caption=f"{selected_font_name} + 背景画像のプレビュー", use_container_width=True)
                                except Exception as e:
                                    st.warning(f"背景付きプレビューの生成に失敗: {e}")
                                    # 通常のフォントプレビューにフォールバック
                                    large_preview = generate_font_preview(str(font_path), text_content if text_content else preview_text, size=40)
                                    st.image(large_preview, caption=f"{selected_font_name} のプレビュー", use_container_width=True)
                            else:
                                # 通常のフォントプレビュー
                                large_preview = generate_font_preview(str(font_path), text_content if text_content else preview_text, size=40)
                                st.image(large_preview, caption=f"{selected_font_name} のプレビュー", use_container_width=True)
                        else:
                            st.warning(f"{selected_font_name} をダウンロードしてください")
                        
                        st.markdown("---")
                        
                        # 表示時間をスライダーで設定
                        st.write("**⏱️ 表示時間設定**")
                        text_time_range = st.slider(
                            "表示時間範囲（秒）",
                            min_value=0.0,
                            max_value=clip_duration,
                            value=(0.0, min(3.0, clip_duration)),
                            step=0.1,
                            key="new_text_time_slider"
                        )
                        text_start, text_end = text_time_range
                        st.caption(f"📌 {text_start:.1f}秒 〜 {text_end:.1f}秒 （長さ: {text_end - text_start:.1f}秒）")
                        
                        st.markdown("---")
                        
                        col_t3, col_t4 = st.columns(2)
                        with col_t3:
                            text_size = st.slider("フォントサイズ", 24, 120, 48, key="new_text_size")
                        with col_t4:
                            text_color = st.color_picker("文字色", "#FFFFFF", key="new_text_color")
                        
                        st.markdown("---")
                        
                        # 背景画像設定
                        st.write("**🖼️ 背景画像設定**")
                        background_mode = st.radio(
                            "背景設定",
                            ["⛔ 設定しない", "📚 プリセットから選択", "📤 カスタム画像をアップロード"],
                            key="text_bg_mode",
                            horizontal=True
                        )
                        
                        text_bg_path = None
                        text_bg_scale = 1.0
                        text_bg_opacity = 1.0
                        
                        # 背景なしの場合はプレビューフラグをクリア
                        if background_mode == "⛔ 設定しない":
                            st.session_state.preview_with_background = False
                            st.session_state.preview_bg_path = None
                        
                        if background_mode == "📚 プリセットから選択":
                            # プリセット背景画像を取得
                            preset_backgrounds = list(TEXT_BACKGROUNDS_DIR.glob("*.png")) + list(TEXT_BACKGROUNDS_DIR.glob("*.jpg"))
                            if preset_backgrounds:
                                bg_names = [bg.stem for bg in preset_backgrounds]
                                
                                # 🆕 選択変更時にプレビューを即座に更新
                                def update_bg_preview():
                                    if 'text_preset_bg' in st.session_state:
                                        selected = st.session_state.text_preset_bg
                                        matching_bg = [bg for bg in preset_backgrounds if bg.stem == selected]
                                        if matching_bg:
                                            st.session_state.preview_bg_path = str(matching_bg[0])
                                            st.session_state.preview_with_background = True
                                
                                selected_bg_name = st.selectbox(
                                    "背景画像を選択",
                                    bg_names,
                                    key="text_preset_bg",
                                    on_change=update_bg_preview
                                )
                                
                                # 選択された背景のパスを取得
                                matching_bg = [bg for bg in preset_backgrounds if bg.stem == selected_bg_name]
                                if matching_bg:
                                    text_bg_path = str(matching_bg[0])
                                    
                                    # プレビュー用にセッション状態を更新
                                    st.session_state.preview_bg_path = text_bg_path
                                    st.session_state.preview_with_background = True
                                    
                                    # プレビュー表示
                                    st.image(text_bg_path, caption=f"選択した背景: {selected_bg_name}", width=200)
                            else:
                                st.info("💡 プリセット背景画像がまだありません。カスタム画像をアップロードしてください。")
                                st.caption("※ 管理者は text_backgrounds/ フォルダに画像を配置することでプリセットを追加できます")
                        
                        elif background_mode == "📤 カスタム画像をアップロード":
                            custom_bg_file = st.file_uploader(
                                "背景画像（PNG, JPG推奨）",
                                type=['png', 'jpg', 'jpeg'],
                                key="text_custom_bg"
                            )
                            if custom_bg_file:
                                # カスタム背景を保存
                                custom_bg_path = TEMP_VIDEOS_DIR / f"text_bg_{len(st.session_state.pro_layers)}_{custom_bg_file.name}"
                                with open(custom_bg_path, 'wb') as f:
                                    f.write(custom_bg_file.getbuffer())
                                text_bg_path = str(custom_bg_path)
                                
                                # プレビュー用にセッション状態を更新
                                st.session_state.preview_bg_path = text_bg_path
                                st.session_state.preview_with_background = True
                                
                                st.image(custom_bg_path, caption="アップロードした背景", width=200)
                        
                        # 背景画像が設定されている場合の調整オプション
                        if text_bg_path:
                            st.info("💡 背景画像はテキストに自動追従します。サイズと位置を調整できます。")
                            
                            col_bg1, col_bg2 = st.columns(2)
                            with col_bg1:
                                text_bg_scale = st.slider(
                                    "背景サイズ（%）",
                                    50, 300, 150, 5,
                                    key="text_bg_scale",
                                    help="背景画像のサイズを調整（テキストより大きめがおすすめ）"
                                ) / 100.0
                            with col_bg2:
                                text_bg_opacity = st.slider(
                                    "背景の透明度",
                                    0.0, 1.0, 0.9, 0.1,
                                    key="text_bg_opacity",
                                    help="0.0=完全透明、1.0=完全不透明"
                                )
                            
                            # 背景とテキストの相対位置調整
                            st.write("**🔧 背景とテキストの位置微調整**")
                            col_offset1, col_offset2 = st.columns(2)
                            with col_offset1:
                                bg_x_fine_offset = st.slider(
                                    "左右オフセット（px）",
                                    -200, 200, 0, 10,
                                    key="text_bg_x_offset",
                                    help="背景をテキストに対して左右に移動"
                                )
                            with col_offset2:
                                bg_y_fine_offset = st.slider(
                                    "上下オフセット（px）",
                                    -200, 200, 0, 10,
                                    key="text_bg_y_offset",
                                    help="背景をテキストに対して上下に移動"
                                )
                        
                        st.markdown("---")
                        
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
                            # 背景画像用の位置オフセット（UIで設定した値を使用）
                            bg_x_offset = bg_x_fine_offset if text_bg_path else 0
                            bg_y_offset = bg_y_fine_offset if text_bg_path else 0
                                
                            new_layer = {
                                'type': 'text',
                                'content': text_content,
                                'start': text_start,
                                'end': text_end,
                                'x': x,
                                'y': y,
                                'font_size': text_size,
                                'color': text_color,
                                'font_file': selected_font_file,
                                'animation': 'none',
                                'background_image': text_bg_path,
                                'background_scale': text_bg_scale,
                                'background_opacity': text_bg_opacity,
                                'background_x_offset': bg_x_offset,
                                'background_y_offset': bg_y_offset,
                                'is_preset_position': position_mode == "🎯 プリセット",
                                'position_preset': text_position if position_mode == "🎯 プリセット" else None
                            }
                            st.session_state.pro_layers.append(new_layer)
                            st.success(f"✅ テキストレイヤーを追加しました！")
                            st.rerun()
                    
                    
                    # ステッカー・画像
                    st.subheader("🖼️ ステッカー・画像")
                    
                    with st.expander("➕ 画像/ステッカーを追加", expanded=False):
                        sticker_file = st.file_uploader("画像をアップロード（PNG, JPG, GIF）", type=['png', 'jpg', 'jpeg', 'gif'], key="new_sticker")
                        
                        if sticker_file:
                            # 画像を保存
                            sticker_path = TEMP_VIDEOS_DIR / f"sticker_{len(st.session_state.pro_layers)}_{sticker_file.name}"
                            with open(sticker_path, 'wb') as f:
                                f.write(sticker_file.getbuffer())
                            
                            st.image(sticker_path, caption="アップロードした画像", width=200)
                            
                            st.write("**⏱️ 表示時間設定**")
                            
                            # スライダーでの時間調整
                            if 'sticker_time_slider' not in st.session_state:
                                st.session_state.sticker_time_slider = (0.0, min(3.0, clip_duration))
                            
                            sticker_time_range = st.slider(
                                "表示時間範囲（秒）",
                                min_value=0.0,
                                max_value=clip_duration,
                                value=(0.0, min(3.0, clip_duration)),
                                step=0.1,
                                key="sticker_time_slider_widget"
                            )
                            sticker_start, sticker_end = sticker_time_range
                            st.caption(f"📌 {sticker_start:.1f}秒 〜 {sticker_end:.1f}秒 （長さ: {sticker_end - sticker_start:.1f}秒）")
                            
                            st.markdown("---")
                            
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
                    
                    
                    # アニメーション
                    st.subheader("✨ アニメーション")
                    
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
                    
                    
                    # エフェクト
                    st.subheader("⚡ エフェクト")
                    
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
                        # 🆕 エフェクトリセット（再生速度とカラーフィルターをデフォルトに）
                        if st.button("🔄 エフェクトをリセット", key="preset_reset", type="secondary"):
                            st.session_state.pro_effects['speed'] = 1.0
                            st.session_state.pro_effects['brightness'] = 0.0
                            st.session_state.pro_effects['contrast'] = 1.0
                            st.session_state.pro_effects['saturation'] = 1.0
                            st.success("✅ エフェクトをデフォルト値にリセットしました")
                            st.rerun()
                    
                    
                    # オーディオ
                    st.subheader("🎵 オーディオ")
                    
                    # 🆕 元動画のオーディオフェード設定
                    with st.expander("🎧 元動画の音声設定", expanded=False):
                        st.write("**🎚️ 自動フェードエフェクト**")
                        st.caption("切り抜いた動画部分の音声に自動的にフェード効果を適用します")
                        
                        # デフォルトでチェックを入れる
                        if 'auto_audio_fade' not in st.session_state.pro_audio:
                            st.session_state.pro_audio['auto_audio_fade'] = True
                        
                        auto_fade = st.checkbox(
                            "🔊 元動画の音声に自動フェードを適用",
                            value=st.session_state.pro_audio.get('auto_audio_fade', True),
                            key="auto_audio_fade_check",
                            help="切り抜き開始時にフェードイン（2秒）、終了時にフェードアウト（2秒）を自動適用します"
                        )
                        st.session_state.pro_audio['auto_audio_fade'] = auto_fade
                        
                        if auto_fade:
                            st.info("✅ 元動画の音声に自動フェード効果が適用されます")
                            st.caption("📈 開始: 2秒かけてフェードイン")
                            st.caption("📉 終了: 2秒かけてフェードアウト")
                        else:
                            st.info("⚪ 元動画の音声はそのまま使用されます")
                    
                    with st.expander("🎵 BGMを追加", expanded=False):
                        bgm_file = st.file_uploader("BGM音楽ファイル（MP3, WAV）", type=['mp3', 'wav'], key="new_bgm")
                        
                        if bgm_file:
                            # BGMを保存
                            bgm_path = TEMP_VIDEOS_DIR / f"bgm_{bgm_file.name}"
                            with open(bgm_path, 'wb') as f:
                                f.write(bgm_file.getbuffer())
                            
                            st.write("**🎵 BGMプレビュー:**")
                            st.audio(bgm_path)
                            st.session_state.pro_audio['bgm_path'] = str(bgm_path)
                            st.success(f"✅ BGM: {bgm_file.name}")
                            st.info("💡 BGMは自動的に動画の長さに合わせてループします")
                        
                        if st.session_state.pro_audio['bgm_path']:
                            st.markdown("---")
                            st.write("**⏱️ BGM挿入タイミング設定**")
                            
                            # BGMの開始・終了時間をスライダーで設定
                            bgm_time_range = st.slider(
                                "BGM再生範囲（秒）",
                                min_value=0.0,
                                max_value=clip_duration,
                                value=(0.0, clip_duration),
                                step=0.1,
                                key="bgm_time_slider",
                                help="BGMを再生する時間範囲を指定します。動画の途中から開始したり、途中で終了させることができます。"
                            )
                            
                            bgm_start, bgm_end = bgm_time_range
                            st.session_state.pro_audio['bgm_start'] = bgm_start
                            st.session_state.pro_audio['bgm_end'] = bgm_end
                            st.caption(f"📌 {bgm_start:.1f}秒 〜 {bgm_end:.1f}秒 （長さ: {bgm_end - bgm_start:.1f}秒）")
                            
                            st.markdown("---")
                            st.write("**🔊 音量バランス**")
                            
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
                            
                            st.markdown("---")
                            st.write("**🎚️ フェードエフェクト**")
                            
                            col_fade1, col_fade2 = st.columns(2)
                            with col_fade1:
                                fade_in = st.slider(
                                    "フェードイン（秒）",
                                    0.0, 5.0,
                                    st.session_state.pro_audio.get('bgm_fade_in', 0.0),
                                    0.1,
                                    key="audio_fade_in",
                                    help="BGMの開始時にフェードインする時間"
                                )
                                st.session_state.pro_audio['bgm_fade_in'] = fade_in
                            
                            with col_fade2:
                                fade_out = st.slider(
                                    "フェードアウト（秒）",
                                    0.0, 5.0,
                                    st.session_state.pro_audio.get('bgm_fade_out', 0.0),
                                    0.1,
                                    key="audio_fade_out",
                                    help="BGMの終了時にフェードアウトする時間"
                                )
                                st.session_state.pro_audio['bgm_fade_out'] = fade_out
                            
                            if fade_in > 0 or fade_out > 0:
                                effects_text = []
                                if fade_in > 0:
                                    effects_text.append(f"📈 フェードイン: {fade_in:.1f}秒")
                                if fade_out > 0:
                                    effects_text.append(f"📉 フェードアウト: {fade_out:.1f}秒")
                                st.info(" | ".join(effects_text))
                            
                            st.markdown("---")
                            if st.button("🗑️ BGMを削除"):
                                st.session_state.pro_audio['bgm_path'] = None
                                st.rerun()
                    
                    
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
                        st.caption("📹 プレビュー動画（縮小表示）")
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
                        
                        # テキストレイヤー数
                        text_layers = [l for l in st.session_state.pro_layers if l['type'] == 'text']
                        st.metric("テキストレイヤー", len(text_layers))
                        
                        # ステッカーレイヤー数
                        sticker_layers = [l for l in st.session_state.pro_layers if l['type'] == 'sticker']
                        st.metric("ステッカーレイヤー", len(sticker_layers))
                        
                        # アニメーション数
                        animated_layers = [l for l in st.session_state.pro_layers if l.get('animation', 'none') != 'none']
                        if animated_layers:
                            st.metric("✨ アニメーション", f"{len(animated_layers)}個")
                        
                        # BGM情報
                        if st.session_state.pro_audio['bgm_path']:
                            bgm_start = st.session_state.pro_audio.get('bgm_start', 0.0)
                            bgm_end = st.session_state.pro_audio.get('bgm_end', clip_duration)
                            st.metric("🎵 BGM", f"{bgm_start:.1f}秒〜{bgm_end:.1f}秒")
                        else:
                            st.metric("BGM", "なし")
                        
                        # エフェクト
                        st.metric("エフェクト", "適用中" if st.session_state.pro_effects['speed'] != 1.0 or st.session_state.pro_effects['brightness'] != 0.0 else "なし")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
        # ダイアログ関数定義（ifブロック内に配置）
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
                        st.session_state.clip_start = st.session_state.dialog_adjusted_start  # 動画編集用
                        st.session_state.clip_end = st.session_state.dialog_adjusted_end  # 動画編集用
                        st.session_state.scene_preview_dialog_open = False
                        st.session_state.scene_selected = True
                        st.session_state.show_edit_guidance = True  # 動画編集タブで案内を表示
                        st.session_state.switch_to_edit_tab = True  # タブ切り替えフラグ
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
    
    else:
        st.info("👈 サイドバーから動画を取得し、文字起こしを実行してください。")
    
    # フッター
    st.markdown("---")
    st.markdown("**Context Cut Pro** - Powered by Streamlit, Whisper, ChromaDB, FFmpeg")


if __name__ == "__main__":
    main()
