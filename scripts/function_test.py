"""
직접 함수 호출로 API 테스트
"""
import asyncio
import json
from qdd2.backend_api import find_quote_origin, QuoteRequest

async def main():
    payload = {
        'quote_id': 'quote_001',
        'quote_content': '수단은 지구상에서 가장 폭력적인 지역이다',
        'article_text': '트럼프 대통령은 수단은 지구상에서 가장 폭력적인 지역이라고 말했다.',
        'top_matches': 3
    }

    print('='*80)
    print('TEST: Quote Origin API (Direct Function Call)')
    print('='*80)
    print('\nRequest:')
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # 요청 객체 생성
    request = QuoteRequest(**payload)
    
    # 함수 호출
    result = await find_quote_origin(request)
    
    print(f'\nStatus: Success')
    print('\nResponse:')
    result_dict = result.dict()
    result_str = json.dumps(result_dict, indent=2, ensure_ascii=False)
    print(result_str[:2000])

    if result.best_candidate:
        print('\n' + '='*80)
        print('✅ BEST CANDIDATE FOUND')
        print('='*80)
        best = result.best_candidate
        print(f'candidate_index: {best.candidate_index}')
        print(f'similarity_score: {best.similarity_score}')
        print(f'original_span: {best.original_span[:200]}...')
        print(f'source_url: {best.source_url}')
    else:
        print(f'\n⚠️ Error: {result.error}')

if __name__ == "__main__":
    asyncio.run(main())
