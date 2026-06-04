# Continue

## Baseline

Theo bài báo: baseline có thể hiểu theo 3 lớp

### Lớp 1 - Evaluation datasets

Dataset:
- Top200: đo false positives (FP) trên contract không có bug nghiêm trọng
- Web3Bugs: đo khả năng detect logic vulnerability trên large logic
- DefiHacks: đo khả năng detect trên các contract đã từng bị hack

Total: 388 projects
- Top200: 303 projects
- Web3Bugs: 72 projects
- DefiHack: 13 Projects

### Lớp 2 - Baseline so với các tool static analysis

3 đối tượng chính dùng để so sánh trong lớp này
- Slither - Static tool (stt)
- MScan
- pure GPT-based approach từ các nghiên cứu khác

Tuy nhiên: Lớp này không hoàn toàn công bằng vì: nhiều stt không cover đúng loại vulnerability mà GPTScan nhắm tới -> Chọn Slither + MScan vì có một số rule liên quan, ví dụ:
- rule target: rule đó nhắm tới loại vulnerability nào;
- rule scope: rule đó kiểm tra trong phạm vi nào;
- rule assumption: rule đó giả định bug có pattern gì;
- rule evidence: rule cần bằng chứng tĩnh nào để báo lỗi.

| Tool rule                           | Rule target                                      | Rule evidence                                        | Vì sao chưa đủ cho GPTScan                                                            |
| ----------------------------------- | ------------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Slither reentrancy detector         | Reentrancy                                       | External call trước khi update state                 | Phù hợp bug có control-flow pattern rõ, nhưng không hiểu logic nghiệp vụ              |
| Slither unchecked-transfer detector | Transfer không kiểm tra return value             | Có call transfer nhưng thiếu check                   | Bắt được misuse API, không bắt được invariant sai                                     |
| Access-control rule                 | Hàm nhạy cảm thiếu modifier/require              | Function thay đổi state quan trọng nhưng thiếu guard | Có thể bắt access bug đơn giản, nhưng khó hiểu quyền theo logic protocol              |
| MScan-related rules                 | Một số pattern liên quan đến DeFi/security logic | Dựa trên rule/static pattern                         | Có thể cover một phần logic bug, nhưng vẫn bị giới hạn bởi rule được định nghĩa trước |

Ví dụ cụ thể hơn:

```bash
function withdraw(uint amount) external {
    require(balance[msg.sender] >= amount);
    token.transfer(msg.sender, amount);
    balance[msg.sender] -= amount;
}
```

Static analyzer có thể phát hiện nguy cơ reentrancy vì có external trước khi cập nhật state

Tuy nhiên, nhưng với logic bug kiểu:

```bash
function claimReward() external {
    uint reward = totalReward / totalUsers;
    rewardToken.transfer(msg.sender, reward);
}
```

Solutions:

```bash
function claimReward() external {
    require(eligible[msg.sender], "not eligible"); // Kiểm tra
    require(!claimed[msg.sender], "already claimed"); // Cập nhật

    claimed[msg.sender] = true;

    uint256 reward = totalReward / totalUsers;

    rewardToken.transfer(msg.sender, reward);
}
```

Nếu contract không kiểm tra user đã claim chưa, lỗi không nhất thiết hiện ra như một pattern cú pháp đơn giản. Nó cần hiểu property nghiệp vụ:
-  Một user chỉ được claim reward một lần.
Đây là kiểu chỗ GPTScan muốn khai thác năng lực semantic reasoning của GPT.

Cân scenario cụ thể

### Lớp 3 - Ablation Baseline

Dựa trên kiến trúc của GPTScan thì có thể tách thành 3 phần riêng biệt:
| Biến thể                      | Cách hoạt động                                                                                    | Ý nghĩa                                                            |
| ----------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Static filtering only**     | Chỉ dùng static analysis để lọc candidate functions/statements                                    | Kiểm tra static analysis tự thân giúp thu hẹp search space đến đâu |
| **GPT-only recognition**      | GPT nhận diện vulnerability dựa trên candidate/context                                            | Kiểm tra GPT có hiểu semantic bug hay không                        |
| **GPT + static confirmation** | GPT nhận diện semantic pattern, sau đó static analysis xác nhận key variables/statements/property | Pipeline đầy đủ của GPTScan                                        |




Trong RQ3, paper cho thấy static confirmation làm giảm rất mạnh số case còn lại sau GPT matching: từ 647 raw functions xuống 221 raw functions trên Web3Bugs; paper kết luận static confirmation lọc khoảng 65.84% false positives.

Hiều: GPT có khả năng tìm ra các đoạn code “có vẻ giống” vulnerability scenario, nhưng nó dễ tạo ra nhiều candidate nhiễu. Static confirmation đóng vai trò kiểm chứng lại bằng bằng chứng chương trình cụ thể.

Đây là bằng chứng quan trọng cho luận điểm:
- Giá trị của GPTScan không nằm ở “GPT detect bug”, mà nằm ở pipeline hybrid: GPT semantic reasoning + static verification.

Ví dụ với bug “missing check before token transfer”:
GPT có thể nhận ra rằng một function thực hiện transfer token và có vẻ thiếu kiểm tra điều kiện. Nhưng static confirmation sẽ kiểm tra sâu hơn:

- biến nào là amount?
- biến nào là user balance?
- có require liên quan đến amount/balance không?
- state có được update đúng không?
- transfer có nằm trong nhánh điều kiện nào không?
- property cần kiểm tra có thật sự bị vi phạm không?

