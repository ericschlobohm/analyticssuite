# Subagent Delegation Policy

This repository uses custom subagents in `.claude/agents/`.

When handling user requests in this workspace, default to delegating work to the best-fit subagent before doing implementation directly.

## Delegation Rules

1. If the user explicitly names a subagent, invoke that exact subagent.
2. If the request maps to a known domain, route it using the matrix below.
3. If a request has multiple phases, split work across subagents in sequence.
4. If the request is tiny or purely conversational, answer directly without spawning.
5. If routing is ambiguous, choose `Explore` first for quick scoping, then hand off.

## Routing Matrix

- `analytics-writer`:
  - Generate new SQL or Python analytics code
  - Draft new transformations, queries, or pipelines

- `analytics-reviewer`:
  - Review code quality, performance, maintainability, and security
  - Audit recent changes and provide prioritized findings

- `analytics-corrector`:
  - Fix failing tests, runtime errors, bad query behavior, and regressions
  - Apply minimal, validated code changes

- `analytics-documenter`:
  - Create or update docs for analytics code, dashboards, and usage
  - Produce markdown documentation and implementation notes

- `dashboard-builder`:
  - Create or revise dashboard configs, chart definitions, and layout structure
  - Translate business dashboard requirements into config artifacts

- `dashboard-tester`:
  - Validate dashboard configuration integrity and query readiness
  - Identify performance and release risks before shipping

- `dashboard-exporter`:
  - Implement or improve CSV/data export flows
  - Design filter, sort, and column-selection logic for exports

- `workspace-review`:
  - Review all current workspace files for quality, drift, and stale assets
  - Recommend prioritized updates and cleanup candidates

- `workspace-cleanup`:
  - Apply safe cleanup based on review findings
  - Remove confirmed redundant files and validate workspace integrity

- `workspace-git-interaction`:
  - Handle local git operations and remote sync workflows
  - Prepare branch, commit, and push flows safely

- `workspace-repo-sync`:
  - Keep local branches synchronized with remote safely
  - Report ahead/behind, pull outcomes, and sync blockers

- `workspace-release-maintenance`:
  - Maintain release notes/version metadata and readiness summaries
  - Prepare concise release checklists and blocker reports

- `workspace-maintenance-orchestrator`:
  - Coordinate end-to-end maintenance workflows across maintenance subagents
  - Produce consolidated phase-by-phase outcomes and final status

- `workspace-code-formatting`:
  - Apply file-type-aware formatting consistently across the workspace
  - Improve whitespace, casing consistency, and readability without behavior changes

- `workspace-docs-sync`:
  - Keep README and docs aligned with current implementation
  - Update stale guidance and examples

- `workspace-quality-gate`:
  - Run tests/lint checks and summarize pass/fail readiness
  - Identify top blockers before merge or release

- `workspace-dependency-hygiene`:
  - Audit dependency declarations vs real usage
  - Recommend minimal dependency cleanup actions

- `Explore`:
  - Read-only codebase discovery, file hunting, and rapid scoping
  - Use quick/medium/thorough depth depending on task complexity

## Execution Pattern

For implementation requests:
1. Delegate to the selected subagent.
2. Receive and apply its result.
3. Validate changes (tests/lint/checks when relevant).
4. Report concise outcome and file-level changes.

For review requests:
1. Delegate to `analytics-reviewer` or `dashboard-tester`.
2. Return findings first, ordered by severity.

## Examples

- "Write a Snowflake query for weekly conversion by channel" -> `analytics-writer`
- "Review this SQL for performance issues" -> `analytics-reviewer`
- "Fix failing dashboard tests" -> `analytics-corrector` then `dashboard-tester`
- "Create docs for export filters" -> `analytics-documenter`
- "Build a customer retention dashboard" -> `dashboard-builder`
- "Validate this dashboard JSON" -> `dashboard-tester`
- "Add CSV export with starts_with filter" -> `dashboard-exporter`
- "Review all workspace files and recommend updates" -> `workspace-review`
- "Clean up stale test artifacts and extra files" -> `workspace-cleanup`
- "Commit local changes and push to remote" -> `workspace-git-interaction`
- "Sync this workspace with origin and show ahead/behind" -> `workspace-repo-sync`
- "Prepare this repo for release with notes and readiness status" -> `workspace-release-maintenance`
- "Run complete repo maintenance end to end" -> `workspace-maintenance-orchestrator`
- "Format this repo for consistent style and readability" -> `workspace-code-formatting`
- "Bring docs in sync with current code" -> `workspace-docs-sync`
- "Run full quality checks before merge" -> `workspace-quality-gate`
- "Audit pyproject dependencies for unused packages" -> `workspace-dependency-hygiene`
