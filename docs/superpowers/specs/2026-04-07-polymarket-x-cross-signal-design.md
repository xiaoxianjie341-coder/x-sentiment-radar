# Polymarket + X Cross-Signal Monitor Design

Date: 2026-04-07
Status: Approved for implementation planning

## Summary

This project should evolve from a pure sentiment analyzer into a cross-signal monitor for public topics.

The target behavior is:

1. Use Polymarket as the first gate to find topics that may have entered a real-world event cycle.
2. Use X as the second gate to confirm whether the topic is spreading as a multi-post public discussion, not just a single viral post.
3. Only when both gates pass, produce a compact research card and then hand the topic into the existing sentiment workflow.

This is not a trading signal system. It is a social hot-topic cross-verification system.

## Problem

The current system is good at extracting crowd reaction after a topic is already selected, but it does not yet have a dedicated front-end gate for:

- detecting external event signals before they become obvious in the feed
- filtering out topics that move in capital markets but never become public discussion
- summarizing the actual spread narrative on X before deeper sentiment analysis starts

If we only scan broad X trends, we miss a useful external signal.
If we only scan Polymarket movers, we pull in too much market-only noise.
The product needs both.

## Goals

- Build a two-gate monitor that mirrors the approved business logic.
- Keep the first gate light and practical by using Polymarket candidate signals instead of building a heavy market analytics system.
- Keep the second gate grounded in real X spread patterns, not single-post virality.
- Reuse the existing repository as much as possible, especially the current X clients and downstream sentiment pipeline.

## Non-Goals

- Do not build a full Polymarket trading engine.
- Do not optimize for private alpha or market-making use cases.
- Do not require the paid X API.
- Do not model a complete retweet graph in v1.
- Do not replace the current downstream sentiment summarization and publishing pipeline.

## User-Facing Outcome

When a topic passes both gates, the system should emit a green-light topic card with:

- topic name
- why it is worth attention now
- Polymarket signal source
- top 5 X posts by spread momentum
- a short angle summary describing the narrative currently spreading

If a topic does not pass both gates, the system stays quiet.

## Business Logic

### Gate 1: Polymarket Candidate Signal

The first gate should not scan all markets with a hard-only `6h > 15%` rule.
That approach behaves more like a market anomaly detector and creates too much noise.

Instead, the system should build a candidate pool from:

- Polymarket Breaking candidates
- additional obvious anomaly candidates when useful

The first gate is intentionally broad, but it should still apply a simple business filter so the candidate pool is biased toward public-interest topics rather than pure market churn.

Recommended include bias:

- politics
- geopolitics
- tech
- AI
- economy
- culture
- brand or public-event topics

Recommended exclude bias:

- crypto price target markets
- airdrop-only markets
- sports and esports markets
- low-context recurring markets that do not map cleanly to public news discussion

The output of Gate 1 is a normalized topic candidate, not a final alert.

### Gate 2: X Spread Verification

The second gate checks whether the topic has become a real discussion on X.

This gate is intentionally not based on one viral post.
It should validate that:

- at least 3 independent posts discuss the topic
- those posts come from multiple accounts
- at least 1-2 posts show meaningful spread
- the discussion has enough density to look like a developing public narrative

The approved strictness for v1 is the loose version:

- if a topic has formed a visible multi-post discussion, it may pass
- it does not need a fully proven retweet cascade before alerting

The output of Gate 2 is:

- pass or fail
- top 5 representative posts ranked by spread momentum
- a one-line summary of the angle currently working

## End-to-End Flow

1. Poll Polymarket on a recurring schedule such as every 30 minutes.
2. Build a candidate pool from Breaking and optional anomaly signals.
3. Normalize each candidate into a topic label plus 1-3 X search queries.
4. Use a free X-capable client to search for that topic on X.
5. Group and rank matching posts to determine whether the topic has become a multi-post discussion.
6. If Gate 2 fails, do nothing.
7. If Gate 2 passes, create a green-light topic card.
8. Hand the passed topic into the existing hydration, crowd-sense, and publishing pipeline for deeper sentiment analysis and note output.

