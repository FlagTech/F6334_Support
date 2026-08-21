---
name: project-risk-dashboard
description: Analyze project meeting notes, plans, schedules, and spreadsheets to identify traceable risks, dependencies, open decisions, and schedule conflicts, then create a standalone interactive HTML risk dashboard. Use when Codex needs a source-backed project risk assessment or launch-readiness dashboard.
---

# Project Risk Dashboard

Create a concise, evidence-backed assessment for project or launch materials. Produce a browser-openable HTML dashboard in Traditional Chinese unless the user requests another language.

## Workflow

1. Inventory every supplied source. Mark templates, previews, and generated copies as non-authoritative unless they add project-specific facts.
2. Extract commitments, dates, owners, dependencies, gates, thresholds, unknowns, and explicit concerns. Give each evidence item a stable source key such as `S1???` or `S2:A14`.
3. Read [risk-model.md](references/risk-model.md) before scoring. Score only from source evidence; label recommended deadlines and inferred dependencies as analysis rather than source facts.
4. Create a risk register with ID, risk, impact, likelihood, score, priority, affected domains, owner, mitigation, due date, status, and evidence keys. Keep an unassigned primary owner as `?????`; name a coordinator only when the sources identify one.
5. Create a decision register for unresolved choices. Include the missing information, decision owner, source deadline or labelled recommended deadline, and downstream effect.
6. Trace the critical path from launch or delivery milestones backwards. Flag date conflicts, missing owners, missing dates, and gates with insufficient buffer.
7. Read [source-traceability.md](references/source-traceability.md) and build one self-contained HTML file. Start from [risk-dashboard-template.html](assets/risk-dashboard-template.html) when a reusable shell helps.

## Required Dashboard Behaviour

- Embed all assessment data, styles, and scripts; do not fetch network resources.
- Show overview metrics, a clickable 5?5 matrix, a dated timeline, a filterable risk table, decisions, and source evidence.
- Filter risks by priority, domain, owner, and status. Let matrix selection refine the same table.
- Visually flag risks touching go-live, security, legal, data correctness, or customer experience when their score is 12 or above.
- State the assessment date and timezone. Calculate overdue and near-term labels from that stated date, not the browser clock.
- Ensure every risk, decision, and timeline item has at least one evidence key and evidence summary.

## Validation

- Check that `impact ? likelihood = score` and that the score maps to the required priority.
- Check all source keys resolve to a listed source and every displayed date has an explicit source or `????` label.
- Open the HTML with no network connection. Test filters, matrix selection, evidence disclosure, keyboard navigation, and a narrow viewport.
