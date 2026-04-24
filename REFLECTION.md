# Reflection — Privacy, Risk & Limitations

## 1. Memory nào giúp agent nhất?

Trong 10 conversations benchmark, **long-term profile (Redis)** và **semantic (Chroma)** là hai loại mang lại differential value lớn nhất so với baseline:

- **Profile** quyết định pass/fail ở 6/10 conversations (profile recall + conflict update + trim scenarios). Không có nó, agent baseline không thể nhớ tên/job/dị ứng qua nhiều turn.
- **Semantic** cung cấp factual grounding cho các câu hỏi kiến thức (thủ đô, GIL) — baseline LLM vẫn có thể trả lời đúng nhờ pretraining, nhưng với knowledge base nội bộ có thể version hóa, update, và kiểm soát (quan trọng cho enterprise).
- **Episodic** giúp agent "recall thói quen làm việc" của user — ít dùng nhất nhưng có tác động lớn khi cần (debug cùng issue 2 lần).
- **Short-term** là baseline — có ở cả 2 agent.

## 2. Memory nào rủi ro nhất nếu retrieve sai?

**Long-term profile (Redis)** là rủi ro nhất vì 3 lý do:

1. **Chứa PII trực tiếp:** name, dị ứng (PHI — thông tin sức khỏe), preferences cá nhân. Trong benchmark có trường hợp lưu "dị ứng hải sản" — nếu retrieve sai hoặc stale, agent có thể gợi ý món hải sản gây hậu quả y tế nghiêm trọng.
2. **Persistent across sessions:** một fact sai không tự biến mất — nó sống mãi trong Redis cho đến khi bị overwrite hoặc xóa thủ công.
3. **Cross-context leak:** nếu `user_id` bị nhầm, agent có thể trả info của user A cho user B.

Chroma (semantic) rủi ro hạng 2 — có thể retrieve info sai context nhưng thường là kiến thức public, ít PII.

Episodic rủi ro hạng 3 — chứa lịch sử tương tác (có thể nhạy cảm nếu user từng share PII trong query).

## 3. Nếu user yêu cầu xóa memory, xóa ở đâu?

Hiện tại code có partial support cho "right to be forgotten":

| Backend | Deletion hook | Implemented |
|---------|--------------|-------------|
| Short-term | `ShortTermMemory.clear()` | ✅ |
| Profile (Redis) | `LongTermProfile.delete(user_id)` / `delete_fact(user_id, fact_key)` | ✅ |
| Episodic (JSON) | `EpisodicMemory.clear(user_id)` | ✅ (filter by user_id) |
| Semantic (Chroma) | `SemanticMemory.delete(doc_id)` | ✅ nhưng thiếu per-user scope |

**Gap:** semantic collection hiện là shared knowledge base, nếu user đưa info cá nhân vào (chưa làm trong agent này nhưng có thể xảy ra trong production), cần thêm `user_id` vào metadata của Chroma và implement `delete_by_metadata(user_id)`.

**TTL:** Redis nên set `EXPIRE` cho keys `user:{id}:profile` (ví dụ 90 ngày không tương tác thì tự xóa). Chưa implement.

**Consent:** hiện fact extractor tự động gom fact mỗi turn — nên có opt-in/opt-out flag (e.g., user nói "đừng nhớ điều này" hoặc system-level setting `allow_profile_learning=false`).

## 4. Điều gì sẽ fail khi scale?

| Component | Failure mode | Mitigation |
|-----------|-------------|------------|
| Episodic JSON file | Không chịu được concurrent write (race khi nhiều user cùng ghi) | Chuyển sang SQLite/Postgres hoặc Redis list per-user |
| Chroma in-process | Giới hạn RAM khi số doc > 1M; không support multi-process writes | Move sang Chroma server mode hoặc Qdrant/Pinecone |
| Redis single-node | Điểm chết; thiếu persistence nếu không config AOF | Redis Sentinel/Cluster + AOF appendonly yes |
| LLM router mỗi query | Cost tăng tuyến tính với QPS (3 calls/turn: router + main + extractor) | Cache intent cho queries tương tự; dùng local classifier (DistilBERT) cho router; async extractor |
| Token budget cứng | Prompt vượt budget vẫn có thể xảy ra nếu semantic doc quá dài | Chunking docs trước khi index; re-summarize episodic khi vượt quota |
| Fact extractor LLM | Trả JSON sai format → drop fact | Hiện đã có try/except; nên thêm structured output (OpenAI JSON mode) và retry |

## 5. Limitations kỹ thuật khác

- **Router chỉ chọn ON/OFF cho mỗi backend**, không rank theo confidence → có thể retrieve thừa khi query ambiguous.
- **4-level trimmer dùng token count của rendered section**, không tái rank từng hit cá nhân — có thể vứt 1 episode tốt còn giữ 2 episode tệ nếu timestamp order không khớp relevance.
- **Conflict handling chỉ overwrite theo key** — không handle được "thêm" fact (e.g., user có 2 dị ứng). Fix: đổi value thành list với dedup.
- **Không có evaluation LLM-as-judge** — benchmark chỉ substring match, miss các case agent trả đúng ý nhưng diễn đạt khác.
- **Không có reranking semantic hits** — dùng raw distance; nên thêm cross-encoder rerank cho high-stakes case.
- **State không persist giữa các run của main.py** — short-term buffer mất khi quit. Chấp nhận được cho lab, nhưng production cần checkpoint state vào Redis.
