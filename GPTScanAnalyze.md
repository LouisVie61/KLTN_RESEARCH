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

- để ý chỉ số: intent chung; ý nghĩa
- nền tảng viết smart contracts? so sánh 5 cái phổ biến nhất và chọn 1 thằng
deep understand
- học máy: ML cơ bản: lazy prediction
- giải thích: 3 bộ dữ liệu: đặc trưng, vì sao chọn, độ khác biệt giữa các datasets, điểm nào khác biệt

Với DefiHacks:

- TP = 10
- FP = 1
- FN = 4
- Precision = 90.91%
- Recall = 71.43%
- F1 = 80%

## Kết quả thực tế với dataset đang có trong workspace

Trong workspace hiện tại có 2 phần liên quan đến Web3Bugs:

- `datasets/Web3Bugs-source`: source code của 72 project Web3Bugs. Đếm nhanh bằng `rg --files datasets\Web3Bugs-source -g '*.sol'` cho thấy có 3613 file Solidity.
- `datasets/GPTScan-Web3Bugs`: repo kết quả/report của GPTScan cho Web3Bugs, gồm `web3bugs_res_temp0_230723.csv`, thư mục `reports/`, và `screenshots/`.

File kết quả `datasets/GPTScan-Web3Bugs/web3bugs_res_temp0_230723.csv` có đủ 72 dòng project. Dòng tổng ở cuối CSV là:

| Dataset | Rule cases | TP | TN | FP | FN | Total | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Web3Bugs | 232 | 40 | 154 | 30 | 8 | 232 | 57.14% | 83.33% | 67.80% |

Vì vậy 57.14% không phải là kết quả tôi chạy lại bằng Gemini. Nó là kết quả có sẵn trong dataset/release của GPTScan-Web3Bugs:

```text
Precision = TP / (TP + FP)
          = 40 / (40 + 30)
          = 57.14%
```

Run Gemini hiện tại của tôi không được dùng để claim accuracy. Kết quả thực tế ở `tmp/gptscan_gemini_visor_fixed/run_summary.md` là:

- Backend: `gemini`
- Project chạy: `10-LogicBug-Visorfinance/contracts`
- Status: `llm_failed`
- Compile success rate: `1.0`
- Lý do không hoàn tất: Gemini trả `429 RESOURCE_EXHAUSTED`, tức hết quota.
- Metadata project: 19 Solidity files, 25 contracts, 38 functions, 2775 LOC.
- Pipeline đã lọc được 38 functions sau parser/filter và còn 1 candidate sau step 1, nhưng dừng trước khi hoàn tất vì quota.

Nói cách khác: môi trường local đã chứng minh project compile được và GPTScan bắt đầu đi vào pipeline, nhưng chưa đủ quota để tái tạo precision/recall.

### So sánh dataset theo số lượng source phải xử lý

Tôi đã clone thêm 2 dataset chính thức của GPTScan vào workspace:

- `datasets/GPTScan-Top200`: có source Solidity và file kết quả `top200_result.csv`.
- `datasets/GPTScan-DefiHacks`: có `defihack_res_temp0_230723.csv`, 13 PDF reports, 13 screenshots. Repo này không chứa source `.sol`, nên trong workspace hiện tại chỉ so sánh được metric/report, chưa so sánh được số file source phải xử lý.

Bảng thống kê local hiện tại:

| Dataset local | Mục đích trong paper | Project/cases | Solidity files local | LOC local | Kết quả local có sẵn |
| --- | --- | ---: | ---: | ---: | --- |
| `datasets/GPTScan-Top200` | Stress-test false positives trên audited/popular contracts | 303 projects | 1020 | 181685 | `top200_result.csv`: 296 false-positive reports; 126/303 projects có ít nhất 1 FP; 177/303 projects có 0 FP |
| `datasets/Web3Bugs-source` + `datasets/GPTScan-Web3Bugs` | Detect logic bugs trong large audited projects | 72 projects / 232 rule cases | 3613 | 372452 | `web3bugs_res_temp0_230723.csv`: TP=40, TN=154, FP=30, FN=8, Precision=57.14%, Recall=83.33% |
| `datasets/GPTScan-DefiHacks` | Detect trên các DeFi hack đã biết | 13 hack cases / 34 rule cases | 0 trong repo đã publish | không có source local | `defihack_res_temp0_230723.csv`: TP=10, TN=19, FP=1, FN=4, Precision=90.91%, Recall=71.43% |

