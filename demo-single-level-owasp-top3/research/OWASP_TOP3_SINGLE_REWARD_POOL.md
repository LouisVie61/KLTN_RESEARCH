# Nghiên cứu 3 phương án tấn công và phòng thủ áp dụng cho `SingleRewardPool`

## 0. Phạm vi và phương pháp

Tài liệu này không khảo sát toàn bộ Web3. Phạm vi được giới hạn ở:

- Ethereum/EVM;
- Solidity `0.8.20`;
- DeFi reward pool đơn cấp;
- block-based reward accounting;
- local Hardhat attack reproduction.

Ba nhóm được chọn từ OWASP Smart Contract Top 10:2026:

1. SC01 — Access Control Vulnerabilities;
2. SC02 — Business Logic Vulnerabilities;
3. SC05 — Lack of Input Validation.

Lý do chọn: cả ba xuất hiện tự nhiên trong trust boundary và state model của
`SingleRewardPool`. Price oracle và flash loan không được ép vào contract này vì
nó không định giá tài sản từ AMM/oracle và không có lending/borrowing primitive.

Mỗi nhóm được phân tích bằng cùng một khung:

```text
Definition
Protected asset
Expected invariant
Root cause
Preconditions
Attack sequence
Exploitability
Vulnerable implementation
Reproduction test
Defense
Residual risk
Detection
Mapping
Sources
```

---

# 1. SC01 — Access Control Vulnerabilities

## Definition

Access-control vulnerability xảy ra khi contract không thực thi đúng việc ai
được phép gọi privileged behavior, trong điều kiện nào, và với phạm vi quyền nào.
Trong reward pool, privileged behavior gồm thay đổi reward rate, fee, treasury,
owner, pause state hoặc emergency action.

Câu hỏi phân loại trung tâm:

```text
Caller này có quyền thực hiện hành động không?
```

## Protected asset

- Reward reserve trong pool;
- principal của depositor nếu admin có chức năng rescue/withdraw;
- `rewardPerBlock` và các tham số kinh tế;
- ownership và governance authority;
- availability của `deposit`, `withdraw`, `claim`;
- tính toàn vẹn của protocol configuration.

## Expected invariant

```text
msg.sender không có quyền quản trị
⇒
không thể thay đổi rewardPerBlock, fee hoặc critical state.
```

Với contract dùng owner đơn:

```text
setRewardPerBlock(newRate) chỉ thành công khi msg.sender == owner.
```

## Root cause

Các root cause phổ biến:

- thiếu `onlyOwner`/`onlyRole`;
- modifier được gắn nhầm function;
- role admin cấu hình sai;
- dùng `tx.origin` để authorization;
- initializer/proxy initialization không được khóa;
- trusted forwarder, router hoặc cross-chain sender được xác thực sai;
- quyền quá lớn được dồn vào một EOA.

Trong vulnerable demo, function cố ý không có modifier:

```solidity
function setRewardPerBlockUnauthorized(
    uint256 newRewardPerBlock
) external {
    _updatePool();
    rewardPerBlock = newRewardPerBlock;
}
```

`_updatePool()` được gọi để tránh trộn SC01 với retroactive accounting bug. Root
cause ở đây chỉ là thiếu authorization.

## Preconditions

- Contract đã deploy và có reward configuration;
- function thay đổi rate là `external`;
- attacker biết contract address và ABI;
- function không yêu cầu quyền;
- attacker có đủ native token để trả gas.

Không cần flash loan hoặc vốn lớn.

## Attack sequence

```text
1. Pool đang trả 1 DRW/block.
2. Attacker gọi setRewardPerBlockUnauthorized(1000 DRW/block).
3. Contract chấp nhận vì không kiểm tra msg.sender.
4. Reward liability tăng mạnh.
5. Attacker hoặc account phối hợp deposit/claim.
6. Reward reserve có thể bị rút cạn hoặc pool mất khả năng thanh toán.
```

## Exploitability

Mức độ có thể là **Critical** nếu function cho phép:

- chuyển reserve;
- mint token;
- đổi owner/admin;
- upgrade implementation;
- cấu hình rate/fee tạo đường rút tài sản.

Trong mini-demo, test trực tiếp chứng minh attacker thay đổi được
`rewardPerBlock`. Việc rút cạn pool là impact tiếp theo phụ thuộc reserve và
accounting sequence.

## Vulnerable implementation

File:

```text
contracts/OWASPTop3VulnerableRewardPool.sol
```

Function:

