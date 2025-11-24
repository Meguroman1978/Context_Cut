#!/usr/bin/env python3
"""
吹き出し画像生成スクリプト
様々な形状の吹き出し画像をPNG形式で生成
"""
from PIL import Image, ImageDraw
import math
from pathlib import Path

# 出力ディレクトリ
BALLOON_DIR = Path("balloon_images")
BALLOON_DIR.mkdir(exist_ok=True)

def create_oval_balloon(width=800, height=400, color=(255, 255, 255, 250), outline_width=3):
    """楕円形吹き出し"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 楕円を描画
    draw.ellipse([10, 10, width-10, height-10], fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    # しっぽを追加（下中央）
    tail_points = [
        (width//2 - 30, height - 10),
        (width//2, height - 5),
        (width//2 + 30, height - 10)
    ]
    draw.polygon(tail_points, fill=color, outline=(0, 0, 0, 255))
    
    return img

def create_round_rect_balloon(width=800, height=400, radius=50, color=(255, 255, 255, 250), outline_width=3):
    """角丸長方形吹き出し"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 角丸長方形を描画
    draw.rounded_rectangle([10, 10, width-10, height-10], radius=radius, fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    # しっぽを追加（下中央）
    tail_points = [
        (width//2 - 30, height - 10),
        (width//2, height - 5),
        (width//2 + 30, height - 10)
    ]
    draw.polygon(tail_points, fill=color, outline=(0, 0, 0, 255))
    
    return img

def create_cloud_balloon(width=800, height=400, color=(255, 255, 255, 250), outline_width=3):
    """雲形吹き出し"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 複数の円を重ねて雲の形を作る
    circle_params = [
        (width*0.2, height*0.3, width*0.25),
        (width*0.35, height*0.2, width*0.28),
        (width*0.55, height*0.2, width*0.30),
        (width*0.75, height*0.3, width*0.28),
        (width*0.5, height*0.5, width*0.35),
    ]
    
    for cx, cy, r in circle_params:
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    # しっぽを追加（下中央）
    tail_points = [
        (width//2 - 20, height - 30),
        (width//2, height - 5),
        (width//2 + 20, height - 30)
    ]
    draw.polygon(tail_points, fill=color, outline=(0, 0, 0, 255))
    
    return img

def create_star_balloon(width=800, height=400, color=(255, 255, 255, 250), outline_width=3):
    """星型吹き出し（トゲトゲ）"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 星型（ギザギザ）の頂点を計算
    center_x, center_y = width // 2, height // 2
    outer_radius = min(width, height) // 2 - 20
    inner_radius = outer_radius * 0.6
    num_points = 12
    
    points = []
    for i in range(num_points * 2):
        angle = math.pi * i / num_points - math.pi / 2
        if i % 2 == 0:
            r = outer_radius
        else:
            r = inner_radius
        x = center_x + r * math.cos(angle)
        y = center_y + r * math.sin(angle)
        points.append((x, y))
    
    draw.polygon(points, fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    return img

def create_explosion_balloon(width=800, height=400, color=(255, 255, 0, 250), outline_width=3):
    """爆発形吹き出し"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 爆発型（大きなトゲトゲ）
    center_x, center_y = width // 2, height // 2
    outer_radius = min(width, height) // 2 - 20
    inner_radius = outer_radius * 0.5
    num_points = 8
    
    points = []
    for i in range(num_points * 2):
        angle = math.pi * i / num_points - math.pi / 2
        if i % 2 == 0:
            r = outer_radius
        else:
            r = inner_radius
        x = center_x + r * math.cos(angle)
        y = center_y + r * math.sin(angle)
        points.append((x, y))
    
    draw.polygon(points, fill=color, outline=(255, 128, 0, 255), width=outline_width)
    
    return img

def create_heart_balloon(width=800, height=400, color=(255, 192, 203, 250), outline_width=3):
    """ハート形吹き出し"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # ハート形の座標を計算
    center_x, center_y = width // 2, height // 2
    scale = min(width, height) // 3
    
    points = []
    for t in range(0, 360, 5):
        rad = math.radians(t)
        # ハートの数式
        x = 16 * math.sin(rad) ** 3
        y = -(13 * math.cos(rad) - 5 * math.cos(2*rad) - 2 * math.cos(3*rad) - math.cos(4*rad))
        points.append((center_x + x * scale / 16, center_y + y * scale / 16))
    
    draw.polygon(points, fill=color, outline=(255, 0, 128, 255), width=outline_width)
    
    return img

def create_square_balloon(width=800, height=400, color=(255, 255, 255, 250), outline_width=3):
    """角張った長方形吹き出し"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 長方形を描画
    draw.rectangle([10, 10, width-10, height-10], fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    # しっぽを追加（下中央）
    tail_points = [
        (width//2 - 30, height - 10),
        (width//2, height - 5),
        (width//2 + 30, height - 10)
    ]
    draw.polygon(tail_points, fill=color, outline=(0, 0, 0, 255))
    
    return img

def create_thought_balloon(width=800, height=400, color=(255, 255, 255, 250), outline_width=3):
    """考え事吹き出し（複数の円）"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # メイン楕円
    draw.ellipse([10, 10, width-10, height-60], fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    # 小さい円（しっぽ代わり）
    draw.ellipse([width//2 - 40, height - 70, width//2 - 10, height - 40], fill=color, outline=(0, 0, 0, 255), width=outline_width)
    draw.ellipse([width//2 - 25, height - 40, width//2 - 5, height - 20], fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    return img

def create_scream_balloon(width=800, height=400, color=(255, 255, 255, 250), outline_width=3):
    """叫び吹き出し（ギザギザ長方形）"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # ギザギザの辺を持つ多角形
    points = []
    zigzag_height = 20
    
    # 上辺（ギザギザ）
    for x in range(20, width-20, 40):
        points.append((x, 10))
        points.append((x + 20, 10 + zigzag_height))
    points.append((width-20, 10))
    
    # 右辺（ギザギザ）
    for y in range(20, height-20, 40):
        points.append((width-10, y))
        points.append((width-10-zigzag_height, y + 20))
    points.append((width-10, height-20))
    
    # 下辺（ギザギザ）
    for x in range(width-20, 20, -40):
        points.append((x, height-10))
        points.append((x - 20, height-10-zigzag_height))
    points.append((20, height-10))
    
    # 左辺（ギザギザ）
    for y in range(height-20, 20, -40):
        points.append((10, y))
        points.append((10+zigzag_height, y - 20))
    
    draw.polygon(points, fill=color, outline=(0, 0, 0, 255), width=outline_width)
    
    return img

# 全ての吹き出しを生成
def generate_all_balloons():
    """全ての吹き出し画像を生成"""
    
    balloons = {
        # 白系
        "oval_white.png": create_oval_balloon(color=(255, 255, 255, 250)),
        "round_rect_white.png": create_round_rect_balloon(radius=50, color=(255, 255, 255, 250)),
        "cloud_white.png": create_cloud_balloon(color=(255, 255, 255, 250)),
        "star_white.png": create_star_balloon(color=(255, 255, 255, 250)),
        "square_white.png": create_square_balloon(color=(255, 255, 255, 250)),
        "thought_white.png": create_thought_balloon(color=(255, 255, 255, 250)),
        "scream_white.png": create_scream_balloon(color=(255, 255, 255, 250)),
        
        # 黒系
        "oval_black.png": create_oval_balloon(color=(50, 50, 50, 230)),
        "round_rect_black.png": create_round_rect_balloon(radius=50, color=(50, 50, 50, 230)),
        "cloud_black.png": create_cloud_balloon(color=(50, 50, 50, 230)),
        "star_black.png": create_star_balloon(color=(50, 50, 50, 230)),
        "square_black.png": create_square_balloon(color=(50, 50, 50, 230)),
        "thought_black.png": create_thought_balloon(color=(50, 50, 50, 230)),
        "scream_black.png": create_scream_balloon(color=(50, 50, 50, 230)),
        
        # カラー系
        "explosion_yellow.png": create_explosion_balloon(color=(255, 255, 0, 250)),
        "explosion_red.png": create_explosion_balloon(color=(255, 100, 100, 250)),
        "heart_pink.png": create_heart_balloon(color=(255, 192, 203, 250)),
        "round_rect_blue.png": create_round_rect_balloon(radius=50, color=(173, 216, 230, 250)),
        "round_rect_green.png": create_round_rect_balloon(radius=50, color=(144, 238, 144, 250)),
    }
    
    print(f"吹き出し画像を生成中... 保存先: {BALLOON_DIR.absolute()}")
    for filename, balloon_img in balloons.items():
        output_path = BALLOON_DIR / filename
        balloon_img.save(output_path, "PNG")
        print(f"  ✓ {filename}")
    
    print(f"\n✅ {len(balloons)}個の吹き出し画像を生成完了！")

if __name__ == "__main__":
    generate_all_balloons()