Điểm rút ra từ bảng này:

- Web3Bugs là dataset nặng nhất trong workspace về source code: 72 project nhưng 3613 Solidity files và 372452 LOC. Trung bình một project Web3Bugs có khoảng 50 file Solidity.
- Top200 có nhiều project hơn, 303 project, nhưng chỉ 1020 Solidity files và 181685 LOC. Trung bình khoảng 3.37 file Solidity/project. Nó phù hợp để đo false positive trên contract phổ biến hơn là đo khả năng hiểu logic phức tạp cấp hệ thống.
- DefiHacks có ít case nhất: 13 hack cases và 34 rule cases. Kết quả precision cao hơn Web3Bugs, nhưng repo public hiện có không kèm source `.sol`, nên trong workspace hiện tại chỉ dùng được CSV/report để so sánh metric.

Nếu cần phản biện rằng Web3Bugs khó hơn Top200/DefiHacks, nên nói bằng số:

```text
Web3Bugs: 72 projects, 3613 Solidity files, 372452 LOC, 232 rule cases
Top200:   303 projects, 1020 Solidity files, 181685 LOC, false-positive-only benchmark
DefiHacks: 13 hack cases, source không nằm trong repo publish hiện tại, 34 rule cases
```

So sánh này giải thích vì sao cùng là GPTScan nhưng Web3Bugs có precision 57.14%: đây không chỉ là nhiều project, mà là nhiều file/module trong mỗi project và bug logic phụ thuộc invariant cấp hệ thống. Top200 có nhiều project hơn nhưng mỗi project thường nhỏ hơn và mục tiêu chính là kiểm tra GPTScan có báo nhầm trên audited/token contracts không. DefiHacks thì ít case hơn và tập trung vào exploit đã biết, nên bài toán định vị pattern hack cụ thể khác với audit project-level như Web3Bugs.

## Vì sao GPTScan chỉ đạt 57.14% precision trên Web3Bugs?

Kết quả 57.14% precision trên Web3Bugs không nên được hiểu đơn giản là GPTScan “kém” trong việc phát hiện lỗi smart contract. Theo tôi, kết quả này phản ánh rõ hơn độ khó của Web3Bugs với tư cách là một benchmark project-level, nơi vulnerability không chỉ nằm trong một function hoặc một contract đơn lẻ, mà thường phụ thuộc vào quan hệ giữa nhiều file, nhiều contract, nhiều state variable và nhiều flow nghiệp vụ.

Tiếp cận Web3Bugs dưới góc nhìn hệ thống và benchmark: phân tích số liệu TP/FP/FN/TN, cấu trúc project, và dùng một số đoạn code để minh họa vì sao GPTScan dễ phát sinh false positive trên các project lớn.

Về mặt định lượng, từ CSV hiện có, 72 project trong Web3Bugs tạo ra 232 case đánh giá. GPTScan phát hiện đúng 40 true positive case, nhưng đồng thời cũng tạo ra 30 false positive case. Vì vậy:

Precision = TP / (TP + FP)
          = 40 / (40 + 30)
          = 57.14%

Điểm đáng chú ý là recall vẫn đạt 83.33%. Điều này cho thấy GPTScan vẫn bắt được phần lớn vulnerability thật, nhưng số false positive cao đã kéo precision xuống. Nói cách khác, vấn đề chính của GPTScan trên Web3Bugs không phải là “không phát hiện được lỗi”, mà là “phát hiện đúng nhưng cũng báo nhầm nhiều”.

Nguyên nhân 1: Web3Bugs là project-level benchmark, không phải single-contract benchmark

Một nguyên nhân quan trọng là Web3Bugs đánh giá các project lớn, không phải chỉ các contract đơn lẻ. Trong thực tế, nhiều lỗi smart contract không thể hiểu đầy đủ nếu chỉ nhìn một file hoặc một function. Logic của protocol thường được chia ra nhiều module, nhiều contract cha/con, nhiều interface và nhiều flow tương tác.

Ví dụ, project 10-LogicBug-Visorfinance không phải là một single-contract project. Cấu trúc source của project có nhiều thư mục như:

