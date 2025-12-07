"""
API 테스트 스크립트
"""
import requests
import json
import time

# 서버 시작 대기
time.sleep(3)

print("=" * 80)
print("TEST: Quote Origin API")
print("=" * 80)

payload = {
    "quote_id": "quote_001",
    "quote_content": "수단은 지구상에서 가장 폭력적인 지역이다",
    "article_text": "트럼프 대통령은 이후 자신의 소셜미디어 트루스소셜에 수단에서 엄청난 잔혹 행위가 벌어지고 있다며 수단은 지구상에서 가장 폭력적인 지역이자 동시에 매우 심각한 인도주의적 위기가 발생한 곳이다는 글을 올렸다.",
    "article_date": "2025-11-20",
    "top_matches": 3,
    "debug": False
}

print("\nRequest:")
print(json.dumps(payload, indent=2, ensure_ascii=False))

try:
    response = requests.post("http://localhost:8000/api/find-origin", json=payload, timeout=60)
    print(f"\n✅ Response Status: {response.status_code}")
    result = response.json()
    
    print("\nResult:")
    # 결과 출력 (처음 2000자)
    result_str = json.dumps(result, indent=2, ensure_ascii=False)
    print(result_str[:2000])
    
    if result.get("best_candidate"):
        print("\n" + "=" * 80)
        print("BEST CANDIDATE")
        print("=" * 80)
        best = result["best_candidate"]
        print(f"candidate_index: {best['candidate_index']}")
        print(f"similarity_score: {best['similarity_score']}")
        print(f"original_span: {best['original_span'][:300]}...")
        print(f"source_url: {best['source_url']}")
    
    if result.get("candidates"):
        print("\n" + "=" * 80)
        print(f"TOP {len(result['candidates'])} CANDIDATES")
        print("=" * 80)
        for cand in result["candidates"][:3]:
            print(f"\n[{cand['candidate_index']}] Score: {cand['similarity_score']:.4f}")
            print(f"    URL: {cand['source_url']}")
            print(f"    Span: {cand['original_span'][:100]}...")
    
    if result.get("error"):
        print(f"\n⚠️  Error: {result['error']}")

except requests.exceptions.ConnectionError as e:
    print(f"\n❌ Connection Error: 서버가 실행 중인지 확인하세요")
    print(f"   URL: http://localhost:8000")
except requests.exceptions.Timeout:
    print(f"\n⏱️ Timeout: 요청 시간 초과 (검색 중일 수 있습니다)")
except Exception as e:
    print(f"\n❌ Error: {e}")