```solidity
function setRewardPerBlockUnauthorized(
    uint256 newRewardPerBlock
) external {
    _updatePool();
    rewardPerBlock = newRewardPerBlock;
}
```

## Reproduction test

```javascript
it("vulnerable pool lets an attacker change the reward rate", async function () {
  const { attacker, vulnerable } = await deployFixture();
  const maliciousRate = ethers.parseEther("1000");

  await vulnerable
    .connect(attacker)
    .setRewardPerBlockUnauthorized(maliciousRate);

  expect(await vulnerable.rewardPerBlock())
    .to.equal(maliciousRate);
});
```

Security evidence:

```text
Expected: unauthorized transaction reverts.
Observed: transaction succeeds and critical state changes.
```

## Defense

Minimum defense:

```solidity
modifier onlyOwner() {
    require(msg.sender == owner, "only owner");
    _;
}

function setRewardPerBlock(uint256 newRate)
    external
    onlyOwner
{
    // ...
}
```

Production-oriented defenses:

- OpenZeppelin `Ownable2Step` cho một admin đơn;
- `AccessControl` nếu có nhiều role;
- tách `RATE_MANAGER_ROLE`, `PAUSER_ROLE`, `TREASURY_ROLE`;
- multisig thay cho EOA đơn;
- timelock cho thay đổi economic configuration;
- event cho grant/revoke/config change;
- negative authorization tests cho mọi privileged function;
- least privilege và periodic permission review.

## Residual risk

Sau khi thêm `onlyOwner`:

- owner key vẫn có thể bị đánh cắp;
- owner có thể hành động độc hại;
- multisig signers có thể thông đồng;
- role admin có thể cấp quyền sai;
- timelock có thể quá ngắn;
- authorized action vẫn có thể chứa SC02 hoặc SC05 bug.

`onlyOwner` trả lời “ai được gọi”, không chứng minh “giá trị có an toàn” hoặc
“logic có đúng”.

## Detection

- Liệt kê tất cả `public`/`external` functions;
- đánh dấu function thay đổi critical state;
- kiểm tra modifier, role và inheritance;
- viết test từ owner, user thường và attacker;
- kiểm tra ownership transfer và revoke/grant;
- chạy static analysis, sau đó manual review;
- review proxy initializer và upgrade admin nếu có;
- theo dõi event và quyền thực tế sau deployment.

## Mapping

- OWASP Smart Contract Top 10:2026: **SC01**;
- SCSVS: Authentication and Authorization;
- weakness family: missing/incorrect authorization;
- category boundary:
  - caller không có quyền → SC01;
  - caller có quyền nhưng parameter ngoài giới hạn → SC05;
  - caller và parameter hợp lệ nhưng state transition sai → SC02.

## Sources

- https://scs.owasp.org/sctop10/
- https://scs.owasp.org/sctop10/SC01-AccessControlVulnerabilities/
- https://docs.openzeppelin.com/contracts/5.x/access-control
- https://docs.openzeppelin.com/contracts/5.x/api/access

---

# 2. SC02 — Business Logic Vulnerabilities

## Definition

Business-logic vulnerability xảy ra khi contract thực thi các câu lệnh hợp lệ
nhưng quy tắc kinh tế, state transition hoặc invariant được mô hình hóa sai.
Type safety, access control và input validation có thể đều đúng mà hệ thống vẫn
cho phép kết quả không an toàn.

Câu hỏi phân loại trung tâm:

```text
Giả sử caller và input đều hợp lệ,
quy tắc nghiệp vụ và thứ tự cập nhật state có còn an toàn không?
```

## Protected asset

- Reward token reserve;
- quyền nhận reward đúng của từng user;
- sự công bằng giữa user stake ở các thời điểm khác nhau;
- `accRewardPerShare`, `lastRewardBlock`, `rewardDebt`;
- solvency và khả năng claim của pool;
- niềm tin rằng mỗi reward epoch dùng đúng rate.

## Expected invariant

Mỗi block phải dùng rate có hiệu lực trong chính block đó.

Ví dụ:

```text
10 block ở rate 1
+ 5 block ở rate 10
=
10 × 1 + 5 × 10
```

Không được tính toàn bộ 15 block bằng rate mới.

Invariant epoch:

```text
accruedReward
=
Σ(blocksElapsedInEpoch × rateOfEpoch).
```

## Root cause

`rewardPerBlock` được ghi trước khi phần reward của epoch cũ được checkpoint:

```solidity
function setRewardPerBlockRetroactive(
    uint256 newRewardPerBlock
) external onlyOwner {
    rewardPerBlock = newRewardPerBlock;
}
```

