---
name: create-company-progress-deck
description: Create concise company weekly or monthly progress presentations from raw notes, meeting records, metrics, or source files. Use for team status updates, progress reports, 週報、月報、進度簡報、工作匯報, or requests to turn operational updates into a Markdown outline and then a PowerPoint deck. Always create an editable outline first and require explicit approval before producing PPTX.
---

# Create Company Progress Deck

Create a 4–6 slide Traditional Chinese progress deck for internal team tracking. Accept unstructured inputs, normalize them into a reviewable Markdown outline, and enforce an approval gate before PowerPoint production.

## Route the request

1. Infer weekly or monthly mode from the request and reporting period.
2. Use weekly mode when the period is unclear; state that assumption in the outline.
3. Treat a user-provided destination, language, audience, company template, logo, font, or brand palette as authoritative.
4. Otherwise use Traditional Chinese, internal team tracking, and the Apple-inspired visual system in [apple-minimal-style.md](references/apple-minimal-style.md).
5. Use [progress-outline.md](references/progress-outline.md) for the exact outline structure and weekly/monthly slide sequence.

## Enforce the two-stage workflow

### Stage 1: Create or revise the outline

1. Read all supplied notes and files before drafting.
2. Separate facts from interpretations. Never invent results, numbers, owners, dates, targets, quotes, or status.
3. Keep the main deck between four and six slides. Combine or remove low-value detail before adding slides.
4. Create a user-facing Markdown deliverable, not a scratch planning file.
5. Save it to the user-specified location. Otherwise use `outputs/progress-deck/` under the current workspace.
6. Name weekly outlines `YYYY-Www-weekly-progress-outline.md` and monthly outlines `YYYY-MM-monthly-progress-outline.md`.
7. Mark unknown slide-visible information as `待補`; put all unresolved items in the final checklist.
8. Return the outline and stop. Do not create, initialize, or render a PPTX in the same turn.

When the user requests outline edits, update the Markdown only and remain in Stage 1.

### Approval gate

Proceed only when one of these conditions is true:

- The user explicitly approves the generated outline, such as `已核准`, `就照這版做`, or an equally clear instruction.
- The user supplies an edited complete Markdown outline and explicitly asks to turn that version into PowerPoint.

Do not treat the initial request to “make a deck” as approval of an outline created in that same turn. If any `待補` item would appear on a slide, ask the user to resolve it or explicitly authorize omitting it before continuing.

### Stage 2: Create the PowerPoint

1. Treat the approved or edited Markdown outline as the content source of truth.
2. Use the available Presentations skill and follow its local PowerPoint creation, source-note, rendering, and quality-assurance workflow.
3. Apply the explicit custom visual direction from [apple-minimal-style.md](references/apple-minimal-style.md). Do not use a generic bundled layout library.
4. If the user provides a PPTX template or reference deck, follow the Presentations template workflow and let that source override the default visual system.
5. Build a 16:9 PPTX with four to six main slides. Add an appendix only when explicitly requested.
6. Name the deck `YYYY-Www-weekly-progress.pptx` or `YYYY-MM-monthly-progress.pptx` beside its outline.
7. Use only claims and assets traceable to the approved outline or supplied sources. Add `[Sources]` speaker-note blocks when required by the Presentations workflow.
8. Render and inspect every slide at full size. Fix overflow, clipping, unexpected wrapping, unintended overlap, unresolved placeholders, inconsistent alignment, and chart/data mismatches.
9. Deliver only the approved outline and final PPTX unless the user requests build artifacts.

## Content rules

- Give each slide one narrative job and one takeaway-style title.
- Prefer outcomes and implications over task inventories.
- Keep owner, status, due date, risk impact, and next action together when those fields are available.
- Use target-versus-actual charts only when both values exist and share a valid basis.
- Use milestones instead of an empty KPI slide when quantitative data is unavailable.
- Keep `待補`, production notes, visual instructions, and approval language out of the final audience-facing slides.
- Preserve provided terminology and status labels; explain only when ambiguity affects interpretation.

## Output checks

Before returning an outline, confirm:

- The reporting period and mode are clear.
- The slide count is four to six.
- Every slide contains visible content, evidence/source notes, a visual suggestion, and a missing-information field.
- Every unsupported claim is removed or marked `待補`.
- No PPTX has been created before approval.

Before returning a deck, confirm:

- The exact approved outline drove the slide content.
- No unresolved placeholder remains.
- The design follows the selected brand or the default minimal style.
- Every slide passed visual inspection and overflow checks.
