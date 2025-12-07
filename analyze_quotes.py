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
    
    print("=== 원본 일부 ===")
    print(clean_article[:300])
    
    print("\n=== 따옴표 문자 분석 ===")
    # 따옴표 주변 문자 분석
    pattern = r'(["\"])([^"\'"]{0,80}?)\1'
    matches = re.finditer(pattern, clean_article)
    
    found_quotes = []
    for m in matches:
        quote_char = m.group(1)
        text = m.group(2)
        code = ord(quote_char)
        found_quotes.append({
            'char': quote_char,
            'code': code,
            'text': text[:50],
        })
    
    print(f"찾은 인용문: {len(found_quotes)}개")
    
    for i, q in enumerate(found_quotes[:15]):
        print(f"{i+1}. 문자='{q['char']}' (U+{q['code']:04X}) | 텍스트: {q['text']}")
    
    # 특정 문자의 16진수 코드 보기
    print("\n=== 첫 500자의 16진수 ===")
    sample = clean_article[:500]
    for i, char in enumerate(sample):
        if ord(char) > 127 or char in '"\'':  # 비ASCII 또는 따옴표
            print(f"위치 {i}: '{char}' = U+{ord(char):04X}")