contracts/
  factory/
  hypervisor/
  interfaces/
  mock/
  visor/

Riêng thư mục contracts/visor đã có nhiều file như:

EIP712.sol
ERC1271.sol
OwnableERC721.sol
Visor.sol
VisorFactory.sol

Ngoài ra còn có các file khác như:

Mainframe.sol
RewardsToken.sol
StakingToken.sol

Run metadata cũng ghi nhận project này có 19 files, 25 contracts, 38 functions và 2775 LOC. Với cấu trúc như vậy, việc xác nhận một cảnh báo vulnerability không thể chỉ dựa trên một đoạn code cục bộ. Detector cần hiểu quan hệ giữa các contract, vai trò của từng module và luồng dữ liệu/chức năng đi qua nhiều file.

Điều này giải thích vì sao Web3Bugs khó hơn các benchmark thiên về contract-level. Khi context bị phân tán, model dễ thiếu một phần thông tin quan trọng, từ đó tạo ra false positive hoặc bỏ sót lỗi thật.

**Nguyên nhân 2**: Logic vulnerability cần hiểu invariant cấp protocol

Nhiều bug trong Web3Bugs thuộc nhóm logic vulnerability. Đây là loại lỗi khó vì nó không nhất thiết xuất hiện dưới dạng pattern rõ ràng như reentrancy, integer overflow hay thiếu access control ở một dòng cụ thể. Thay vào đó, bug thường liên quan đến việc protocol vi phạm một invariant nào đó.

Invariant có thể hiểu đơn giản là “điều kiện đúng mà hệ thống luôn phải duy trì”. Ví dụ:

Người không có quyền không được rút tài sản.
Số share mint ra phải phản ánh đúng lượng asset deposit.
Reward không được claim nhiều hơn phần người dùng được hưởng.
NFT bị lock thì không được transfer ra ngoài.

Những invariant này không phải lúc nào cũng được viết rõ trong code. Vì vậy, detector phải suy luận từ nhiều function và nhiều trạng thái khác nhau.

Ví dụ trong Visor.sol, các function liên quan đến NFT nằm ở nhiều vị trí khác nhau:

function _addNft(address nftContract, uint256 tokenId) internal {
  nfts.push(
    Nft({
      tokenId: tokenId,
      nftContract: nftContract
    })
  );
  emit AddNftToken(nftContract, tokenId);
}

function transferERC721(
    address to,
    address nftContract,
    uint256 tokenId
) external {
    if(msg.sender != _getOwner()) {
      require(
        nftApprovals[keccak256(abi.encodePacked(msg.sender, nftContract, tokenId))],
        "NFT not approved for transfer"
      );
    }

    _removeNft(nftContract, tokenId);
    IERC721(nftContract).safeTransferFrom(address(this), to, tokenId);
}

function onERC721Received(
    address operator,
    address from,
    uint256 tokenId,
    bytes calldata
) external override returns (bytes4) {
  _addNft(msg.sender, tokenId);
  return IERC721Receiver.onERC721Received.selector;
}

Nếu chỉ nhìn từng function riêng lẻ, đây có thể giống một flow ERC721 bình thường: contract nhận NFT, ghi nhận metadata, sau đó owner hoặc người được approve có thể transfer NFT ra ngoài. Tuy nhiên, để kết luận flow này có lỗi logic hay không, cần hiểu thêm các quan hệ khác:

Ai là owner thật sự của vault?
NFT được gửi vào vault trong hoàn cảnh nào?
NFT được ghi nhận trong mảng nfts với ý nghĩa gì?
Approval được cấp bởi ai và trong trường hợp nào?
Lock/unlock NFT được xử lý ở đâu?
Invariant của vault đối với NFT là gì?

Đây là điểm khiến logic vulnerability khó hơn pattern vulnerability. Nếu model không lấy đủ context liên quan đến ownership, approval, asset accounting và lock/unlock flow, nó có thể báo nhầm hoặc kết luận thiếu chính xác.

**Nguyên nhân 3**: Static confirmation giúp giảm false positive nhưng không đủ cho design-level bug

GPTScan không chỉ dùng LLM để đọc code, mà còn có bước static confirmation nhằm kiểm tra lại các cảnh báo và giảm false positive. Đây là một điểm mạnh của pipeline hybrid. Tuy nhiên, static analysis vẫn có giới hạn, đặc biệt với các lỗi mang tính design-level hoặc business-logic-level.

