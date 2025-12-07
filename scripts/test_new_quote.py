"""
새로운 인용문 테스트
"""
import asyncio
import json
from qdd2.backend_api import find_quote_origin, QuoteRequest

async def main():
    payload = {
        'quote_id': 'quote_002',
        'quote_content': '한국, 위안부 문제에 집착',
        'article_text': '이재명 대통령과 정상회담한 도널드 트럼프 미국 대통령이 “한국이 위안부 문제에 매우 집착”해서 한·일 관계 개선에 어려움을 겪었다고 말했다.',
        'top_matches': 5
    }

    print('='*80)
    print('TEST: Quote Origin API (새로운 인용문)')
    print('='*80)
    print('\nRequest:')
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # 요청 객체 생성
    request = QuoteRequest(**payload)
    
    # 함수 호출
    print('\n실행 중...')
    result = await find_quote_origin(request)
    
    print(f'\nStatus: Success')
    print('\nResponse:')
    result_dict = result.model_dump()
    result_str = json.dumps(result_dict, indent=2, ensure_ascii=False)
    print(result_str[:3000])

    if result.best_candidate:
        print('\n' + '='*80)
        print('✅ BEST CANDIDATE FOUND')
        print('='*80)
        best = result.best_candidate
        print(f'candidate_index: {best.candidate_index}')
        print(f'similarity_score: {best.similarity_score:.4f}')
        print(f'original_span: {best.original_span[:300]}...')
        print(f'source_url: {best.source_url}')
        
        print('\n' + '='*80)
        print('ALL CANDIDATES')
        print('='*80)
        if result.candidates:
            for i, cand in enumerate(result.candidates):
                print(f"\n[{i}] Score: {cand.similarity_score:.4f}")
                print(f"    URL: {cand.source_url}")
                print(f"    Span: {cand.original_span[:150]}...")
    else:
        print(f'\n⚠️ Error: {result.error}')

if __name__ == "__main__":
    asyncio.run(main())
