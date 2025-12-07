"""
Quote Origin Frontend Client

여러 개의 인용문을 받아서 백엔드 API에 전송하고 결과를 반환하는 클라이언트
"""

import requests
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

@dataclass
class Quote:
    """인용문 데이터 클래스"""
    quote_id: str
    quote_content: str
    article_text: Optional[str] = None
    article_date: Optional[str] = None


@dataclass
class OriginResult:
    """원문 검색 결과"""
    quote_id: str
    quote_content: str
    candidate_index: int
    original_span: str
    similarity_score: float
    source_url: str
    error: Optional[str] = None


class QuoteOriginClient:
    """Quote Origin API 클라이언트"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Args:
            api_url: API 서버 URL (기본값: http://localhost:8000)
        """
        self.api_url = api_url
        self.endpoint = f"{api_url}/api/find-origin"
        
    def process_single_quote(self, quote: Quote, top_matches: int = 3) -> Optional[OriginResult]:
        """
        단일 인용문 처리
        
        Args:
            quote: Quote 객체
            top_matches: 반환할 최고 점수 후보 1개
            
        Returns:
            OriginResult 또는 None
        """
        payload = {
            "quote_id": quote.quote_id,
            "quote_content": quote.quote_content,
            "article_text": quote.article_text or "",
            "article_date": quote.article_date,
            "top_matches": top_matches,
            "debug": False
        }
        
        try:
            response = requests.post(self.endpoint, json=payload, timeout=120)
            
            if response.status_code == 200:
                data = response.json()
                
                # 최고 점수 후보 반환
                if data.get("best_candidate"):
                    best = data["best_candidate"]
                    return OriginResult(
                        quote_id=quote.quote_id,
                        quote_content=quote.quote_content,
                        candidate_index=best["candidate_index"],
                        original_span=best["original_span"],
                        similarity_score=best["similarity_score"],
                        source_url=best["source_url"],
                        error=None
                    )
                elif data.get("error"):
                    return OriginResult(
                        quote_id=quote.quote_id,
                        quote_content=quote.quote_content,
                        candidate_index=-1,
                        original_span="",
                        similarity_score=0.0,
                        source_url="",
                        error=data["error"]
                    )
            else:
                return OriginResult(
                    quote_id=quote.quote_id,
                    quote_content=quote.quote_content,
                    candidate_index=-1,
                    original_span="",
                    similarity_score=0.0,
                    source_url="",
                    error=f"HTTP {response.status_code}"
                )
                
        except requests.exceptions.ConnectionError:
            return OriginResult(
                quote_id=quote.quote_id,
                quote_content=quote.quote_content,
                candidate_index=-1,
                original_span="",
                similarity_score=0.0,
                source_url="",
                error="Connection failed. API server not running?"
            )
        except requests.exceptions.Timeout:
            return OriginResult(
                quote_id=quote.quote_id,
                quote_content=quote.quote_content,
                candidate_index=-1,
                original_span="",
                similarity_score=0.0,
                source_url="",
                error="Request timeout (>120s)"
            )
        except Exception as e:
            return OriginResult(
                quote_id=quote.quote_id,
                quote_content=quote.quote_content,
                candidate_index=-1,
                original_span="",
                similarity_score=0.0,
                source_url="",
                error=str(e)
            )
    
    def process_quotes(self, quotes: List[Quote], top_matches: int = 3) -> List[OriginResult]:
        """
        여러 인용문 일괄 처리
        
        Args:
            quotes: Quote 객체 리스트
            top_matches: 반환할 최고 점수 후보 1개
            
        Returns:
            OriginResult 리스트
        """
        results = []
        
        for i, quote in enumerate(quotes, 1):
            print(f"[{i}/{len(quotes)}] Processing: {quote.quote_content[:50]}...")
            result = self.process_single_quote(quote, top_matches)
            results.append(result)
            
            # API 부하 분산
            if i < len(quotes):
                time.sleep(2)
        
        return results
    
    @staticmethod
    def format_result(result: OriginResult) -> Dict:
        """결과를 JSON 직렬화 가능한 딕셔너리로 변환"""
        return {
            "quote_id": result.quote_id,
            "quote_content": result.quote_content,
            "result": {
                "candidate_index": result.candidate_index,
                "original_span": result.original_span,
                "similarity_score": result.similarity_score,
                "source_url": result.source_url
            } if result.error is None else None,
            "error": result.error
        }


def main():
    """사용 예제"""
    
    # 클라이언트 초기화
    client = QuoteOriginClient(api_url="http://localhost:8000")
    
    # 테스트용 인용문들
    quotes = [
        Quote(
            quote_id="quote_001",
            quote_content="수단은 지구상에서 가장 폭력적인 지역이다",
            article_text="트럼프 대통령은 수단은 지구상에서 가장 폭력적인 지역이라고 말했다.",
            article_date="2025-11-20"
        ),
        Quote(
            quote_id="quote_002",
            quote_content="한국, 위안부 문제에 집착",
            article_text="트럼프 전 대통령이 한국이 위안부 문제에 집착한다고 비판했다.",
            article_date="2025-12-05"
        ),
        Quote(
            quote_id="quote_003",
            quote_content="경제가 중요하다",
            article_text="대통령은 경제가 중요하다고 강조했다.",
            article_date="2025-12-05"
        )
    ]
    
    print("="*80)
    print("Quote Origin Frontend Client - Test")
    print("="*80)
    
    # 여러 인용문 처리
    results = client.process_quotes(quotes)
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    # 결과 출력
    for result in results:
        formatted = client.format_result(result)
        print(f"\n[{result.quote_id}]")
        print(f"  Quote: {result.quote_content}")
        
        if result.error:
            print(f"  ❌ Error: {result.error}")
        else:
            print(f"  ✅ Found!")
            print(f"     Score: {result.similarity_score:.4f}")
            print(f"     Span: {result.original_span[:100]}...")
            print(f"     URL: {result.source_url}")
    
    # JSON으로 저장
    output = [client.format_result(r) for r in results]
    
    with open("quote_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to quote_results.json")
    
    # 요약 통계
    success_count = sum(1 for r in results if r.error is None)
    error_count = len(results) - success_count
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Error: {error_count}")
    
    if success_count > 0:
        avg_score = sum(r.similarity_score for r in results if r.error is None) / success_count
        print(f"Average Score: {avg_score:.4f}")


if __name__ == "__main__":
    main()
