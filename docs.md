# Hướng dẫn Thực hành Lab #17: Xây dựng Multi-Memory Agent với LangGraph
**Đơn vị:** VinUniversity

## I. Tổng quan (Overview)
Trong bài lab này, bạn sẽ học cách thiết kế và triển khai một AI Agent nâng cao có khả năng quản lý và truy xuất thông tin từ nhiều nguồn bộ nhớ khác nhau, giúp Agent giải quyết hạn chế về việc "quên" ngữ cảnh hoặc tràn giới hạn token trong các cuộc hội thoại dài.

* **Mục tiêu chính:** Xây dựng một Multi-Memory Agent sử dụng framework **LangGraph**.
* **Thời gian thực hiện dự kiến:** 2 giờ.
* **Yêu cầu đầu ra (Deliverable):**
    * Mã nguồn Agent hoàn chỉnh với toàn bộ stack bộ nhớ (Full memory stack).
    * Báo cáo đánh giá (Benchmark report) so sánh hiệu năng của Agent có bộ nhớ và không có bộ nhớ.

---

## II. Các bước thực hành chi tiết (Implementation Steps)

### Bước 1: Cài đặt 4 cơ sở lưu trữ bộ nhớ (Implement 4 memory backends)
Thay vì sử dụng một bộ nhớ duy nhất, Agent của bạn sẽ cần 4 "backend" khác nhau để phục vụ cho các mục đích ghi nhớ cụ thể:

1. **Short-term Memory (Bộ nhớ ngắn hạn):**
    * *Công cụ:* Sử dụng `ConversationBufferMemory` (của LangChain/LangGraph).
    * *Chức năng:* Lưu trữ trực tiếp các lượt hội thoại gần nhất (recent turns) để duy trì mạch giao tiếp tự nhiên ngay lập tức.
2. **Long-term Memory (Bộ nhớ dài hạn):**
    * *Công cụ:* **Redis**.
    * *Chức năng:* Lưu trữ các thông tin mang tính chất hồ sơ người dùng (User Profiles), sở thích (User preferences), hoặc các setting được cập nhật qua thời gian.
3. **Episodic Memory (Bộ nhớ theo tập / Sự kiện):**
    * *Công cụ:* Ghi log dưới dạng file **JSON**.
    * *Chức năng:* Ghi lại lịch sử các hành động (actions), suy luận (thoughts) hoặc quỹ đạo (trajectories) mà Agent đã thực hiện trong quá khứ (Experience recall). Giúp Agent nhớ lại "hôm qua tôi đã giải quyết bài toán này như thế nào".
4. **Semantic Memory (Bộ nhớ ngữ nghĩa):**
    * *Công cụ:* Cơ sở dữ liệu Vector **Chroma (ChromaDB)**.
    * *Chức năng:* Lưu trữ các sự kiện, kiến thức (Factual recall). Khi người dùng hỏi một thông tin cụ thể, Agent sẽ dùng semantic search để trích xuất thông tin liên quan từ Chroma.

### Bước 2: Xây dựng bộ định tuyến bộ nhớ (Build Memory Router)
Bạn cần thiết kế một cơ chế (có thể là một node LLM phân loại hoặc rule-based logic trong LangGraph) để phân tích **Query Intent** (Ý định của câu truy vấn) từ người dùng, từ đó quyết định gọi đến backend bộ nhớ nào.

* **Ví dụ định tuyến:**
    * *Truy vấn:* "Tôi có bị dị ứng với loại thức ăn nào không?" -> Router trỏ về **Redis** (User preference).
    * *Truy vấn:* "Thủ đô của nước Pháp là gì và nó có bao nhiêu dân?" -> Router trỏ về **Chroma** (Factual recall).
    * *Truy vấn:* "Lần trước bạn đã dùng công thức nào để tính toán cho tôi?" -> Router trỏ về **JSON episodic log** (Experience recall).

### Bước 3: Quản lý cửa sổ ngữ cảnh (Context Window Management)
Để tránh lỗi vượt quá giới hạn token của LLM, bạn cần thiết lập thuật toán cắt tỉa (trimming) thông minh.

* **Auto-trim:** Tự động cắt bỏ bớt lịch sử hội thoại khi số lượng token tiến gần đến giới hạn (limit).
* **Priority-based Eviction theo phân cấp 4 mức (4-level hierarchy):** Khi cần xóa bộ nhớ để nhường chỗ cho token mới, hãy xóa theo thứ tự ưu tiên:
    1. *Mức 1 (Cao nhất - Không bao giờ xóa):* System Prompt & Core Instructions.
    2. *Mức 2:* User Profile cốt lõi (từ Redis).
    3. *Mức 3:* Context của câu hỏi hiện tại & Short-term buffer gần nhất.
    4. *Mức 4 (Thấp nhất - Xóa đầu tiên):* Các factual knowledge hoặc episodic logs cũ được retrieve về nhưng ít liên quan nhất.

### Bước 4: Đánh giá hiệu năng (Benchmark)
Tạo một tập dữ liệu kiểm thử gồm **10 cuộc hội thoại multi-turn** (nhiều lượt tương tác, yêu cầu Agent phải nhớ thông tin từ các lượt trước).

Thực hiện chạy 2 phiên bản Agent (Có Multi-Memory Stack và Không có Memory/Chỉ có basic buffer) và đo lường các chỉ số sau:
1. **Response Relevance:** Mức độ liên quan và chính xác của câu trả lời.
2. **Context Utilization:** Agent có thực sự sử dụng đúng các thông tin đã được lưu trong memory để trả lời không.
3. **Token Efficiency:** Hiệu quả sử dụng token (chỉ retrieve phần memory cần thiết thay vì nhồi nhét tất cả vào prompt).

---

## III. Yêu cầu Nộp bài (Submission & Deliverables)

Sinh viên cần hoàn thành và nộp 2 tài liệu sau:

**1. GitHub Repository:**
* Chứa toàn bộ mã nguồn xây dựng bằng LangGraph.
* Cấu hình đầy đủ kết nối tới Redis và Chroma.
* Có file `README.md` hướng dẫn cách setup và chạy Agent.

**2. Báo cáo đánh giá (Benchmark Report):** Báo cáo phải bao gồm:
* **Bảng so sánh metrics:** Trình bày rõ ràng điểm số (hoặc đánh giá định tính/định lượng) giữa Agent có bộ nhớ và không có bộ nhớ qua 10 cuộc hội thoại.
* **Memory hit rate analysis:** Phân tích tỷ lệ "trúng đích" của từng loại memory (Ví dụ: Router đã gọi đúng Chroma bao nhiêu lần? Gọi đúng Redis bao nhiêu lần?).
* **Token budget breakdown:** Phân tích việc tiêu thụ token cho mỗi thành phần (System prompt, retrieved memory, short-term history).