## Architecture

The design should add a lightweight cross-signal layer in front of the current v2 workflow, rather than replacing the current workflow.

### New Responsibilities

#### Polymarket Signal Scout

Responsible for:

- fetching Breaking candidates
- optionally fetching additional anomaly candidates
- normalizing market titles and metadata
- applying coarse business filtering

This layer only finds candidates.
It does not decide whether a topic is already spreading on X.

#### Topic Query Builder

Responsible for:

- converting a Polymarket market title into 1-3 practical X search queries
- stripping decision-market phrasing that harms search quality
- preserving core entities, brands, people, and event terms

This layer exists because market wording and social wording are often different.

#### X Virality Verifier

Responsible for:

- searching X for each topic query
- deduplicating near-identical results
- measuring whether the topic has become a multi-post discussion
- returning the top 5 posts by spread momentum
- summarizing the currently performing angle

This layer is the true second gate.

#### Cross-Signal Gate

Responsible for:

- combining Gate 1 and Gate 2
- deciding whether a topic earns a green light
- producing a stable handoff payload for the existing pipeline

## Integration With Current Codebase

The repository already has useful pieces that should be reused:

- `XHunt` as an existing trend-discovery reference
- `twscrape` support for free X search
- browser-session support for detail and reply capture
- the current downstream `hydration -> priority_gate -> crowd_sense -> publisher` flow

Important current constraint:

- browser-session currently does not implement search, so it cannot be the primary Gate 2 search client in v1

Recommended integration shape:

- use a new Polymarket-based scout before the current downstream stages
- use `twscrape` as the default topic-search verifier
- keep browser-session available for deeper fetch and reply capture after a topic is already verified
- feed verified topics into the existing sentiment pipeline instead of building a second output system

## Verification Model For X

The verifier should rank by topic spread, not just raw likes.

The exact scoring can change during implementation, but the model should consider:

- independent post count
- distinct account count
- likes
- retweets
- replies
- quotes
- recency
- whether multiple posts express the same emerging angle

The final top 5 should be the posts that best represent current spread momentum for the topic.

## Output Contract

For a passed topic, the handoff object should contain at least:

- normalized topic label
- source market title and source URL
- reason it entered the candidate pool
- verification pass result
- top 5 representative X posts
- one-line angle summary
- raw verification stats useful for downstream ranking

This output should be compact enough to support:

- alerting
- downstream sentiment analysis
- future ranking or suppression rules

## Error Handling

- If Polymarket is unavailable, skip the run and log a recoverable failure.
- If X search is unavailable, do not promote the topic to a green light.
- If the query builder produces noisy searches, the topic should fail closed rather than force a bad alert.
- If the same topic appears repeatedly across runs, reuse lightweight state to suppress duplicate alerts.
- If one query is noisy but another is clean, keep the query set small and practical rather than trying to search everything.

## Testing Strategy

Implementation should cover at least:

- parser tests for Polymarket candidate extraction
- query-builder tests for market-title normalization
- X verification tests for pass and fail scenarios
- ranking tests for top-5 representative post selection
- orchestration tests covering both-gates-pass and one-gate-fails paths

The most important quality bar is not raw recall.
It is whether the system avoids promoting market-only noise while still catching public-interest topics early.

## Rollout Recommendation

Use a staged rollout:

1. Build the cross-signal monitor and green-light output first.
2. Validate whether the selected topics match operator judgment.
3. After validation, wire the passed topics into the existing full note-writing workflow by default.

This keeps early iteration safe while preserving the final direction.

## Implementation Direction

The implementation plan should optimize for:

- minimal moving parts
- maximum reuse of current repository capabilities
- free or nearly free external dependencies
- quiet failure when signals are weak
- alert quality over alert volume

In short:

Polymarket should answer "what might matter now?"
X should answer "is it actually spreading as a public discussion?"
The existing sentiment pipeline should answer "what are people feeling and how should we write about it?"
