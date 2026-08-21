---
name: create-google-workspace-project-starter
description: Create a reusable Google Workspace project starter kit with a Drive folder, one-page Google Docs project charter, Google Sheets task and milestone tracker, reference-materials folder, and date-aligned Google Calendar milestones. Use when a user asks to start or set up a project, formalize a verbal project idea, create a project charter or kickoff package, build a task tracker, or create a Google Workspace project template. Prefer copying the configured native templates and fall back to native reconstruction when the templates are unavailable.
---

# 建立 Google Workspace 專案起始包

把零散的專案構想整理成集中、可執行且日期一致的 Google Workspace 起始包。

## 工作流程

1. 讀取 [references/starter-kit-spec.md](references/starter-kit-spec.md)。
2. 讀取並遵守已安裝的 Google Drive、Google Docs、Google Sheets 與 Google Calendar Skills；使用其連接器完成操作。
3. 從使用者提供的內容擷取：
   - 專案名稱與一句話構想
   - 預計交付日
   - 專案負責人、參與人員與決策／核准者
   - 已知期限、預算、技術、法規限制及外部相依性
   - 目標、成果、驗收方式、範圍與里程碑
4. 對缺少的內容填入「待確認」，不要因資料不完整而停止建立；不要猜測日期、時區、電子郵件或期限。
5. 建立 `[專案名稱]｜專案起始包` Drive 資料夾。專案名稱缺少時使用 `待命名專案｜專案起始包`。
6. 在主資料夾內建立 `03｜參考資料` 子資料夾。
7. 優先依規格複製 Docs 與 Sheets 母版：
   - 把每個母版直接複製到新主資料夾。
   - 重新命名為 `01｜[專案名稱]｜專案立案單` 與 `02｜[專案名稱]｜專案任務與里程碑追蹤表`。
   - 只編輯副本，不得修改母版。
8. 若母版不存在、無權限或複製失敗，立即依規格原生重建該項成果。允許 Docs 使用複製路徑、Sheets 使用重建路徑，反之亦然。
9. 將已知資訊寫入立案單與追蹤表；保留未知欄位為「待確認」。讓 Docs 的四個里程碑與 Sheets「里程碑與日曆」分頁完全一致。
10. 僅為同時具備明確日期、時間與 IANA 時區的里程碑建立 Calendar 事件：
    - 使用主日曆，除非使用者指定其他日曆。
    - 使用規格中的事件名稱、持續時間、透明度與描述。
    - 只有取得已驗證電子郵件時才加入參與者。
    - 不符合條件的里程碑保持 `待建立`，不得建立暫定或猜測事件。
11. 將每個成功建立的 Calendar 事件連結回填 Sheets，並把狀態改為 `已建立`。
12. 完成前執行一致性檢查，然後回傳主資料夾、立案單、追蹤表及已建立 Calendar 事件的實際連結。

## 寫入與失敗安全

- 在任何既有文件寫入前確認檔案 ID、名稱與父資料夾。
- 不要修改、移動、重新命名或分享母版。
- 只使用工具回傳或讀回確認的 ID 與 URL，不要自行拼接未觀察到的連結。
- 任一成果失敗時保留已成功建立的內容，列出缺失項目與失敗原因，不要宣稱整套完成。
- 若 Calendar 建立失敗，將該里程碑狀態改為 `需更新`，並保留日期資料。
- 不要擴大分享權限；沿用新建檔案的預設存取狀態。

## 完成條件

只有在以下事項通過時才宣告完成：

- 主資料夾同時包含立案單、追蹤表與參考資料子資料夾。
- 立案單包含所有必備章節且沒有母版專案的殘留資料。
- 追蹤表包含三個指定分頁、欄位與下拉選項。
- Docs、Sheets 與 Calendar 中所有已知里程碑日期一致。
- Sheets 中每個 `已建立` 里程碑都有可讀回的 Calendar 事件連結。
- 所有未知資料均清楚標為「待確認」或 `待建立`。
