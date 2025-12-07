"""
크롬 익스텐션 API 테스트
"""

import requests
import json
import time

API_URL = "http://localhost:8000/api/find-origin"

test_quotes = [
    {
        "quote_id": "quote_1",
        "quote_content": "한국은 민주주의 국가입니다"
    },
    {
        "quote_id": "quote_2", 
        "quote_content": "기후 변화는 점점 심해지고 있습니다"
    },
    {
        "quote_id": "quote_3",
        "quote_content": "경제 성장률이 예상보다 높았습니다"
    }
]

def test_api():
    """API 테스트"""
    print("\n" + "=" * 70)
    print("크롬 익스텐션 API 테스트")
    print("=" * 70)
    
    # 헬스 체크
    try:
        response = requests.get("http://localhost:8000/health")
        print("\n✓ 헬스 체크 성공")
        print(f"  상태: {response.json()['status']}")
        print(f"  모드: {response.json()['mode']}")
    except Exception as e:
        print(f"\n✗ 헬스 체크 실패: {e}")
        return False
    
    # API 테스트
    print("\n" + "-" * 70)
    print("직접인용문 검색 테스트")
    print("-" * 70)
    
    for i, quote in enumerate(test_quotes, 1):
        print(f"\n테스트 {i}: {quote['quote_content'][:30]}...")
        
        try:
            response = requests.post(API_URL, json=quote, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ 응답 성공")
                print(f"    유사도: {result['similarity_score']:.1%}")
                print(f"    원문: {result['original_span'][:40]}...")
                print(f"    출처: {result['source_url']}")
            else:
                print(f"  ✗ 오류: {response.status_code}")
                print(f"    {response.text}")
        
        except requests.exceptions.Timeout:
            print(f"  ✗ 타임아웃 (10초 초과)")
        except requests.exceptions.ConnectionError:
            print(f"  ✗ 연결 오류")
        except Exception as e:
            print(f"  ✗ 오류: {e}")
        
        time.sleep(0.5)
    
    print("\n" + "=" * 70)
    print("✅ 테스트 완료!")
    print("=" * 70)
    print("\n다음 단계:")
    print("1. Chrome을 열고 chrome://extensions/ 방문")
    print("2. 개발자 모드 활성화")
    print("3. chrome_extension 폴더 로드")
    print("4. 네이버 뉴스 기사 방문 후 익스텐션 테스트")
    
    return True

if __name__ == "__main__":
    test_api()
