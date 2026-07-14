# Understanding the metrics in machine learning

These metrics are useful when a model gives a positive/negative decision. In the GPTScan paper, the positive decision is: "this smart contract code has a vulnerability." The negative decision is: "this code is safe for this vulnerability type."

## Precision

Precision answers this question:

> Among all warnings reported by the tool, how many warnings are actually correct?

Formula:

```text
Precision = TP / (TP + FP)
```

Where:

- `TP` means true positive: the tool reports a vulnerability, and the vulnerability is real.
- `FP` means false positive: the tool reports a vulnerability, but the code is not actually vulnerable.

Precision is important for security tools because too many false alarms waste auditor time. If a tool has low precision, users may stop trusting its reports.

In GPTScan, precision is especially important on the Top200 dataset, because Top200 contains popular and well-audited contracts. The main question there is not "can GPTScan find many bugs?", but "does GPTScan report too many false alarms on code that is probably safe?"

## Recall

Recall answers this question:

> Among all real vulnerabilities, how many did the tool successfully find?

Formula:

```text
Recall = TP / (TP + FN)
```

Where:

- `FN` means false negative: the code has a real vulnerability, but the tool misses it.

Recall is important because missed bugs are dangerous. In smart contracts, one missed logic vulnerability can lead to financial loss after deployment.

In GPTScan, recall is important on Web3Bugs and DefiHacks because those datasets contain known vulnerability cases. The tool should be able to recover as many of those known bugs as possible.

## F1-score

F1-score balances precision and recall into one number.

Formula:

