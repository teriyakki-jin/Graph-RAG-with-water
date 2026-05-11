# 수처리 법령으로 Graph RAG 포트폴리오 만들기 — "왜 Neo4j인가"에 답하기까지

> FastAPI + Neo4j + LangChain으로 지식 그래프 기반 RAG 시스템을 구축하면서 겪은 설계 고민과 삽질 기록

![메인 화면](https://raw.githubusercontent.com/teriyakki-jin/Graph-RAG-with-water/master/screenshot_main.png)
*지식 그래프 시각화(좌) + 질의응답 패널(우)로 구성된 메인 UI*

---

## 왜 Graph RAG인가

RAG(Retrieval-Augmented Generation)를 공부하다 보면 자연스럽게 이런 질문이 생깁니다.

> "벡터 검색만으로 충분하지 않나?"

솔직히 말하면, 단순 질의에서는 충분합니다. 하지만 이런 질문은 어떨까요?

```
"1991년 낙동강 사고 이후 도입된 소독 방식에서 생성되는 부산물의 수질기준은?"
```

이 질문에 답하려면 세 가지 정보가 **연결**되어야 합니다.

```
수질사고(낙동강 페놀, 1991)
    → 원인이다 → 낙동강 정수장 처리 강화
    → 적용한다 → 오존 소독
    → 생성한다 → 브로모산염(BrO₃⁻)
    → 기준값이다 → 0.01 mg/L 이하
```

벡터 검색은 각 정보가 **서로 다른 문서 청크**에 흩어져 있으면 연결하지 못합니다. 그래프는 이 관계 체인을 탐색할 수 있습니다.

이것이 이 프로젝트를 Graph RAG로 만든 이유입니다.

---

## 도메인 선택: 왜 수처리인가

수처리·수질 법령 도메인은 Graph RAG 포트폴리오에 이상적입니다.

1. **명확한 수치** — "탁도 0.5 NTU 이하"처럼 기준값이 정해져 있어 RAG 정확도를 객관적으로 평가할 수 있습니다.
2. **복잡한 관계 구조** — 법령 → 수질기준 → 공정 → 사고 → 처벌로 이어지는 멀티홉 연결이 자연스럽게 존재합니다.
3. **공개 데이터** — 수도법, 먹는물 수질기준 고시는 공공 법령이라 자유롭게 활용할 수 있습니다.

---

## 아키텍처 개요

```
사용자 질문
    │
    ├─── Graph Retriever (Cypher QA) ──┐
    │    구조적 관계 탐색               │
    │                                  ├── Context 통합 → GPT-4o-mini → 답변
    └─── Vector Retriever (KR-SBERT) ──┘
         의미적 유사 청크 검색
```

핵심은 두 검색을 `asyncio.gather`로 **병렬** 실행한다는 점입니다. 순차 실행 대비 응답 시간을 절반 가까이 줄였습니다.

```python
graph_task = asyncio.create_task(_run_graph_search(question, graph))
vector_task = asyncio.create_task(asyncio.to_thread(vector_search, question, k))

graph_result, cypher = await graph_task
vector_docs = await vector_task
```

여기에 LRU 캐시(TTL 1시간, 128 엔트리)를 얹었더니 동일 질문 재요청 시 **134배 빠른** 응답이 나왔습니다. 2.68초 → 0.02초.

---

## 온톨로지 설계가 핵심이었다

LLMGraphTransformer에 그냥 문서를 던지면 LLM이 마음대로 노드를 만들어냅니다. `Person`, `Organization`, `Event` 같은 범용 타입이 나오면 수처리 도메인에서 의미 있는 Cypher 쿼리를 짜기가 어렵습니다.

그래서 **도메인 온톨로지를 먼저 설계**했습니다.

```python
ALLOWED_NODES = [
    # 법제
    "법령", "조문", "고시",
    # 수질기준 (세분화)
    "건강항목", "심미적항목", "소독부산물", "미생물항목",
    # 수치 정보
    "수질기준값", "검사주기", "검사방법",
    # 시설·공정
    "정수장", "공정", "소독방법", "약품",
    # 기관·지역
    "기관", "지역",
    # 사고·위반
    "수질사고", "위반항목", "처벌규정",
]
```

`strict_mode=False`로 설정해서 온톨로지 외 관계도 "연관된다"로 수용했습니다. 너무 엄격하게 하면 정보 손실이 큽니다.

결과: 문서 6종 → 청크 25개 → **노드 247개 / 관계 194개**

---

## 지식 그래프 시각화

D3.js force-directed 그래프로 247개 노드를 인터랙티브하게 렌더링했습니다. 노드 타입별로 색상을 다르게 지정하고, 클릭하면 이웃 관계를 API로 가져와서 확장합니다.

![노드 클릭 디테일](https://raw.githubusercontent.com/teriyakki-jin/Graph-RAG-with-water/master/screenshot_node.png)
*노드 클릭 시 타입·속성·이웃 관계를 상세 패널에 표시*

```typescript
// 노드 ID를 elementId(UUID) 대신 n.id(한글 이름)로 통일 — 초기 삽질 포인트
const nodeIds = new Set(nodes.map((n) => n.id));
const validEdges = edges.filter(
  (e) => nodeIds.has(e.source as string) && nodeIds.has(e.target as string)
);
```

---

## 질의응답 데모

### 단순 기준값 조회

> "탁도 기준은 얼마이고 초과 시 처분은?"

![단순 질의 결과](https://raw.githubusercontent.com/teriyakki-jin/Graph-RAG-with-water/master/screenshot_query.png)
*그래프 검색 결과(Cypher)와 벡터 검색 청크를 통합한 답변 생성*

답변 예시:
```
먹는물의 탁도 기준은 0.5 NTU 이하입니다(수도법 제26조).
이 기준을 초과할 경우, K-water와 지방자치단체는 즉시 급수를 중단하고
대체 급수원을 확보해야 할 의무가 있습니다.
```

### 멀티홉 복합 질의

> "낙동강 페놀 사고 이후 도입된 소독 방식과 그 부산물 기준은?"

![멀티홉 질의](https://raw.githubusercontent.com/teriyakki-jin/Graph-RAG-with-water/master/screenshot_multihop.png)
*사고 → 정수장 → 소독방법 → 부산물 → 기준값 체인을 그래프에서 탐색*

이 질의는 벡터 RAG 단독으로는 어렵습니다. 각 정보가 서로 다른 문서에 흩어져 있기 때문입니다. 그래프 경로 탐색이 정보를 연결합니다.

---

## 벤치마크 평가 시스템

"성능이 어떻게 되나요?"라는 질문에 답하려면 평가 시스템이 필요합니다.

RAGAS를 참고해서 수처리 도메인에 맞는 5가지 지표를 직접 구현했습니다.

| 지표 | 설명 | 가중치 |
|------|------|--------|
| **Keyword Recall** | 정답 키워드가 답변에 포함된 비율 | 35% |
| **Faithfulness** | 답변이 컨텍스트에 근거하는 비율 | 25% |
| **Numeric Accuracy** | 수치 + 단위 정확도 (도메인 특화) | 20% |
| **Context Precision** | 정답 키워드가 컨텍스트에 있는 비율 | 10% |
| **Answer Relevancy** | 질문-답변 키워드 Jaccard 유사도 | 10% |

Numeric Accuracy는 직접 추가한 지표입니다. "0.5 NTU"에서 숫자와 단위가 모두 맞아야 1.0, 숫자만 맞으면 0.7, 틀리면 0.0을 줍니다.

평가셋은 수동으로 작성한 Q&A 20문항입니다.

```
카테고리별:
  기준값_단순 (easy)  → "탁도 기준은?"
  소독_비교 (medium)  → "염소 vs 오존 소독 차이?"
  법령 (medium)       → "수도법 83조 처벌은?"
  사고_사례 (hard)    → "인천 붉은수돗물 사고 원인과 위반 항목?"
  멀티홉 (hard)       → "페놀 기준과 낙동강 사고 검출값을 비교하라"
```

---

## 삽질 기록

개발하면서 꽤 많은 문제를 만났습니다. 기록해 두면 같은 스택을 쓰는 분들께 도움이 될 것 같습니다.

### 1. `No module named 'langchain_core.graph_transformers'`

LangChain 버전이 올라가면서 `GraphDocument`의 위치가 바뀌었습니다.

```python
# 틀림
from langchain_core.graph_transformers import GraphDocument

# 맞음 (0.3.x 기준)
from langchain_experimental.graph_transformers.llm import GraphDocument
```

### 2. Windows Hyper-V 포트 예약 문제

Docker를 쓰는 Windows 환경에서 포트 8000, 8080이 접속이 안 됐습니다.

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
# → 7998-8097 범위 전체가 Hyper-V에 예약됨
```

FastAPI 포트를 8888로 변경해서 해결했습니다.

### 3. 노드 이름이 `n.name`이 아니라 `n.id`

LLMGraphTransformer가 추출한 노드의 이름은 `name` 속성이 아니라 `id` 속성에 저장됩니다.

```cypher
-- 안 됨 (결과 없음)
MATCH (n) WHERE n.name = '탁도' RETURN n

-- 됨
MATCH (n) WHERE n.id = '탁도' RETURN n
```

few-shot 예제와 Repository 쿼리를 전부 `n.id`로 수정하고 나서야 답변이 나왔습니다.

### 4. D3 `node not found` 런타임 에러

노드 300개와 엣지 300개를 독립적으로 조회하면 엣지가 참조하는 노드가 목록에 없는 경우가 생깁니다.

```typescript
// D3에 넘기기 전에 유효한 엣지만 필터링
const nodeIds = new Set(nodes.map((n) => n.id));
const validEdges = edges.filter(
  (e) => nodeIds.has(e.source as string) && nodeIds.has(e.target as string)
);
```

### 5. Windows CP949 인코딩

`TextLoader`가 한글 파일을 CP949로 읽으려다 실패합니다.

```python
TextLoader(path, encoding="utf-8")
```

### 6. 유닛 테스트에서 `Settings()` 실패

`pydantic-settings`는 환경변수 없으면 인스턴스 생성 시점에 터집니다. `conftest.py`에서 미리 주입해야 합니다.

```python
# tests/conftest.py
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
```

---

## 마무리: 면접에서 쓸 수 있는 답변 한 줄

> "순수 벡터 RAG는 의미적 유사도로 청크를 찾지만 관계 연결에 약합니다. 이 시스템은 Neo4j 지식 그래프로 법령-수질기준-사고 간 멀티홉 관계를 탐색하고, 벡터 검색을 병렬로 실행해 서술적 맥락을 보완합니다. asyncio.gather 병렬화와 LRU 캐시로 응답 속도를 추가로 최적화했습니다."

---

**GitHub**: https://github.com/teriyakki-jin/Graph-RAG-with-water

사용 기술: `Python` `FastAPI` `Neo4j` `LangChain` `OpenAI` `Next.js` `D3.js`
