# OWASP Top 3 Applicable to `SingleRewardPool`

A local Hardhat companion demo for the existing `demo-single-level` project.
It studies three OWASP Smart Contract Top 10:2026 categories that map naturally
to the reward-pool domain:

1. **SC01 — Access Control Vulnerabilities**
2. **SC02 — Business Logic Vulnerabilities**
3. **SC05 — Lack of Input Validation**

The package deliberately contains one vulnerable contract and one contract that
demonstrates defenses for only those three categories.

> Educational use only. Do not deploy either contract with real funds. The
> defended version is not claimed to be production-ready or secure against all
> smart-contract vulnerability classes.

## Why these three

`SingleRewardPool` already has privileged configuration, block-based reward
accounting, deposit amounts, fee basis points, and token/address parameters.
Therefore SC01, SC02, and SC05 can be demonstrated without inventing an oracle,
AMM, lending market, or flash-loan subsystem that does not belong to the
original case study.

SC03 Price Oracle Manipulation and SC04 Flash Loan–Facilitated Attacks should be
implemented later in a separate `OracleLendingPool` lab.

## Project structure

```text
.
├── contracts/
│   ├── MockToken.sol
│   ├── OWASPTop3VulnerableRewardPool.sol
│   └── OWASPTop3DefendedRewardPool.sol
├── test/
│   └── OWASPTop3RewardPool.js
├── research/
│   └── OWASP_TOP3_SINGLE_REWARD_POOL.md
├── DEMO_GUIDE.md
├── hardhat.config.js
└── package.json
```

## Run

```bash
npm install
npm test
```

## Deploy local and use MetaMask

Open two terminals in this directory:

```bash
npm install
npm run node
```

Import the first three private keys printed by `hardhat node` into MetaMask.
Add this network to MetaMask:

```text
Network name: Hardhat Local
RPC URL:      http://127.0.0.1:8545
Chain ID:     31337
Currency:     ETH
```

In a second terminal run:

```bash
npm run deploy:local
python -m http.server 8080
```

Open `http://localhost:8080/frontend/`. The page reads the generated
`frontend/deployment.json`, asks MetaMask to sign every state-changing call,
waits for its receipt, and records the transaction hash, block, category and
label in browser local storage. Use the first imported account as owner and a
different account as Alice/attacker when demonstrating SC01.

The three visual demonstrations are:

- SC01: attacker changes the vulnerable rate; the defended call reverts for a
  non-owner.
- SC02: approve → deposit 100 → mine 10 blocks → change rate → mine 5 blocks →
  claim, shown side by side for vulnerable and defended pools.
- SC05: vulnerable 10,000 BPS accepts a 100% fee; defended rejects it and
  demonstrates 1,000 BPS as a 10% fee.

Expected test groups:

```text
SC01 - Access Control
  ✓ vulnerable pool lets an attacker change the reward rate
  ✓ defended pool rejects an unauthorized configuration change

SC02 - Business Logic
  ✓ vulnerable pool applies the new rate to old blocks
  ✓ defended pool checkpoints the old rate before changing it

SC05 - Lack of Input Validation
  ✓ vulnerable pool accepts a 100% fee and confiscates the deposit
  ✓ defended pool rejects an out-of-range fee
  ✓ defended pool credits only the net amount for a valid fee
```

## Relationship to the existing demo

The existing `SingleRewardPool` remains the primary case study:

- Its `onlyOwner` checks are examples of an SC01 defense.
- Its intentional retroactive rate-change bug is the direct SC02 case.
- Its positive-amount, fee-bound, non-zero owner, and constructor checks are
  examples of SC05 defenses.
- Its `depositWithFeeBug` is a separate accounting/business-logic case and is
  not treated as pure input validation in this package.

## Sources

- OWASP Smart Contract Top 10:2026: https://scs.owasp.org/sctop10/
- SC01 Access Control: https://scs.owasp.org/sctop10/SC01-AccessControlVulnerabilities/
- SC02 Business Logic: https://scs.owasp.org/sctop10/SC02-BusinessLogicVulnerabilities/
- SC05 Input Validation: https://scs.owasp.org/sctop10/SC05-LackOfInputValidation/
- OpenZeppelin Access Control: https://docs.openzeppelin.com/contracts/5.x/access-control
