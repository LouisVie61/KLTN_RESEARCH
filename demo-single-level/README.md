# Single-level Reward Pool — Local MetaMask demo

Educational-only local Hardhat demo. It accepts a mock staking token, returns it on withdrawal, and transfers a mock reward token on `claim`. **Do not use this code with real funds.**

## Intentional semantic bug

The source deliberately contains two runnable semantic bugs:

- `BUG-1` — `setRewardPerBlock` changes the rate without first checkpointing accumulated rewards. A later `claim` prices old blocks at the new rate.
- `BUG-2` — `depositWithFeeBug` credits the full deposit but sends a configured fee out of the pool, breaking the relationship between recorded deposits and tokens actually held.

Both are covered by tests and are strictly for analysis demonstrations.

## Chạy trực tiếp với MetaMask — không `.env`, không Remix

```bash
npm install
npm run node
```

`npm run node` tạo 10 địa chỉ giả cùng private key và 10,000 ETH local mỗi địa chỉ. Import private key của hai địa chỉ đầu tiên vào MetaMask.

Trong MetaMask thêm mạng:

- Network name: `Hardhat Local`
- RPC URL: `http://127.0.0.1:8545`
- Chain ID: `31337`
- Currency symbol: `ETH`

Trong terminal thứ hai:

```bash
npm run deploy:local
python -m http.server 8080
```

Mở `http://localhost:8080/frontend/`, kết nối MetaMask rồi chuyển DST giữa hai ví hoặc gọi approve/deposit/withdraw/claim. Mọi giao dịch xuất hiện trong popup MetaMask. Script cấp 1,000 DST cho hai ví đầu tiên và 10,000 DRW cho pool.
