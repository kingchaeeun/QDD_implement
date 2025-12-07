import re

# 기사.html 읽기
with open('기사.html', 'r', encoding='utf-8') as f:
    content = f.read()

# article 태그 찾기
match = re.search(r'<article[^>]*>(.*?)</article>', content, re.DOTALL)
if match:
    article = match.group(1)
    
    # 스트립 태그
    clean_article = re.sub(r'<[^>]+>', '', article)
    
    print("=== 원본 첫 300자 ===")
    print(repr(clean_article[:300]))
    
    print("\n=== 따옴표 문자 찾기 ===")
    # U+201C와 U+201D 찾기
    for i, char in enumerate(clean_article[:300]):
        code = ord(char)
        if code in [0x201C, 0x201D, 34, 39]:  # 곡따옴표 또는 일반 따옴표
            print(f"위치 {i}: '{char}' = U+{code:04X}")
    
    # 직접 U+201C 문자로 검색
    print(f"\n=== U+201C (왼쪽 곡따옴표) 검색 ===")
    left_quote = '\u201c'
    right_quote = '\u201d'
    
    print(f"left_quote = {repr(left_quote)}, right_quote = {repr(right_quote)}")
    print(f"clean_article에 포함? left: {left_quote in clean_article}, right: {right_quote in clean_article}")
    
    # 곡따옴표로 직접 검색
    if left_quote in clean_article:
        pattern = f'{left_quote}([\\s\\S]*?){right_quote}'
        matches = re.finditer(pattern, clean_article)
        found = []
        for m in matches:
            text = m.group(1).strip()
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 10:
                found.append(text)
        
        print(f"찾은 인용문: {len(found)}개")
        for i, quote in enumerate(found[:10]):
            print(f"{i+1}. {quote[:70]}...")