Lần `_updatePool()` sau đó dùng rate đang lưu tại thời điểm gọi:

```solidity
uint256 rewards =
    (block.number - lastRewardBlock)
    * rewardPerBlock;
```

Do đó các block cũ bị định giá bằng rate mới.

Đây chính là semantic bug đã tồn tại có chủ đích trong `SingleRewardPool` ban
đầu. `rewardDebt` không sửa được lỗi này vì nó chỉ checkpoint user accounting;
global accumulator đã bị cập nhật sai từ trước.

## Preconditions

- Có user đang deposit;
- `totalDeposited > 0`;
- một số block đã trôi qua;
- `_updatePool()` chưa chạy trong khoảng đó;
- authorized owner thay đổi reward rate;
- thao tác sau đó gọi `_updatePool()` hoặc `claim()`.

Không cần unauthorized caller. Vì vậy đây không phải SC01.

## Attack sequence

```text
1. Alice deposit 100 DST khi rate = 1 DRW/block.
2. 10 block trôi qua.
3. Owner đổi rate thành 10 DRW/block.
4. Contract không checkpoint 10 block cũ.
5. 5 block tiếp tục trôi qua.
6. Alice gọi claim().
7. _updatePool() tính cả khoảng cũ theo rate 10.
8. Alice nhận reward cao hơn thiết kế.
```

## Exploitability

Mức độ **High** khi attacker có thể:

- chiếm admin key;
- thao túng governance;
- phối hợp với depositor đã stake;
- front-run/back-run quanh thời điểm đổi rate;
- claim trước khi reward reserve cạn.

Lỗi cũng có thể xảy ra do vận hành bình thường, không cần attacker. Kết quả:

- overpayment hoặc underpayment;
- reward reserve cạn;
- user claim sau bị revert;
- phân phối không công bằng giữa các epoch.

## Vulnerable implementation

File:

```text
contracts/OWASPTop3VulnerableRewardPool.sol
```

Function:

```solidity
function setRewardPerBlockRetroactive(
    uint256 newRewardPerBlock
) external onlyOwner {
    rewardPerBlock = newRewardPerBlock;
}
```

## Reproduction test

```javascript
await vulnerable.connect(alice)
  .deposit(ethers.parseEther("100"));

await network.provider.send("hardhat_mine", ["0xa"]);

await vulnerable.connect(owner)
  .setRewardPerBlockRetroactive(
    ethers.parseEther("10")
  );

await network.provider.send("hardhat_mine", ["0x5"]);
await vulnerable.connect(alice).claim();

const paid = await reward.balanceOf(alice.address);
expect(paid > ethers.parseEther("100")).to.equal(true);
```

Test dùng inequality thay cho một con số tuyệt đối vì các transaction
`deposit`, `setRewardPerBlock` và `claim` cũng được mine thành block trên Hardhat.
Điều cần chứng minh là old-rate boundary bị phá vỡ.

## Defense

Checkpoint global accounting trước khi đổi rate:

```solidity
function setRewardPerBlock(uint256 newRate)
    external
    onlyOwner
{
    require(newRate > 0, "rate is zero");

    _updatePool();

    uint256 oldRate = rewardPerBlock;
    rewardPerBlock = newRate;

    emit RewardPerBlockChanged(oldRate, newRate);
}
```

Các defense bổ sung:

- mô hình reward theo epoch rõ ràng;
- upper bound và budget check cho rate;
- timelock và event;
- reference model ngoài chain để differential test;
- stateful fuzz sequence:
  `deposit → mine → changeRate → mine → claim`;
- invariant tổng reward theo từng epoch;
- kiểm tra principal liability tách khỏi reward liability.

## Residual risk

- rate mới vẫn có thể quá cao cho tương lai;
- reward reserve có thể không đủ;
- integer rounding vẫn tạo dust;
- nhiều lần đổi rate có thể tạo edge case;
- compromised owner vẫn có thể cấu hình độc hại;
- token behavior có thể gây external-call risk;
- một user claim trước có thể nhận token, user sau chịu insolvency nếu reserve
  không được kiểm soát.

## Detection

Static analysis thường khó phát hiện vì từng câu lệnh hợp lệ. Phương pháp phù
hợp hơn:

- manual state-transition review;
- viết expected invariant trước test;
- model-based/differential testing;
- sequence tests qua nhiều block;
- stateful fuzzing;
- kiểm tra event timeline;
- so sánh một lần update dài với nhiều lần update ngắn;
- review mọi configuration function ảnh hưởng accumulator.

