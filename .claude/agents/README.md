# Analytics Suite Subagents

This directory defines project-level Claude subagents for the existing analytics agent set.

Each subagent uses YAML frontmatter plus a focused system prompt body, based on:
- `WriterAgent`
- `ReviewerAgent`
- `CorrectorAgent`
- `DocumenterAgent`
- `DashboardBuilderAgent`
- `DashboardTesterAgent`
- `DashboardExportAgent`

These are discovered automatically by Claude Code from `.claude/agents/`.

## Subagents

- `analytics-writer`
- `analytics-reviewer`
- `analytics-corrector`
- `analytics-documenter`
- `dashboard-builder`
- `dashboard-tester`
- `dashboard-exporter`
- `workspace-review`
- `workspace-cleanup`
- `workspace-git-interaction`
- `workspace-repo-sync`
- `workspace-release-maintenance`
- `workspace-maintenance-orchestrator`
- `workspace-code-formatting`
- `workspace-docs-sync`
- `workspace-quality-gate`
- `workspace-dependency-hygiene`

## Usage

Natural language delegation examples:
- Use the analytics-writer subagent to draft a Snowflake SQL query for daily revenue by region.
- Use the dashboard-tester subagent to validate `example_sales_dashboard.json` and report risks.

Explicit @-mention examples:
- `@"analytics-reviewer (agent)" review the query in src/...`
- `@"dashboard-exporter (agent)" suggest export filters for chart_1`
- `@"workspace-review (agent)" audit this repository and recommend improvements`
- `@"workspace-cleanup (agent)" remove low-risk stale files after the review`
- `@"workspace-code-formatting (agent)" format Python and markdown files for consistency`
- `@"workspace-repo-sync (agent)" fetch and pull latest from origin and summarize changes`
- `@"workspace-release-maintenance (agent)" prepare release notes and readiness summary`
- `@"workspace-maintenance-orchestrator (agent)" run a full maintenance cycle`

## Layered architecture

1. **Wrappers (manage workflows)** - start here:
   - `analytics-workflow-manager`: classifies requests, routes to creators, runs gates, bounded fix loop (max 3), commits on a branch.
   - `dashboard-workflow-manager`: dashboard + export build and validation.
   - `analytics-code-quality-manager`: parallel review/accuracy pass over existing code, optional fixes.
   - `workspace-maintenance-orchestrator`: repo maintenance cycle.
2. **Creation specialists**: `snowflake-sql-writer`, `python-analytics-writer`, `dashboard-config-builder`, `export-filter-designer`, `analytics-doc-writer` (legacy generalists `analytics-writer`, `dashboard-builder`, `dashboard-exporter`, `analytics-documenter` remain as fallbacks).
3. **Accuracy checkers (read-only)**: `sql-accuracy-checker`, `analytics-security-reviewer`, `analytics-performance-reviewer`, `analytics-reviewer`.
4. **Validators**: `dashboard-config-validator`, `export-validator`, `test-validator`, `dashboard-tester`, `workspace-quality-gate`.
5. **Correction**: `analytics-corrector`.

Checkers and validators return a PASS/FAIL verdict plus findings; wrappers loop failures back to the creator.

Example: `@"analytics-workflow-manager (agent)" add a weekly conversion by channel query and export it as CSV`