Nếu GPT chỉ nói “có vẻ nguy hiểm” thì chưa đủ. Static confirmation buộc kết quả phải có bằng chứng cụ thể trong code.

## Metric

Không có metric chính: mà paper dùng nhiều metric theo từng research question

| Metric              | Ý nghĩa                                           |
| ------------------- | ------------------------------------------------- |
| Precision           | trong các cảnh báo được report, bao nhiêu là đúng |
| Recall              | trong các lỗi thật, detect được bao nhiêu         |
| F1-score            | cân bằng precision và recall                      |
| False Positive Rate | đặc biệt quan trọng với Top200                    |
| Time / KLoC         | chi phí thời gian                                 |
| Cost / KLoC         | chi phí API GPT                                   |

Với Web3Bugs, paper báo cáo:

- TP = 40
- FP = 30
- FN = 8
- Precision = 40 / (40 + 30) = 57.14%
- Recall = 40 / (40 + 8) = 83.33%
- F1 = 67.8%

Với DefiHacks:

- TP = 10
- FP = 1
- FN = 4
- Precision = 90.91%
- Recall = 71.43%
- F1 = 80%


## Vì sao chỉ đạt 57.14% trên Web3Bugs? 
Adtraction: large project làm sẽ khó hơn
Cụ thể: Giải thích cụ thể vào ngày 3/6
- Nguyên nhân 1: Web3Bugs là project-level không phải single-contract/ token-level

Top200 chủ yếu phù hợp để đo false positive trên các contract phổ biến, nhiều trường hợp là token contract hoặc contract có logic tương đối chuẩn hóa. Nhưng Web3Bugs gồm các project được audit trên Code4rena, trung bình project có nhiều Solidity files và logic phân tán hơn. GPTScan paper cũng mô tả Web3Bugs là tập gồm large contract projects audited on Code4rena, khác với Top200/DefiHacks vốn nghiêng nhiều hơn về token/DeFi hack cases

- Nguyên nhân 2: Logic Vulnerability cần global business context

Logic bug thường phụ thuộc vào invariant cấp hệ thống: Những invariant này thường không được viết trực tiếp trong code. Chúng tồn tại như “thiết kế đúng” của protocol.

- Ví dụ
```bash
function deposit(uint256 amount) external {
    uint256 shares;

    if (totalSupply == 0) {
        shares = amount;
    } else {
        shares = amount * totalSupply / totalAssets();
    }

    _mint(msg.sender, shares);
    asset.transferFrom(msg.sender, address(this), amount);
}
```

Thoạt nhìn: an toàn: tuy nhiên lại có vấn đề ở TotalAssets() - nếu bị thao túng bằng một cách nào đó: hacker có thể làm biến đổi tỷ lệ shares

- Nguyên nhân 3: Static Confirmation

Paper kết luận static confirmation giảm 65.84% original false positive cases trên Web3Bugs. Tuy nhiên chưa đủ để xác nhận toàn bộ design-level vulnerability.

- Nguyên nhân 4: Prompt scenario/ property vẫn coarse-grained

Việc Human tự viết scenario + property bị thô, dù ý tưởng hay: GPT vẫn có thể nhầm bị price usage nhưng thực tế đã đươc protect ở nơi khác -> Tạo FP

- Nguyên nhân 5: LLM hiểu semantic tuy nhiên không hiểu design intent (dụng ý thiết kế)

LLM có thể hiểu tên hàm, tên biến, comment, luồng code. Nhưng nó không biết chắc tác giả thiết kế protocol với dụng ý gì.

ví dụ với hàm reward(): chúng có thể bị gọi nhiều lần: nhưng vẫn có khả năng dev đã viết một hàm nào đó ví dụ như tăng debt nếu bị gọi quá số lần được gọi: việc lấy reward =+ một khoản nợ như GPTScan không lây được context của hàm debt kia và nhận định lỗi: FP

```bash
function claimReward() external {
    uint256 reward = accumulatedReward[msg.sender] - rewardDebt[msg.sender];
    rewardDebt[msg.sender] = accumulatedReward[msg.sender];

    rewardToken.transfer(msg.sender, reward);
}
```

## Có ai phát triển thêm không? 
Có. Khá mạnh, chủ yếu theo 4 nhánh:
- Nhánh 1 - RAG + GPT: https://arxiv.org/pdf/2407.14838: Phát triển phân: GPT Scenario Matching: embedding + Pinecone + LangChain

Nhánh 2 - LLM Agent/ Multi Agent audit: https://daoyuan14.github.io/papers/TSE25_LLM-SmartAudit.pdf: Phát triển phần: GPT Scenario Matching
+ GPT Key Variable Recognition
+ Audit Reasoning Workflow

Nhánh 3 - Invariant inference: https://arxiv.org/html/2602.03271v1: LogicScan: Thay thế phần Human defined: Scenario + Property: bằng: tạo ra một "Skill" nhận diện thông qua việc học các protocol trên on-chain contract để hình thành một pattern

Nhánh 4 - Business Representation: có thể hiểu là tránh để GPT đọc raw code solidity
ví dụ LogicScan dùng: Business Specification Language -> normalized structure thành structured, verifiable logic representation
- Thay vì dùng scenario + property viết = tay: thì tạo ra một hệ thống biểu diễn các business invariant



Kết luận: Không dừng ở việc Detect: chuyển dấn sang:
- cung cấp đúng context
- đúng variant
- đúng workflow kiểm chứng
- đúng representation