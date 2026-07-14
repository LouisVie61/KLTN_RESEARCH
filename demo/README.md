# GPTScan Demo

Demo này mô phỏng một pipeline quét lỗ hổng Solidity theo hướng GPTScan-inspired. Pipeline kết hợp static heuristic, LLM matching và static confirmation để tìm các pattern rủi ro trong smart contract.

## Cấu trúc thư mục

```text
demo/
├── pipeline.py              # Entrypoint CLI để chạy toàn bộ pipeline
├── requirements.txt         # Dependencies cho demo
├── .env.example             # Mẫu cấu hình Gemini
├── scenarios.json           # Định nghĩa vulnerability scenarios
├── gptscan_demo/            # Các module chính của pipeline
├── prompts/                 # Prompt templates cho Gemini
├── samples/                 # Solidity sample input
└── tests/                   # Unit tests cho parser/filter/confirmation
```

Các file quan trọng trong `gptscan_demo/`:

- `parser.py`: đọc Solidity source và tách các function kèm line range.
- `filters.py`: lọc candidate functions bằng heuristic tĩnh.
- `scenarios.py`: tải các scenario từ `scenarios.json`.
- `llm_client.py`: chọn backend LLM theo mode `auto`, `mock`, hoặc `gemini`.
- `mock_gpt.py`: LLM giả lập deterministic, dùng được khi không có API key.
- `gemini_client.py`: gọi Gemini API và parse JSON response.
- `confirm.py`: xác nhận finding bằng static checks.
- `report.py`: render kết quả dạng text hoặc JSON.

## Cài đặt

Từ thư mục gốc repo:

```powershell
cd demo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu đã có môi trường Python phù hợp, có thể bỏ qua bước tạo virtualenv và chỉ chạy:

```powershell
cd demo
pip install -r requirements.txt
```

## Cấu hình Gemini

Demo có thể chạy bằng `mock` LLM mà không cần API key. Nếu muốn dùng Gemini, tạo file `.env` từ mẫu:

```powershell
Copy-Item .env.example .env
```

Sau đó cập nhật:

```env
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MIN_INTERVAL_SECONDS=13
GEMINI_MAX_RETRIES=1
```

`GEMINI_MODEL` mặc định là `gemini-2.5-flash` nếu không khai báo biến này.
`GEMINI_MIN_INTERVAL_SECONDS` và `GEMINI_MAX_RETRIES` giúp demo chạy ổn định hơn khi dùng Gemini free tier.

## Cách chạy

Chạy với sample mặc định `samples/vulnerable.sol`:

```powershell
python pipeline.py
```

```powershell
python pipeline.py samples/vulnerable.sol --llm mock
```


```powershell
python pipeline.py samples/vulnerable_gemini.sol --llm gemini
```

Các mode LLM:

- `auto`: dùng Gemini nếu có `GOOGLE_API_KEY`, nếu không sẽ fallback sang mock.
- `mock`: dùng mock deterministic, phù hợp để demo offline và test.
- `gemini`: ưu tiên Gemini; nếu thiếu API key hoặc SDK lỗi, pipeline fallback sang mock và in warning.

## Chạy test

Từ thư mục `demo`:

```powershell
python -m pytest tests
```

```powershell
python -m pytest demo/tests
```

## Kiến trúc pipeline

Pipeline chính nằm trong `pipeline.py` và điều phối các module theo thứ tự:

1. Nhận input Solidity file và options CLI như `--llm`, `--json`.
2. Tải vulnerability scenarios từ `scenarios.json`.
3. Parse Solidity file thành danh sách `SolidityFunction`.
4. Chạy static filter để chọn `CandidateFunction`.
5. Gửi candidate vào LLM backend để match scenario/property và trích key statements.
6. Chạy static confirmation để phân loại finding thành `confirmed`, `rejected`, hoặc `needs_review`.
7. Render kết quả ra terminal bằng text report hoặc JSON.

## Dataflow

```text
Solidity file
    |
    v
parser.py
    |
    v
List[SolidityFunction]
    |
    v
filters.py + scenarios.json
    |
    v
List[CandidateFunction]
    |
    v
llm_client.py -> mock_gpt.py hoặc gemini_client.py
    |
    v
List[LLMFinding]
    |
    v
confirm.py
    |
    v
List[FindingResult]
    |
    v
report.py
    |
    v
Text report hoặc JSON
```

## Output chính

Text report chia theo các stage:

- `[1] Parse`: số lượng function tìm được.
- `[2] Static filter`: candidate functions và lý do được chọn.
- `[3] LLM matching + key extraction`: số finding tiềm năng.
- `[4] Static confirmation`: trạng thái xác nhận, proof và evidence.

JSON output dùng `ScanResult.to_dict()` và bao gồm:

- input file, LLM requested/used, số lượng function/candidate.
- danh sách candidates.
- danh sách findings, confidence, key variables, key statements.
- confirmation status, proof và evidence.
- warnings nếu có fallback hoặc lỗi LLM.

## Ghi chú

Parser trong demo chỉ là parser heuristic để phục vụ minh họa, không thay thế Solidity compiler/parser đầy đủ. Kết quả quét nên được xem là tín hiệu hỗ trợ review, không phải kết luận bảo mật cuối cùng.


- baseline: danh gia metric nao la chinh dua tren thuc nghiem va bo du lieu cua bai bao
- vi sao chi duoc 57% cho large project nhu web3bugs nhu ket qua cua bai bao? reason?
- huong nghien cuu co ai phat trien them khong? reason?