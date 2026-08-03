# 倉庫工時管理系統 V4.2.2 Enterprise

## 本版修正

- 修正手機版選擇功能後，按「開啟功能」沒有切換頁面的問題。
- 手機按鈕改用 `pending_page`：
  1. 記錄要前往的頁面。
  2. 執行 `st.rerun()`。
  3. 在建立左側選單前同步 `current_page`、`sidebar_page` 與 `fallback_page`。
- 避免左側選單殘留的舊值覆蓋手機選擇。
- 桌機左側選單仍可正常切換。
- 保留 V4.2.1 的：
  - 「上架作業」
  - 倉管角色別名辨識
  - 手機備援功能選單
  - Supabase PostgreSQL
  - Login 與 RBAC

## Streamlit 部署

```text
Repository: jesshsu-dev/warehouse-worktime
Branch: main
Main file path: warehouse_worktime_enterprise_v4_2_2.py
```

原有 `requirements.txt` 與 `DATABASE_URL` Secrets 不需要修改。
