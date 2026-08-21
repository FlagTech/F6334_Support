# Progress outline specification

Use this structure for the user-facing Markdown outline. Keep wording concise and editable.

```markdown
# [團隊／專案名稱]｜[週／月]進度簡報大綱

- 報告類型：[週報／月報]
- 報告期間：[日期範圍]
- 主要受眾：團隊內部
- 簡報目標：[受眾看完後應理解或採取的行動]
- 預計頁數：[4–6]
- 使用假設：[無則填「無」]

## Slide 1 — [重點式標題]

- 敘事任務：[本頁唯一目的]
- 投影片可見內容：
  - [內容]
- 數據／來源：[檔案、筆記段落、使用者提供資料；無則填「無」]
- 建議視覺：[排版、簡表、原生圖表或大型數字]
- 待補：[無／需要補充的資訊]

[依序列出所有投影片]

## 待確認清單

- [所有未解決的待補項目；無則填「無」]

## 核准方式

請直接修改本檔，或明確回覆「已核准／就照這版做」。核准前不會產生 PPTX。
```

## Weekly default: five slides

1. **封面** — 團隊或專案、週次、日期範圍；保持極簡。
2. **本週總覽** — 整體狀態、最多三項關鍵進展、可用的核心指標。
3. **工作進展** — 已完成與進行中工作；保留負責人、狀態和必要日期。
4. **風險與阻礙** — 風險或依賴、影響、負責人、下一動作及所需協助。
5. **下週優先事項** — 三至五項優先工作、負責人和到期日。

When the input covers several workstreams, use a compact tracker table on slide 3. Do not create one slide per workstream unless the user explicitly requests a longer deck.

## Monthly default: six slides

1. **封面** — 團隊或專案、月份；保持極簡。
2. **月度摘要** — 最重要的結果、整體狀態和可用的核心指標。
3. **目標或指標進展** — 有可比數據時顯示目標與實際；否則改用關鍵成果或里程碑。
4. **工作與里程碑進展** — 已完成、延遲和進行中的主要工作。
5. **風險、經驗與所需協助** — 只保留會影響後續工作的內容。
6. **下月重點** — 三至五項優先事項、負責人和預期完成時間。

## Adaptation rules

- Keep the cover plus at least three content slides.
- Merge the metric and progress slides when evidence is sparse.
- Split an overloaded progress slide only if the total remains at six slides.
- Omit an empty category instead of filling it with generic copy.
- Move detailed task lists to an appendix only when the user explicitly requests one.
- Record any inferred report mode or date range under `使用假設`.
- Treat missing KPI data as optional when milestones communicate progress adequately.
- Treat any unresolved text intended for a slide as blocking until resolved or explicitly omitted.
