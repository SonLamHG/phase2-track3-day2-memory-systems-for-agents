"""10 scripted multi-turn conversations covering the 5 rubric-required groups.

Each conversation has:
  - setup_turns: messages to run through the agent (populates memory)
  - test_query: the final turn whose response is evaluated
  - expected_intent: ground-truth for router correctness
  - expected_contains: substring(s) the with-memory response must include to pass
  - expected_absent: substring(s) that if present signal a failure (e.g., stale fact)
"""
from __future__ import annotations

CONVERSATIONS = [
    # Group 1: Profile recall (2 conversations)
    {
        "id": 1,
        "group": "profile_recall",
        "title": "Recall user name after intervening turns",
        "user_id": "bench_u1",
        "setup_turns": [
            "Xin chào, tôi tên là Linh.",
            "Hôm nay trời đẹp nhỉ.",
            "Bạn thấy Python có dễ học không?",
            "Kể tôi nghe về cách hoạt động của cache.",
        ],
        "test_query": "Bạn còn nhớ tên tôi không?",
        "expected_intent": {"use_profile": True},
        "expected_contains": ["Linh"],
        "expected_absent": [],
    },
    {
        "id": 2,
        "group": "profile_recall",
        "title": "Recall user's job through distractor turns",
        "user_id": "bench_u2",
        "setup_turns": [
            "Tôi là data scientist làm việc với Python và SQL.",
            "Kể tôi nghe một câu chuyện cười.",
            "Thời tiết Hà Nội ra sao?",
            "Giải thích binary search cho tôi.",
        ],
        "test_query": "Công việc hiện tại của tôi là gì?",
        "expected_intent": {"use_profile": True},
        "expected_contains": ["data scientist"],
        "expected_absent": [],
    },
    # Group 2: Conflict update (2 conversations) — rubric mandatory
    {
        "id": 3,
        "group": "conflict_update",
        "title": "Allergy: milk -> soy (rubric mandatory test)",
        "user_id": "bench_u3",
        "setup_turns": [
            "Tôi dị ứng với sữa bò, bạn nhớ nhé.",
            "Bạn có thể gợi ý đồ uống cho bữa sáng không?",
            "À nhầm, thực ra tôi dị ứng với đậu nành chứ không phải sữa bò.",
        ],
        "test_query": "Tôi bị dị ứng gì?",
        "expected_intent": {"use_profile": True},
        "expected_contains": ["đậu nành"],
        "expected_absent": ["sữa bò"],
    },
    {
        "id": 4,
        "group": "conflict_update",
        "title": "Drink preference: coffee -> tea",
        "user_id": "bench_u4",
        "setup_turns": [
            "Sở thích của tôi là uống cà phê vào buổi sáng.",
            "Bạn thấy cà phê và trà khác nhau thế nào?",
            "Thực ra tôi đã đổi sang uống trà rồi, không uống cà phê nữa.",
        ],
        "test_query": "Đồ uống yêu thích của tôi bây giờ là gì?",
        "expected_intent": {"use_profile": True},
        "expected_contains": ["trà"],
        "expected_absent": [],  # cà phê có thể xuất hiện trong giải thích; không strict
    },
    # Group 3: Episodic recall (2 conversations)
    {
        "id": 5,
        "group": "episodic_recall",
        "title": "Recall previous calculation approach",
        "user_id": "bench_u5",
        "setup_turns": [
            "Giúp tôi tính công thức BMI, tôi nặng 65kg cao 1.7m.",
            "Cảm ơn nhé.",
            "Bạn thấy BMI có phản ánh đúng sức khỏe không?",
        ],
        "test_query": "Lần trước bạn đã dùng công thức nào để tính cho tôi?",
        "expected_intent": {"use_episodic": True},
        "expected_contains": ["BMI"],
        "expected_absent": [],
    },
    {
        "id": 6,
        "group": "episodic_recall",
        "title": "Recall previous debug suggestion",
        "user_id": "bench_u6",
        "setup_turns": [
            "Hai container docker của tôi không kết nối được với nhau.",
            "Tôi đã đặt tên service là 'api' và 'db' trong cùng một network.",
            "Cảm ơn, tôi sẽ thử dùng service name làm hostname.",
        ],
        "test_query": "Hôm qua bạn đã đề xuất cách debug docker networking gì cho tôi?",
        "expected_intent": {"use_episodic": True},
        # Accept either English "service name" or Vietnamese equivalents
        "expected_contains_any": ["service name", "tên dịch vụ", "tên service"],
        "expected_contains": [],
        "expected_absent": [],
    },
    # Group 4: Semantic retrieval (2 conversations)
    {
        "id": 7,
        "group": "semantic_retrieval",
        "title": "Factual Q&A about France",
        "user_id": "bench_u7",
        "setup_turns": [
            "Tôi đang tìm hiểu về châu Âu.",
            "Pháp là một quốc gia thú vị nhỉ.",
        ],
        "test_query": "Thủ đô của Pháp là gì và dân số khoảng bao nhiêu?",
        "expected_intent": {"use_semantic": True},
        "expected_contains": ["Paris"],
        "expected_absent": [],
    },
    {
        "id": 8,
        "group": "semantic_retrieval",
        "title": "Python GIL factual question",
        "user_id": "bench_u8",
        "setup_turns": [
            "Tôi đang tối ưu hóa code Python cho xử lý ảnh.",
            "CPU-bound có nghĩa là gì nhỉ.",
        ],
        "test_query": "Để chạy song song CPU-bound tasks trong Python thì nên dùng gì?",
        "expected_intent": {"use_semantic": True},
        "expected_contains": ["multiprocessing"],
        "expected_absent": [],
    },
    # Group 5: Trim / budget (2 conversations)
    {
        "id": 9,
        "group": "trim_budget",
        "title": "Long conversation — profile must survive eviction",
        "user_id": "bench_u9",
        "setup_turns": [
            "Tôi tên Minh, tôi là kỹ sư backend.",
            "Kể tôi nghe về Redis.",
            "Kể về PostgreSQL.",
            "So sánh hai cái đó.",
            "Kafka là gì?",
            "RabbitMQ khác Kafka thế nào?",
            "Giải thích CAP theorem.",
            "ACID là gì?",
            "Eventual consistency nghĩa là sao?",
            "Sharding vs replication?",
        ],
        "test_query": "Ngành của tôi là gì và bạn còn nhớ tên tôi không?",
        "expected_intent": {"use_profile": True},
        "expected_contains": ["Minh", "backend"],
        "expected_absent": [],
    },
    {
        "id": 10,
        "group": "trim_budget",
        "title": "Spam filler — core profile + recent context preserved",
        "user_id": "bench_u10",
        "setup_turns": [
            "Tôi dị ứng với hải sản, rất nghiêm trọng nhé.",
            "Tôi sống ở Hà Nội.",
            "Kể vài quán ăn ngon ở Hà Nội.",
            "Giới thiệu món phở bò.",
            "Bún chả có gì đặc biệt?",
            "Cà phê trứng hình thành khi nào?",
            "Bánh mì pate ra sao?",
            "Chè Hà Nội có những loại gì?",
        ],
        "test_query": "Gợi ý cho tôi 1 món ăn trưa an toàn ở Hà Nội đi.",
        "expected_intent": {"use_profile": True},
        "expected_contains": [],  # khó check chặt; ta check absence của hải sản
        "expected_absent": ["hải sản"],  # agent có memory không được gợi ý hải sản
    },
]
