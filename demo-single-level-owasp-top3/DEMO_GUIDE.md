# Demo guide — attack, invariant, defense

## Goal

Show that security is not just “the transaction reverted” or “the test passed.”
For every case, present the same five-step sequence:

```text
Protected asset
→ Expected invariant
→ Attack transaction sequence
→ Observable broken state
→ Defense that restores the invariant
```

## Suggested 8–10 minute presentation

### 1. Context — 1 minute

`SingleRewardPool` behaves like a block-based savings/reward pool:

```text
Alice approves DST
→ deposits DST
→ reward accrues in DRW per block
→ withdraw returns principal DST
→ claim transfers reward DRW
```

`rewardDebt` is an accounting checkpoint, not an auditor. It prevents old reward
from being counted repeatedly when user balances change.

### 2. SC01 Access Control — 2 minutes

Run:

```bash
npx hardhat test --grep "SC01"
```

Explain:

- Vulnerable path: `attacker` changes `rewardPerBlock` to an arbitrary value.
- Broken invariant: only the authorized administrator may modify economic
  configuration.
- Defense: `onlyOwner`/role check, plus stronger production governance such as
  multisig and timelock.

### 3. SC02 Business Logic — 3 minutes

Run:

```bash
npx hardhat test --grep "SC02"
```

Sequence:

```text
Alice deposits 100 DST at rate 1 DRW/block
→ 10 blocks pass
→ owner changes rate to 10 DRW/block
→ 5 more blocks pass
→ Alice claims
```

Vulnerable behavior:

```text
Old blocks are retrospectively valued using the new rate.
Paid reward > 100 DRW in the test.
```

Defended behavior:

```text
_updatePool() checkpoints the old epoch
before rewardPerBlock is changed.
Paid reward remains between 50 and 100 DRW
for the deterministic local sequence.
```

The exact amount includes transaction-mining blocks; the security assertion is
about the old-rate/new-rate boundary, not a hand-picked exact total.

### 4. SC05 Input Validation — 2 minutes

Run:

```bash
npx hardhat test --grep "SC05"
```

Vulnerable path:

```text
Owner sets feeBps = 10_000
→ Alice deposits 100 DST
→ 100 DST is charged as fee
→ Alice receives zero deposit credit
```

The caller is authorized, so this is not an SC01 bypass. The failure is that the
contract accepts an economically unsafe parameter.

Defense:

```text
feeBps <= 1_000
amount > 0
net credited amount > 0
non-zero token addresses
```

### 5. Conclusion — 1–2 minutes

Use this distinction:

```text
SC01: Is the actor allowed?
SC05: Is the supplied value valid?
SC02: Even with a valid actor and value, are the rules/state transitions safe?
```

## Commands

```bash
npm install
npm run compile
npm test
npm test -- --grep "SC01"
npm test -- --grep "SC02"
npm test -- --grep "SC05"
```

## What not to claim

- The defended contract is not generally production-ready.
- `onlyOwner` does not protect against a compromised or malicious owner.
- Fee bounds do not prove the whole economic design is fair.
- Unit tests do not replace fuzzing, invariant testing, static analysis, and
  manual review.
- Flash loans and oracle manipulation are not demonstrated because the original
  reward pool has no oracle-dependent market.