## Mapping

- OWASP Smart Contract Top 10:2026: **SC02**;
- SCSVS: business logic/economic security;
- weakness family: wrong state-transition ordering, missing checkpoint;
- category boundary:
  - owner có quyền, rate có thể hợp lệ, nhưng epoch accounting sai → SC02;
  - người thường đổi rate → SC01;
  - rate vượt documented bound → SC05.

## Sources

- https://scs.owasp.org/sctop10/
- https://scs.owasp.org/sctop10/SC02-BusinessLogicVulnerabilities/
- Existing `demo-single-level/SingleRewardPool.sol` and tests.

---

# 3. SC05 — Lack of Input Validation

## Definition

Lack of input validation xảy ra khi contract nhận parameter, calldata, signed
payload hoặc external message nhưng không kiểm tra đầy đủ format, range, unit,
address, freshness hoặc operation context.

Câu hỏi phân loại trung tâm:

```text
Caller có thể hợp lệ,
nhưng giá trị được truyền vào có nằm trong miền an toàn không?
```

## Protected asset

- Principal của depositor;
- economic configuration của pool;
- khả năng deposit/withdraw;
- treasury/fee routing;
- contract availability;
- tính hợp lệ của token, owner và recipient addresses.

## Expected invariant

Với basis points:

```text
0 <= depositFeeBps <= MAX_DEPOSIT_FEE_BPS <= 10_000.
```

Trong demo, policy được chọn:

```text
MAX_DEPOSIT_FEE_BPS = 1_000, tức 10%.
```

Với deposit:

```text
amount > 0
creditedAmount = amount - fee > 0.
```

Với constructor/admin address:

```text
stakingToken != address(0)
rewardToken != address(0)
newOwner != address(0).
```

## Root cause

Vulnerable setter chấp nhận mọi `uint256`:

```solidity
function setDepositFeeBpsUnchecked(
    uint256 newFeeBps
) external onlyOwner {
    depositFeeBps = newFeeBps;
}
```

Access control đúng: chỉ owner gọi được. Tuy nhiên không có economic bound.
Owner có thể đặt `10_000`, làm fee bằng 100% deposit.

Vulnerable deposit không yêu cầu `creditedAmount > 0`:

```solidity
uint256 fee = amount * depositFeeBps / 10_000;
uint256 creditedAmount = amount - fee;
```

Khi fee bằng 100%, toàn bộ 100 DST được chuyển đến owner và user nhận zero
accounting credit.

## Preconditions

- owner hoặc governance gọi setter;
- setter thiếu upper bound;
- user tiếp tục deposit sau cấu hình;
- frontend/monitoring không cảnh báo hoặc user không kiểm tra fee;
- contract cho phép net amount bằng zero.

Trường hợp này có thể là:

- cấu hình nhầm;
- malicious governance/admin;
- compromised admin key;
- proposal payload sai unit.

## Attack sequence

```text
1. Owner đặt depositFeeBps = 10_000.
2. Alice approve 100 DST.
3. Alice gọi depositWithConfiguredFee(100 DST).
4. Contract nhận 100 DST.
5. Fee = 100 DST.
6. Toàn bộ 100 DST chuyển tới owner.
7. creditedAmount = 0.
8. Alice không có principal để withdraw.
```

## Exploitability

Mức độ **High** nếu:

- admin key bị chiếm;
- fee change không có timelock;
- frontend không hiển thị fee;
- user dùng automation/bot tiếp tục deposit;
- fee recipient do attacker kiểm soát.

Trong mô hình chỉ có trusted owner, đây vẫn là availability/configuration risk.
Không nên gọi đây là unauthorized access vì caller có quyền. Root cause là
unsafe input domain.

## Vulnerable implementation

File:

```text
contracts/OWASPTop3VulnerableRewardPool.sol
```

Functions:

```solidity
function setDepositFeeBpsUnchecked(
    uint256 newFeeBps
) external onlyOwner {
    depositFeeBps = newFeeBps;
}
```

và:

```solidity
uint256 fee = amount * depositFeeBps / 10_000;
uint256 creditedAmount = amount - fee;
// Missing: require(creditedAmount > 0)
```

## Reproduction test

```javascript
const ownerBefore = await stake.balanceOf(owner.address);

await vulnerable.connect(owner)
  .setDepositFeeBpsUnchecked(10_000);

await vulnerable.connect(alice)
  .depositWithConfiguredFee(
    ethers.parseEther("100")
  );

expect(await vulnerable.deposited(alice.address))
  .to.equal(0n);

expect(await stake.balanceOf(owner.address))
  .to.equal(
    ownerBefore + ethers.parseEther("100")
  );
```

