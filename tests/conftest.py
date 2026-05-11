import os
import pytest

# 테스트 실행 전 필수 환경변수 주입 (실제 API 호출 없음)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password123")
