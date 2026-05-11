# Water Treatment Graph RAG

수처리 도메인(먹는물 수질기준·정수처리 공정·수도법) 특화 **Graph RAG** 시스템.  
지식 그래프(Neo4j) + 벡터 검색을 병렬로 실행하는 하이브리드 검색으로 단순 벡터 RAG 대비 멀티홉 질의 응답 품질을 향상시킵니다.

---

## 아키텍처

<img width="2816" height="1536" alt="Gemini_Generated_Image_r9t2z8r9t2z8r9t2" src="https://github.com/user-attachments/assets/da24f414-09b1-49ad-9855-aa268a3c2462" />


---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| API | FastAPI 0.115, SSE 스트리밍 |
| LLM | OpenAI GPT-4o-mini |
| 그래프 DB | Neo4j 5.20 Community |
| 그래프 추출 | LangChain LLMGraphTransformer |
| 임베딩 | KR-SBERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS) |
| 캐시 | 인메모리 LRU (TTL 1시간) |
| 프론트엔드 | Next.js 14 + D3.js (force-directed graph) |
| 인프라 | Docker Compose (Neo4j) |

---

## 도메인 온톨로지

수처리 법령·공정·사고를 표현하는 20종 노드와 18종 관계로 구성된 한국어 온톨로지.

```
노드 타입 (20종)
├── 법제:     법령 · 조문 · 고시
├── 수질기준: 건강항목 · 심미적항목 · 소독부산물 · 미생물항목
├── 수치:     수질기준값 · 검사주기 · 검사방법
├── 시설:     정수장 · 공정 · 소독방법 · 약품
├── 기관:     기관 · 지역
└── 사고:     수질사고 · 위반항목 · 처벌규정

관계 타입 (18종)
  규정한다 · 포함한다 · 기준값이다 · 검사주기이다
  처리한다 · 사용한다 · 적용한다 · 운영한다
  위반한다 · 초과한다 · 처벌받는다 · 원인이다 ...
```

---

## 빠른 시작

### 1. 환경 설정

```bash
git clone https://github.com/teriyakki-jin/Graph-RAG-with-water.git
cd Graph-RAG-with-water

cp .env.example .env
# .env에서 OPENAI_API_KEY 설정
```

### 2. Neo4j 실행

```bash
docker compose up -d
# Neo4j Browser: http://localhost:7474
```

### 3. Python 환경

```bash
pip install -r requirements.txt
```

### 4. 지식 그래프 구축 (오프라인 파이프라인)

```bash
python -m pipeline.run --source data/docs
```

```
문서 6종 → 청크 25개 → 노드 247개 / 관계 194개
```

### 5. API 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

### 6. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

---

## 질의 예시

### 단순 기준값 조회

```bash
curl -X POST http://localhost:8888/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "먹는물의 탁도 기준은 얼마인가?"}'
```

```json
{
  "answer": "먹는물의 탁도 기준은 0.5 NTU 이하입니다. (먹는물 수질기준 제5조)",
  "cypher_query": "MATCH (n {id: '탁도'})-[:기준값이다]->(v) RETURN v.id",
  "sources": ["data/docs/먹는물수질기준_전체.txt"]
}
```

### 멀티홉 비교 질의

```
"오존 소독과 UV 소독의 차이점과, 낙동강 정수장이 이 방식을 도입한 이유는?"
```

→ 그래프 경로: `낙동강 정수장 → 적용한다 → 오존소독 → 사용한다 → 크립토스포리디움 제거`  
→ 벡터 청크: 1991년 페놀 사고 이후 고도처리 도입 기록  
→ 두 컨텍스트를 통합하여 연결된 답변 생성

### SSE 스트리밍

```javascript
const source = new EventSource(
  `/api/v1/query/stream?question=탁도 기준은?`
);
source.addEventListener("token", (e) => {
  const { text } = JSON.parse(e.data);
  // 토큰 단위로 UI 업데이트
});
```