Security evidence:

```text
Input accepted: 10_000 bps.
Observable effect: user transfers 100 DST and receives zero deposit credit.
```

## Defense

Validate at the boundary:

```solidity
uint256 public constant MAX_DEPOSIT_FEE_BPS = 1_000;

function setDepositFeeBps(uint256 newFeeBps)
    external
    onlyOwner
{
    require(
        newFeeBps <= MAX_DEPOSIT_FEE_BPS,
        "fee too high"
    );
    depositFeeBps = newFeeBps;
}
```

Validate the derived value too:

```solidity
uint256 fee = amount * depositFeeBps / 10_000;
uint256 creditedAmount = amount - fee;
require(creditedAmount > 0, "net amount is zero");
```

Broader defense checklist:

- positive amount checks;
- non-zero token/owner/recipient addresses;
- basis-point bounds;
- maximum reward rate and budget constraints;
- explicit units and decimals;
- deadline/slippage checks where applicable;
- custom errors for clear failure modes;
- timelock and event for admin parameter changes;
- invariant tests at min/max boundary values.

## Residual risk

- 10% may still be economically unfair despite being within code bound;
- owner can change fee at an unfavorable time;
- frontend may display stale configuration;
- fee-on-transfer/rebase token behavior is separate;
- multiplication/division can introduce rounding;
- a compromised owner can select the maximum allowed fee repeatedly;
- configuration bounds do not fix reward accounting or access-control flaws.

## Detection

- boundary tests: `0`, `1`, `MAX`, `MAX+1`, `10_000`, `type(uint256).max`;
- fuzz setter and deposit amount;
- inspect all external input and derived values;
- verify units: wei, token decimals, basis points, blocks;
- negative constructor tests for zero addresses;
- mutation test by removing one `require` at a time;
- property:
  `0 < creditedAmount <= amount` for successful deposits;
- monitor configuration-change events.

## Mapping

- OWASP Smart Contract Top 10:2026: **SC05**;
- weakness family: improper/missing input validation;
- category boundary:
  - unauthorized caller changes fee → SC01;
  - authorized caller supplies out-of-range fee → SC05;
  - valid fee is accounted incorrectly against pool assets → SC02.

## Sources

- https://scs.owasp.org/sctop10/
- https://scs.owasp.org/sctop10/SC05-LackOfInputValidation/
- Existing `demo-single-level/SingleRewardPool.sol` input checks.

---

# 4. Tổng hợp attack–defense matrix

| Category | Attacker/control point | Broken invariant | Observable demo result | Primary defense |
|---|---|---|---|---|
| SC01 Access Control | Unauthorized EOA calls rate setter | Only authorized role changes critical configuration | Attacker changes `rewardPerBlock` | `onlyOwner`/RBAC, multisig, timelock |
| SC02 Business Logic | Authorized rate change at unsafe state-transition point | Each block uses its active epoch rate | Old blocks paid at new rate | `_updatePool()` before storing new rate |
| SC05 Input Validation | Authorized caller supplies unsafe `feeBps` | Fee and net deposit remain inside documented bounds | 100% fee produces zero user credit | bounds, derived-value checks, events/timelock |

# 5. Ánh xạ vào `SingleRewardPool` đã triển khai

| Existing element | Security interpretation |
|---|---|
| `onlyOwner` on configuration functions | SC01 defense already present |
| Missing `_updatePool()` before changing rate | Intentional SC02 bug |
| `require(amount > 0)` | SC05 amount defense |
| `require(newFeeBps <= 1_000)` | SC05 fee-bound defense |
| zero-address owner/token checks | SC05 address defense |
| `depositWithFeeBug` gross credit vs held balance | Separate SC02 accounting mismatch |
| `rewardDebt` | User accounting checkpoint, not an auditor/security actor |

# 6. Kết luận

Ba nhóm trả lời ba câu hỏi khác nhau:

```text
SC01 — Ai được phép gọi?
SC05 — Giá trị được truyền vào có hợp lệ?
SC02 — Khi actor và input hợp lệ, quy tắc/state transition có an toàn?
```

Một defense tốt phải khôi phục invariant, không chỉ làm một exploit test cụ thể
bị revert. Với `SingleRewardPool`, thứ tự nghiên cứu phù hợp là:

```text
permission boundary
→ input boundary
→ accounting/state-transition invariant
→ reproduction test
→ defended regression test
→ residual risk
```
