# Lab #17 — Multi-Memory Agent với LangGraph

Xây dựng một AI agent có 4 loại memory (short-term, long-term profile, episodic, semantic) được điều phối bởi một router thông minh trên LangGraph, có khả năng trim context theo priority và benchmark so sánh với baseline không có memory.

## Kiến trúc tổng quan

```
User query
   │
   ▼
[classify_intent]   ← LLM router → {use_profile?, use_episodic?, use_semantic?}
   │
   ▼
[retrieve_memory]   ← gọi các backend được chọn (song song)
   │
   ▼
[trim_context]      ← 4-level priority eviction nếu vượt token budget
   │
   ▼
[call_llm]          ← prompt có section rõ: [PROFILE][EPISODIC][SEMANTIC][RECENT][QUERY]
   │
   ▼
[save_memory]       ← extract facts → Redis; append episodic log
   │
   ▼
Response
```

**4 memory backends (`memory/`):**
- `short_term.py` — sliding window buffer (in-process, per-session)
- `long_term_profile.py` — Redis hash với overwrite semantics (conflict handling)
- `episodic.py` — JSON append-only log cho trajectory
- `semantic.py` — ChromaDB collection + OpenAI embeddings

**Graph components (`graph/`):**
- `state.py` — `MemoryState` TypedDict
- `router.py` — intent classifier node (LLM-based với rule-based fallback)
- `retrieve.py` — gom memory theo intent
- `trimmer.py` — 4-level priority eviction
- `llm.py` — chính LLM call với sectioned prompt
- `save.py` — fact extraction + profile update + episodic save
- `build.py` — StateGraph compilation

## Setup

### 1. Python environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Unix
pip install -r requirements.txt
```

### 2. Start Redis

**Option A — Docker (khuyến nghị):**
```bash
docker run -d --name redis-lab17 -p 6379:6379 redis:7
```

**Option B — Windows:** cài Redis bản port (ví dụ từ Memurai hoặc WSL), đảm bảo port 6379.

### 3. Cấu hình env

```bash
cp .env.example .env
# Sửa .env và điền OPENAI_API_KEY
```

Biến có thể chỉnh:
- `OPENAI_MODEL` — mặc định `gpt-4o-mini`
- `OPENAI_EMBED_MODEL` — mặc định `text-embedding-3-small`
- `MEMORY_BUDGET_TOKENS` — mặc định `1500`
- `SHORT_TERM_MAX_MESSAGES` — mặc định `10`

## Chạy thử

### Interactive CLI

```bash
python main.py --user alice --verbose
```

Sample session:
```
You: Tôi tên Linh và dị ứng với đậu nành.
Agent: Rất vui được biết bạn, Linh. Tôi sẽ ghi nhớ bạn dị ứng đậu nành.

You: Bạn còn nhớ tên tôi không?
Agent: Có, tên bạn là Linh.
```

Lệnh đặc biệt:
- `/profile` — in ra profile đã lưu trong Redis
- `/reset` — xóa memory của user hiện tại
- `/quit` — thoát

### Chạy benchmark

```bash
# Tất cả 10 conversations (both agents)
python -m benchmark.runner

# Chỉ conversation #3 (test bắt buộc của rubric: allergy conflict)
python -m benchmark.runner --only 3

# Chỉ with-memory, bỏ qua baseline
python -m benchmark.runner --skip-no-memory
```

Output: `benchmark/BENCHMARK.md`.

## Cấu trúc repository

```
├── memory/                 # 4 memory backends (interface riêng biệt)
├── graph/                  # LangGraph state, router, nodes, trimmer
├── prompts/                # sectioned prompt templates
├── benchmark/              # 10 conversations + runner + BENCHMARK.md (generated)
├── data/
│   ├── knowledge_seed.json       # seed cho Chroma (10 docs)
│   └── episodic_log.json         # (generated) append-only log
├── main.py                 # CLI demo
├── REFLECTION.md           # privacy/limitations (rubric §5)
├── README.md
├── requirements.txt
└── .env.example
```

## Mapping sang rubric

| Rubric section | Điểm | Where |
|----------------|-----:|-------|
| 1. Full memory stack (4 backends) | 25 | `memory/*.py` — 4 file độc lập, interface `save()`/`retrieve()` |
| 2. LangGraph state/router + prompt injection | 30 | `graph/state.py` (MemoryState), `graph/build.py` (StateGraph), `prompts/system.py` (sectioned) |
| 3. Save/update + conflict handling | 15 | `memory/long_term_profile.py` (overwrite semantics), `graph/save.py` (extractor) |
| 4. Benchmark 10 multi-turn | 20 | `benchmark/conversations.py` (5 groups × 2), `benchmark/runner.py`, `benchmark/BENCHMARK.md` |
| 5. Reflection privacy/limitations | 10 | `REFLECTION.md` |
| Bonus: Redis thật | +2 | `memory/long_term_profile.py` |
| Bonus: Chroma thật | +2 | `memory/semantic.py` |
| Bonus: LLM extraction có error handling | +2 | `graph/save.py` (try/except + JSON fence strip) |
| Bonus: graph flow demo | +2 | `graph/build.py` + `main.py --verbose` (in router intent, retrieved memory, tokens, trim log) |

## Troubleshooting

**"Cannot connect to Redis"** — Redis chưa chạy. Xem Setup §2.

**"OpenAI API key not found"** — kiểm tra `.env` đã có `OPENAI_API_KEY=sk-...`.

**Chroma lỗi khi khởi tạo** — xóa thư mục `data/chroma/` rồi chạy lại (sẽ tự seed lại từ `knowledge_seed.json`).

**Benchmark chạy chậm** — giảm số conversations hoặc dùng `--only <id>` để test từng cái.
