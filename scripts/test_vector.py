from app.services.vector_retriever import vector_search

results = vector_search("탁도 기준은 얼마인가", k=3)
print(f"검색 결과: {len(results)}개\n")
for i, doc in enumerate(results):
    src = doc.metadata.get("source", "?")
    print(f"[{i+1}] source={src}")
    print(f"     {doc.page_content[:100]}")
    print()
