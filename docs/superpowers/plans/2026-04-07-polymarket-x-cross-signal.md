# Polymarket X Cross-Signal Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Polymarket-first, X-verified cross-signal monitor that only promotes topics after they clear both gates and can feed the existing sentiment workflow.

**Architecture:** Add a lightweight cross-signal layer ahead of the existing v2 pipeline. A Polymarket scout gathers candidate markets, a query builder converts them into X searches, an X verifier checks for multi-post spread, and an orchestrator emits a compact green-light report. Reuse `twscrape` for free X search and keep downstream sentiment work separate.

**Tech Stack:** Python 3.14, pytest, standard-library HTTP/JSON parsing, existing repository clients and dataclasses

---

### File Map

**Create:**
- `src/twitter_ops_agent/discovery/polymarket.py`
- `src/twitter_ops_agent/v2/agents/cross_signal_gate.py`
- `src/twitter_ops_agent/v2/cross_signal.py`
- `tests/test_polymarket_discovery.py`
- `tests/v2/test_cross_signal_gate.py`
- `tests/v2/test_cross_signal_orchestrator.py`

**Modify:**
- `src/twitter_ops_agent/domain/models.py`
- `src/twitter_ops_agent/config.py`
- `src/twitter_ops_agent/cli.py`
- `README.md`

### Task 1: Add Polymarket candidate discovery

**Files:**
- Create: `tests/test_polymarket_discovery.py`
- Create: `src/twitter_ops_agent/discovery/polymarket.py`

- [ ] **Step 1: Write the failing tests**

Add tests that verify:
- a Breaking-like HTML payload is parsed into candidate topics
- excluded categories such as price-target and sports markets are filtered out
- optional anomaly candidates can be normalized into the same result type

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_polymarket_discovery.py -v`
Expected: FAIL because the module and parser do not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement a small Polymarket discovery module with:
- candidate dataclass
- HTML extraction for market title, category, slug, volume, liquidity, and hint fields
- coarse include and exclude filters
- optional support for anomaly candidates through a normalized constructor

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_polymarket_discovery.py -v`
Expected: PASS

### Task 2: Add X query building and spread verification

**Files:**
- Create: `tests/v2/test_cross_signal_gate.py`
- Create: `src/twitter_ops_agent/v2/agents/cross_signal_gate.py`
- Modify: `src/twitter_ops_agent/domain/models.py`

- [ ] **Step 1: Write the failing tests**

Add tests that verify:
- a Polymarket market title becomes 1-3 useful X search queries
- a topic passes when it has at least 3 independent posts from multiple accounts
- the verifier returns the top 5 posts ranked by spread momentum
- a topic fails when it only has one post or one-account noise

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/v2/test_cross_signal_gate.py -v`
Expected: FAIL because the verifier and payload models do not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement:
- normalized query builder
- green-light payload model
- verifier logic using counts for independent posts, distinct accounts, and engagement-weighted ranking

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/v2/test_cross_signal_gate.py -v`
Expected: PASS

### Task 3: Add orchestration layer and CLI entrypoint

**Files:**
- Create: `tests/v2/test_cross_signal_orchestrator.py`
- Create: `src/twitter_ops_agent/v2/cross_signal.py`
- Modify: `src/twitter_ops_agent/config.py`
- Modify: `src/twitter_ops_agent/cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests that verify:
- the orchestrator polls candidates, verifies them, and emits only passed topics
- failed topics stay quiet
- the CLI can run a dedicated cross-signal command and print JSON output

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/v2/test_cross_signal_orchestrator.py tests/test_cli.py -v`
Expected: FAIL because the orchestrator wiring and CLI command do not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement:
- config defaults for cadence and thresholds
- orchestrator that combines scout and verifier
- CLI subcommand that runs the cross-signal monitor and returns a compact JSON report

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/v2/test_cross_signal_orchestrator.py tests/test_cli.py -v`
Expected: PASS

### Task 4: Document and integrate with existing workflow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the failing doc expectation**

Identify the user-facing README sections that need updates:
- what the new cross-signal monitor does
- why it is not a trading-signal engine
- how to run the new command

- [ ] **Step 2: Update documentation**

Add a concise section that explains:
- Gate 1: Polymarket candidate signal
- Gate 2: X spread verification
- green-light output

- [ ] **Step 3: Run focused tests**

Run: `python3 -m pytest tests/test_polymarket_discovery.py tests/v2/test_cross_signal_gate.py tests/v2/test_cross_signal_orchestrator.py tests/test_cli.py -v`
Expected: PASS

### Task 5: Final verification

**Files:**
- Modify: tracked files from Tasks 1-4

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest -v`
Expected: PASS with no new failures

- [ ] **Step 2: Review the diff**

Run: `git diff --stat`
Expected: only the planned feature files and docs changed

- [ ] **Step 3: Commit**

```bash
git add README.md src/twitter_ops_agent/config.py src/twitter_ops_agent/cli.py src/twitter_ops_agent/discovery/polymarket.py src/twitter_ops_agent/domain/models.py src/twitter_ops_agent/v2/agents/cross_signal_gate.py src/twitter_ops_agent/v2/cross_signal.py tests/test_polymarket_discovery.py tests/v2/test_cross_signal_gate.py tests/v2/test_cross_signal_orchestrator.py docs/superpowers/plans/2026-04-07-polymarket-x-cross-signal.md
git commit -m "feat: add polymarket x cross-signal monitor"
```