Static analysis thường mạnh khi kiểm tra các quan hệ tương đối rõ trong code, ví dụ:

Có external call hay không?
Biến state có được update trước/sau call không?
Function có modifier không?
Một require condition có tồn tại không?
Data có flow từ source đến sink không?

Nhưng với logic vulnerability, câu hỏi thường phức tạp hơn:

Cách tính share có phản ánh đúng tài sản thật không?
Reward accounting có bị lệch qua nhiều lần update không?
Price dùng trong protocol có thể bị thao túng qua flow khác không?
Một trạng thái có hợp lệ theo thiết kế protocol không?

Ví dụ tổng quát:
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

Nhìn cục bộ, đoạn code này có vẻ hợp lý. Nếu chưa có share thì mint theo amount; nếu đã có share thì mint theo tỷ lệ giữa amount, totalSupply và totalAssets. Tuy nhiên, nếu totalAssets() có thể bị thao túng thông qua donation, stale accounting, flash loan hoặc một flow khác, attacker có thể làm sai lệch số share được mint.

Điểm khó là static analysis không dễ xác nhận đầy đủ câu hỏi: totalAssets() có thật sự phản ánh đúng giá trị tài sản của vault trong mọi trạng thái hay không? Đây là dạng property phụ thuộc vào thiết kế kinh tế và accounting model của protocol, không chỉ phụ thuộc vào một dòng code.

Ngoài ra, trong CSV cũng có một số project được đánh dấu StaticFail. Điều này cho thấy trong một số trường hợp, compile/static-analysis context không đầy đủ hoặc không ổn định. Khi static layer không xác nhận được đầy đủ, pipeline sẽ khó loại bỏ false positive hơn.

**Nguyên nhân 4**: Scenario/property trong prompt vẫn có thể quá rộng

Một ý tưởng quan trọng của GPTScan là mô tả vulnerability thông qua scenario và property. Cách làm này hợp lý, vì logic bug thường cần được diễn đạt bằng điều kiện nghiệp vụ thay vì chỉ pattern code. Tuy nhiên, nếu scenario/property quá rộng, model có thể “over-report”, tức là báo lỗi cả ở những trường hợp thực tế đã được bảo vệ ở nơi khác.

Ví dụ, trong CSV có nhiều project vừa có true positive, vừa có false positive:

Project	TP	TN	FP	FN	Ghi chú
10-LogicBug-Visorfinance	1	2	0	0	Case tốt, không FP
12-2021-05-yield	1	1	1	0	Có 1 FP loại FD
23-2021-08-notional	0	3	1	1	Có FP loại SP và miss 1 FLP
70-2021-12-vader	3	1	1	1	Detect được nhiều nhưng vẫn có FP và FN
193-2022-12-caviar	0	0	1	2	Case xấu, vừa FP vừa miss bug thật

Các ví dụ này cho thấy GPTScan không phải thất bại hoàn toàn. Nó vẫn có tín hiệu đúng, nhưng cũng có xu hướng báo nhầm trong một số project. Một nguyên nhân có thể là scenario/property chưa đủ đặc thù cho từng protocol.

Ví dụ, model có thể thấy một function liên quan đến reward và nghi ngờ double-claim. Nhưng thực tế, protection có thể nằm ở một biến debt được update ở function khác. Hoặc model thấy price được dùng trong một phép tính và nghi ngờ price manipulation, nhưng thực tế price đó có thể đã được bảo vệ bởi oracle wrapper hoặc validation layer ở nơi khác.

Điều này làm tăng false positive, vì model nhìn thấy “dấu hiệu nguy hiểm” nhưng chưa xác nhận đủ toàn bộ ngữ cảnh bảo vệ.

**Nguyên nhân 5**: LLM hiểu code semantic nhưng khó chắc chắn về design intent

LLM có thể hiểu tên hàm, tên biến, comment và control flow ở mức khá tốt. Tuy nhiên, một protocol không chỉ có code, mà còn có dụng ý thiết kế. Đây là phần khó hơn nhiều.

Ví dụ:

