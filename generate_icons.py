"""
크롬 익스텐션 아이콘 생성
SVG를 PNG로 변환
"""

from PIL import Image, ImageDraw
import io

def create_icon(size):
    """
    크롬 익스텐션 아이콘 생성
    간단한 큐 모양 아이콘 (Quote의 Q)
    """
    # 흰색 배경에 파란색 원
    img = Image.new('RGBA', (size, size), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # 배경
    bg_color = (61, 90, 254)  # 파란색
    draw.rectangle(
        [(0, 0), (size, size)],
        fill=bg_color
    )
    
    # 흰색 원 (배경)
    margin = int(size * 0.1)
    draw.ellipse(
        [(margin, margin), (size - margin, size - margin)],
        fill=(255, 255, 255)
    )
    
    # 파란색 Q 글자 그리기 (간단한 형태)
    text_color = bg_color
    text_size = int(size * 0.6)
    
    # 중앙에 "Q" 텍스트 추가
    try:
        # 기본 폰트 사용
        from PIL import ImageFont
        font = ImageFont.load_default()
        text = "Q"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        draw.text((x, y), text, fill=text_color, font=font)
    except:
        # 폰트가 없으면 간단한 도형으로 대체
        pass
    
    return img

def main():
    """아이콘 생성"""
    sizes = [16, 48, 128]
    base_path = r"c:\08_QDD3\quote-origin-pipeline\chrome_extension\images\icon"
    
    print("크롬 익스텐션 아이콘 생성 중...")
    
    for size in sizes:
        img = create_icon(size)
        filename = f"{base_path}-{size}.png"
        img.save(filename)
        print(f"✓ {filename}")
    
    print("\n✅ 모든 아이콘이 생성되었습니다!")

if __name__ == "__main__":
    main()
