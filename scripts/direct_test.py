"""
TestClient를 사용한 API 직접 테스트
"""
from qdd2.backend_api import app
from fastapi.testclient import TestClient
import json

client = TestClient(app)

payload = {
    'quote_id': 'quote_001',
    'quote_content': '수단은 지구상에서 가장 폭력적인 지역이다',
    'article_text': '트럼프 대통령은 수단은 지구상에서 가장 폭력적인 지역이라고 말했다.',
    'top_matches': 3
}

print('='*80)
print('TEST: Quote Origin API (TestClient)')
print('='*80)
print('\nRequest:')
print(json.dumps(payload, indent=2, ensure_ascii=False))

response = client.post('/api/find-origin', json=payload)
print(f'\nStatus Code: {response.status_code}')
result = response.json()

print('\nResponse:')
result_str = json.dumps(result, indent=2, ensure_ascii=False)
print(result_str[:2000])

if result.get('best_candidate'):
    best = result['best_candidate']
    print('\n' + '='*80)
    print('✅ BEST CANDIDATE FOUND')
    print('='*80)
    candidate_index = best['candidate_index']
    similarity_score = best['similarity_score']
    original_span = best['original_span'][:200]
    print(f'candidate_index: {candidate_index}')
    print(f'similarity_score: {similarity_score}')
    print(f'original_span: {original_span}...')
else:
    error = result.get('error')
    print(f'\n⚠️ Error: {error}')