function claimReward() external {
    uint256 reward = accumulatedReward[msg.sender] - rewardDebt[msg.sender];
    rewardDebt[msg.sender] = accumulatedReward[msg.sender];

    rewardToken.transfer(msg.sender, reward);
}

Trong Web3Bugs, các lỗi logic thường phụ thuộc vào chính phần design intent này. Do đó, chỉ dùng semantic understanding của LLM là chưa đủ để xác nhận chắc chắn vulnerability.

Liên hệ lại với con số 57.14%

Từ các nguyên nhân trên, precision 57.14% có thể được giải thích như sau:

GPTScan vẫn phát hiện được nhiều vulnerability thật,
nhưng khi chuyển sang project-level benchmark như Web3Bugs,
số false positive tăng lên do context phức tạp, logic phân tán,
static confirmation chưa đủ mạnh, và scenario/property chưa đủ đặc thù.

Nói cách khác, Web3Bugs làm lộ ra giới hạn của GPTScan ở bài toán protocol-level reasoning. GPTScan không yếu ở việc đọc code cục bộ, nhưng gặp khó khi phải xác nhận các invariant cấp protocol trải qua nhiều file, nhiều contract và nhiều flow nghiệp vụ.

Do đó, precision 57.14% không chỉ phản ánh chất lượng của LLM, mà còn phản ánh độ khó của toàn bộ pipeline detection khi áp dụng vào project-level logic vulnerability detection.

Kết luận

Với góc nhìn của tôi, GPTScan đạt precision 57.14% trên Web3Bugs chủ yếu vì Web3Bugs là benchmark khó hơn nhiều so với các tập contract-level. Trong Web3Bugs, vulnerability thường không thể xác nhận bằng một pattern đơn giản hay một function riêng lẻ. Nó yêu cầu hiểu quan hệ giữa nhiều module, nhiều state variable và invariant thiết kế của protocol.

Vì vậy, kết quả này cho thấy GPTScan có tiềm năng ở việc hỗ trợ phát hiện vulnerability, đặc biệt khi recall vẫn cao, nhưng vẫn còn hạn chế lớn trong việc giảm false positive trên các project smart contract phức tạp. Đây cũng là lý do khi tái hiện hoặc đánh giá GPTScan, tôi cần phân tích không chỉ theo số liệu tổng hợp, mà còn theo từng nhóm lỗi, từng project, và nguyên nhân tạo ra false positive.

## Có ai phát triển thêm không? 
Có. Khá mạnh, chủ yếu theo 4 nhánh:
- Nhánh 1 - RAG + GPT: https://arxiv.org/pdf/2407.14838: Phát triển phân: GPT Scenario Matching: embedding + Pinecone + LangChain

- Nhánh 2 - LLM Agent/ Multi Agent audit: https://daoyuan14.github.io/papers/TSE25_LLM-SmartAudit.pdf: Phát triển phần: GPT Scenario Matching
+ GPT Key Variable Recognition
+ Audit Reasoning Workflow

- Nhánh 3 - Invariant inference: https://arxiv.org/html/2602.03271v1: LogicScan: Thay thế phần Human defined: Scenario + Property: bằng: tạo ra một "Skill" nhận diện thông qua việc học các protocol trên on-chain contract để hình thành một pattern

- Nhánh 4 - Business Representation: có thể hiểu là tránh để GPT đọc raw code solidity
ví dụ LogicScan dùng: Business Specification Language -> normalized structure thành structured, verifiable logic representation
- Thay vì dùng scenario + property viết = tay: thì tạo ra một hệ thống biểu diễn các business invariant



Kết luận: Không dừng ở việc Detect: chuyển dấn sang:
- cung cấp đúng context
- đúng variant
- đúng workflow kiểm chứng
- đúng representation

```bash
$env:GPTSCAN_LLM_BACKEND="gemini"
$env:GPTSCAN_GEMINI_ENV="D:\KLTN_Research\demo\.env"

cd D:\KLTN_Research\GPTScan\src

D:\KLTN_Research\GPTScan\.venv\Scripts\python.exe main.py `
  -s D:\KLTN_Research\datasets\Web3Bugs-source\10-LogicBug-Visorfinance\contracts `
  -o D:\KLTN_Research\tmp\gptscan_gemini_visor_direct\output.json `
  -k GEMINI_BACKEND
```