---

## 프로젝트 구조

```
.
├── app/                        # FastAPI 백엔드
│   ├── api/v1/                 # 엔드포인트 (query, graph, health)
│   ├── core/                   # config, cache, logging, exceptions
│   ├── services/               # hybrid_retriever, graph_retriever, vector_retriever
│   └── repositories/           # graph_repository (Cypher 쿼리)
│
├── pipeline/                   # 오프라인 그래프 구축
│   ├── loaders/                # document_loader, chunker
│   ├── extractors/             # graph_extractor (LLMGraphTransformer)
│   └── graph/                  # neo4j_writer
│
├── evaluation/                 # 벤치마크 평가
│   ├── qa_pairs.json           # 도메인 Q&A 20문항
│   ├── metrics.py              # 5가지 평가 지표
│   └── evaluator.py            # 평가 실행기
│
├── frontend/                   # Next.js + D3.js
│   └── src/
│       ├── components/         # GraphViewer, QueryPanel, NodeDetail
│       └── hooks/              # useGraphSimulation
│
├── data/docs/                  # 수처리 도메인 문서 6종
│   ├── 수도법_발췌.txt
│   ├── 먹는물수질기준_전체.txt
│   ├── 정수처리공정.txt
│   ├── 소독공정_상세.txt
│   ├── 수질사고사례.txt
│   └── 수질사고_처벌규정.txt
│
└── tests/                      # 유닛 + 통합 테스트 (32개)
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/query` | 동기 질의 응답 (캐시 적용) |
| `GET` | `/api/v1/query/stream` | SSE 스트리밍 응답 |
| `GET` | `/api/v1/graph/nodes` | 전체 노드 목록 조회 |
| `GET` | `/api/v1/graph/neighbors/{id}` | 노드 이웃 관계 조회 |
| `GET` | `/api/v1/health` | 헬스체크 (Neo4j 포함) |

---

## 벤치마크 평가

RAGAS에서 영감을 받은 5가지 지표로 자체 평가 프레임워크를 구현했습니다.

| 지표 | 설명 | 가중치 |
|------|------|--------|
| Keyword Recall | 정답 키워드가 답변에 포함된 비율 | 35% |
| Faithfulness | 답변이 컨텍스트에 근거하는 비율 | 25% |
| Numeric Accuracy | 수치·단위 정확도 (도메인 특화) | 20% |
| Context Precision | 정답 키워드가 컨텍스트에 있는 비율 | 10% |
| Answer Relevancy | 질문-답변 키워드 Jaccard 유사도 | 10% |

```bash
# 전체 평가 실행
python -m evaluation.evaluator

# 카테고리 필터
python -m evaluation.evaluator --difficulty hard
python -m evaluation.evaluator --category 사고_사례
```

평가셋 구성: 총 20문항 × 5카테고리 (기준값·소독비교·법령·사고사례·멀티홉)

---

## 테스트

```bash
# 유닛 테스트 (32개)
pytest tests/unit/ -v

# 통합 테스트 (서버 실행 필요)
pytest tests/integration/ -v

# 커버리지
pytest tests/unit/ --cov=app --cov=evaluation --cov-report=term-missing
```

---

## Why Graph RAG?

순수 벡터 RAG와 달리 Graph RAG는 **구조화된 관계**를 활용합니다.

```
질문: "1991년 사고 이후 낙동강 정수장이 도입한 소독 방식의 부산물 기준은?"

벡터 RAG: 개별 문서 청크에서 유사 문장 검색 → 연결 정보 누락 가능
Graph RAG: 수질사고 → 원인이다 → 낙동강정수장
                             → 적용한다 → 오존소독
                                          → 기준값이다 → 브로모산염 0.01mg/L
           관계 체인을 따라 답변 재료 수집 → 연결된 맥락 제공
```

멀티홉 질의, 법령-수치-사고 간 연결 추론에서 벡터 단독 검색보다 정확도가 높습니다.
