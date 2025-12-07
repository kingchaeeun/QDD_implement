"""
백엔드 API 테스트 클라이언트
"""

import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"


def test_api_basic():
    """기본 API 테스트"""
    
    payload = {
        "quote_id": "quote_001",
        "quote_content": "수단은 지구상에서 가장 폭력적인 지역이다",
        "article_text": """
            트럼프 대통령은 이후 자신의 소셜미디어 트루스소셜에 
            "수단에서 엄청난 잔혹 행위가 벌어지고 있다"며 
            "수단은 지구상에서 가장 폭력적인 지역이자 동시에 매우 심각한 
            인도주의적 위기가 발생한 곳이다. 식량, 의료진 등 모든 것이 절실하다"는 글을 올렸다.
        """,
        "article_date": "2025-11-20",
        "top_matches": 5,
        "debug": False,
    }
    
    print("=" * 80)
    print("TEST 1: Basic Find Origin")
    print("=" * 80)
    print(f"\nRequest:")
    print(f"  quote_id: {payload['quote_id']}")
    print(f"  quote_content: {payload['quote_content']}")
    print(f"  article_date: {payload['article_date']}")
    print(f"\nSending request to {BASE_URL}/api/find-origin...")
    
    try:
        response = requests.post(f"{BASE_URL}/api/find-origin", json=payload, timeout=60)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("best_candidate"):
                best = result["best_candidate"]
                print("\n" + "=" * 80)
                print("BEST CANDIDATE")
                print("=" * 80)
                print(f"순위: {best['candidate_index']}")
                print(f"유사도: {best['similarity_score']:.4f}")
                print(f"원문: {best['original_span'][:200]}...")
                print(f"출처: {best['source_url']}")
                if best.get('best_sentence'):
                    print(f"중심문장: {best['best_sentence']}")
            
            if result.get("candidates"):
                print("\n" + "=" * 80)
                print(f"TOP 5 CANDIDATES (총 {len(result['candidates'])}개)")
                print("=" * 80)
                for cand in result["candidates"][:5]:
                    print(f"\n[{cand['candidate_index']}] 유사도: {cand['similarity_score']:.4f}")
                    print(f"    원문: {cand['original_span'][:100]}...")
                    print(f"    출처: {cand['source_url']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    
    except requests.exceptions.ConnectionError:
        print("\n❌ 연결 실패: API 서버가 실행 중인지 확인하세요.")
        print(f"   명령어: python -m qdd2.backend_api")
    except requests.exceptions.Timeout:
        print("\n⏱️ 요청 시간 초과 (60초). 검색 중일 수 있습니다.")
    except Exception as e:
        print(f"\n❌ 오류: {e}")


def test_api_debug():
    """디버그 모드로 API 테스트"""
    
    payload = {
        "quote_id": "quote_debug",
        "quote_content": "경제가 중요하다",
        "article_text": "대통령은 경제가 중요하다고 강조했다.",
        "debug": True,
        "top_matches": 3,
    }
    
    print("\n" + "=" * 80)
    print("TEST 2: Debug Mode")
    print("=" * 80)
    print(f"\nRequest with debug=True")
    
    try:
        response = requests.post(f"{BASE_URL}/api/find-origin", json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\nDebug Info:")
            if result.get("debug_info"):
                print(json.dumps(result["debug_info"], indent=2, ensure_ascii=False))
            
            print(f"\nError (if any): {result.get('error')}")
            print(f"Candidates found: {len(result.get('candidates', []))}")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ 연결 실패: API 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"\n❌ 오류: {e}")


def test_api_no_article_text():
    """article_text 없이 테스트 (에러 케이스)"""
    
    payload = {
        "quote_id": "quote_error",
        "quote_content": "테스트 인용문",
        # article_text 없음
    }
    
    print("\n" + "=" * 80)
    print("TEST 3: Missing article_text (Error Case)")
    print("=" * 80)
    
    try:
        response = requests.post(f"{BASE_URL}/api/find-origin", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nExpected Error:")
            print(f"  Error: {result.get('error')}")
            print(f"  Candidates: {len(result.get('candidates', []))}")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ 연결 실패: API 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"\n❌ 오류: {e}")


def test_health_check():
    """헬스 체크 테스트"""
    
    print("\n" + "=" * 80)
    print("TEST 0: Health Check")
    print("=" * 80)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ API is running:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"\n❌ Health check failed: {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 연결 실패: {BASE_URL} 에 접속할 수 없습니다.")
        print(f"\n서버를 시작하려면 다음 명령어를 실행하세요:")
        print(f"  python -m qdd2.backend_api")
        return False
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print("Quote Origin API - Client Test Suite")
    print("=" * 80)
    
    # 헬스 체크
    if not test_health_check():
        print("\n서버가 실행 중이 아닙니다. 먼저 서버를 시작하세요:")
        print("  python -m qdd2.backend_api")
        sys.exit(1)
    
    # 테스트 실행
    test_api_no_article_text()
    test_api_debug()
    test_api_basic()
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)