```text
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

F1 is useful when we do not want to look at precision or recall alone. For example:

- High precision but low recall means the tool is careful, but misses many real bugs.
- High recall but low precision means the tool finds many real bugs, but also reports many false alarms.
- A better F1-score means the tool has a better balance between both sides.

For GPTScan on Web3Bugs, the result in the available dataset is:

```text
TP = 40
FP = 30
FN = 8
Precision = 40 / (40 + 30) = 57.14%
Recall = 40 / (40 + 8) = 83.33%
F1 = 67.8%
```

My interpretation: GPTScan has strong recall on Web3Bugs, so it can find many real logic vulnerabilities. The weaker point is precision, because it still produces a noticeable number of false positives on large project-level codebases.

# Five platforms for writing smart contracts

The five platforms below are useful for comparison because they represent different ecosystems, programming languages, and security tradeoffs.

| Platform | Main smart contract language | Strengths | Weaknesses | Fit for GPTScan-related work |
| --- | --- | --- | --- | --- |
| Ethereum | Solidity, Vyper | Largest ecosystem, mature tooling, many audits, many real-world DeFi cases | Gas can be expensive, contracts are public targets, complex DeFi logic can be hard to audit | Best fit. GPTScan targets Solidity/EVM projects, and its datasets are Ethereum-compatible |
| BNB Chain | Solidity | EVM-compatible, cheaper transactions than Ethereum, many deployed contracts | Security quality varies a lot across projects, many forks and duplicated code | Good secondary fit because Solidity/EVM tooling can usually be reused |
| Polygon | Solidity | EVM-compatible, low fees, common for DeFi and NFT applications | Cross-chain/bridge assumptions can add extra security risk | Good secondary fit because it stays close to Ethereum development patterns |
| Solana | Rust, C, C++ | High throughput, different execution model, strong performance | Harder learning curve, different bug classes from EVM, not directly compatible with Solidity tools | Weak fit for GPTScan because GPTScan is not designed for Rust/Solana programs |
| Cardano | Plutus, Haskell, Aiken | Strong formal-methods culture, UTXO-based model, careful design | Smaller developer ecosystem than Ethereum, steeper learning curve | Weak fit for GPTScan because the contract model and languages are different |

## Which platform should I choose?

For this research direction, I should choose Ethereum/Solidity as the main platform.

The reason is practical: GPTScan is built around Solidity smart contracts and program analysis for EVM-style projects. The paper datasets also focus on Ethereum-compatible smart contracts. If I choose Solana or Cardano, the research topic changes because the language, execution model, and vulnerability patterns are different.

BNB Chain and Polygon are still useful as secondary examples because they are EVM-compatible. However, Ethereum is the cleanest choice for explaining GPTScan, reproducing results, and connecting the work to existing smart contract security research.

# Five tools for finding smart contract bugs

These tools are not identical. Some are static analyzers, some use symbolic execution, and GPTScan uses a hybrid design that combines GPT with program analysis.

| Tool | Main technique | What it is good at | Main limitation | Relationship to GPTScan |
| --- | --- | --- | --- | --- |
| GPTScan | GPT-based semantic reasoning + static confirmation | Logic vulnerabilities that need business-level understanding | Can still produce false positives when protocol context is large or incomplete | Main paper/tool in this research |
| Slither | Static analysis | Fast checks for common Solidity issues such as reentrancy patterns, unchecked calls, dangerous modifiers, and code smells | Rule-based analysis struggles with deep business logic | Useful baseline because it represents traditional static analysis |
| Mythril | Symbolic execution | Finding execution paths that lead to known vulnerability patterns | Can be slow and may struggle with large projects or complex path explosion | Useful comparison for path-based bug discovery |
| Oyente | Symbolic execution | Early Ethereum vulnerability detection, historically important | Older tool, less suitable for modern complex projects | Useful as background for how smart contract analysis evolved |
| Manticore | Symbolic execution and program exploration | Deeper path exploration and custom analysis | Requires expertise and can be expensive to run on large projects | Useful for comparing manual/security-research style analysis |

## Which bug detection tool should I choose?

For the paper use case, GPTScan should be the main tool because the research question is specifically about detecting smart contract logic vulnerabilities with GPT plus program analysis.

Slither is still important because it gives a clear contrast. Slither can catch many syntactic or pattern-based issues quickly, but logic vulnerabilities often require understanding protocol intent. This is the gap GPTScan tries to address.

The best comparison argument is:

> Traditional tools are strong when a vulnerability has a clear code pattern. GPTScan is designed for cases where the vulnerability depends on semantic meaning, such as missing business checks, wrong accounting assumptions, or broken protocol invariants.

# Basic ML keyword: LazyPredict

LazyPredict is an open-source Python library for quick baseline modeling. The idea is simple: instead of manually writing and tuning many machine learning models one by one, LazyPredict runs a group of common models and gives an initial comparison table.

It is not meant to produce the final best model. It is mainly useful at the beginning of a project.

## What LazyPredict is useful for

- Quickly testing many ML algorithms on the same dataset.
- Establishing a baseline before deeper model tuning.
- Helping beginners see which model families may fit the data.
- Saving time during early experiments.
- Creating a first comparison table for research notes.

## What LazyPredict is not good for

- It does not replace careful feature engineering.
- It does not explain deeply why a model works.
- It does not guarantee the best final result.
- It can hide important modeling decisions if the user only trusts the output table.
- It is not directly related to smart contract analysis.

## How to connect LazyPredict to GPTScan

The connection is indirect. LazyPredict is not used by GPTScan. However, the baseline idea is useful.

In ML, LazyPredict helps answer:

> Before doing deep tuning, what is a reasonable baseline?

In GPTScan, the paper also needs baselines:

> Before claiming GPTScan is useful, how does it compare with existing smart contract analysis tools and datasets?

So I can mention LazyPredict as a general lesson about research methodology: start with baselines, then explain why the proposed method improves or differs from them.

# Lazy learners and LLM prompting

Classic lazy learning means the model does not build a strong general model during training. Instead, it stores examples and uses them when a new prediction is needed. A common example is K-nearest neighbors.

Few-shot prompting in LLMs looks similar, but it is not exactly the same.

When I put examples into a system prompt or user prompt, the LLM does not train itself again. It uses those examples as context during inference. This is usually called in-context learning, not classic lazy learning.

The safer explanation is:

> Few-shot prompting is similar to lazy learning because examples are provided at prediction time. But technically, the LLM is not retrained on those examples. The examples guide the model's behavior inside the current context window.

This distinction matters because GPTScan uses GPT for semantic matching, but it does not mean GPTScan trains a new model for each smart contract project.

# GPTScan: datasets used in the paper

GPTScan evaluates smart contract logic vulnerability detection with three datasets:

1. Web3Bugs
2. DefiHacks
3. Top200

These datasets are not interchangeable. Each one tests a different question.

| Dataset | Size in the paper/workspace notes | Main purpose | Why GPTScan uses it | What it tests |
| --- | ---: | --- | --- | --- |
| Web3Bugs | 72 projects, 232 rule cases | Detect known logic vulnerabilities in large audited projects | It contains realistic project-level bugs from smart contract audit contests | Whether GPTScan can find logic vulnerabilities in complex multi-contract projects |
| DefiHacks | 13 hack cases, 34 rule cases | Detect vulnerabilities connected to real DeFi hacks | It checks whether GPTScan can identify issues that were serious enough to lead to exploits | Whether GPTScan can detect exploit-relevant vulnerabilities |
| Top200 | 303 projects | Stress-test false positives on popular contracts | These contracts are widely used and assumed to have no notable vulnerabilities | Whether GPTScan reports too many false alarms on mature contracts |

## Difference between the datasets

Web3Bugs is the hardest dataset for project-level reasoning. It contains large projects where the bug may depend on several contracts, state variables, and business rules. This is why GPTScan can have good recall but weaker precision on Web3Bugs.

DefiHacks is smaller but more security-focused. The cases are connected to real attacks, so it is useful for asking whether GPTScan can detect vulnerabilities with practical exploit impact.

Top200 is different from the other two. It is mainly a false-positive benchmark. The goal is not to find many bugs, because the contracts are popular and assumed to be well-audited. The goal is to check whether GPTScan reports suspicious issues too often.

## GPTScan results connected to the metrics

From the available notes and dataset files:

| Dataset | TP | TN | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Web3Bugs | 40 | 154 | 30 | 8 | 57.14% | 83.33% | 67.8% |
| DefiHacks | 10 | 19 | 1 | 4 | 90.91% | 71.43% | 80.0% |

The meaning is different for each dataset.

For Web3Bugs, GPTScan finds many true bugs, but false positives are still a problem. This supports the idea that large protocol-level logic is difficult to confirm.

For DefiHacks, precision is higher, but the dataset is much smaller. I should not overclaim from this result because 13 hack cases are not enough to represent all DeFi vulnerabilities.

For Top200, the important metric is false positive behavior. Since these projects are assumed to be well-audited, too many alerts would show that GPTScan over-reports on normal code.

# GPTScan paper use case

The best use case for GPTScan is not simple pattern detection. Tools like Slither already do well when a bug has a clear syntactic pattern.

GPTScan is more interesting when the vulnerability requires semantic reasoning, for example:

- A reward function misses an eligibility check.
- A withdrawal function updates accounting in a way that violates protocol intent.
- A permission check exists, but it protects the wrong role or wrong state transition.
- A token transfer is locally valid, but breaks a higher-level accounting invariant.
- A protocol assumes one user can claim only once, but the implementation does not enforce that property.

This is why GPTScan combines two parts:

1. GPT identifies code that semantically matches a vulnerability scenario.
2. Static analysis confirms whether the key variables, statements, and properties actually support the warning.

The important argument is:

> GPTScan is valuable because it is a hybrid pipeline. GPT helps understand semantic vulnerability scenarios, while static analysis reduces unsupported or noisy reports.

This also explains the Web3Bugs result. GPTScan reaches high recall because GPT can recognize many suspicious semantic patterns. But precision is lower because large projects contain many functions that look dangerous locally while being protected by context elsewhere in the protocol.

# Final research direction

For the next step, I should focus on Ethereum/Solidity, GPTScan, and the three GPTScan datasets. That gives the work a clear scope:

- Platform: Ethereum/Solidity, with BNB Chain and Polygon as secondary EVM examples.
- Main tool: GPTScan.
- Baseline tools: Slither, Mythril, Oyente, and Manticore.
- Main dataset discussion: Web3Bugs, DefiHacks, and Top200.
- Main research point: GPTScan is useful for smart contract logic vulnerability detection, but false positives remain difficult on large project-level benchmarks.

This scope is better than trying to cover every blockchain or every security tool. It stays close to the GPTScan paper and gives enough evidence to explain the results carefully.
