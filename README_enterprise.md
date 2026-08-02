# 倉庫工時管理系統 V4.2 Enterprise

## Streamlit 部署

```text
Repository: jesshsu-dev/warehouse-worktime
Branch: main
Main file path: warehouse_worktime_enterprise.py
```

將 `requirements_enterprise.txt` 的內容複製至 GitHub 根目錄的 `requirements.txt`。

Secrets：

```toml
DATABASE_URL = "postgresql://Supabase顯示的user:已URL編碼的密碼@Shared-Pooler-Host:6543/postgres?sslmode=require"
```

## 本版重點

- 手動 Key in 支援 `HH:MM`。
- 下拉模式可分別選擇 00–23 時、00–59 分。
- 時間模式位於表單外，切換後立即顯示對應欄位。
- PostgreSQL 查詢結果安全轉換成 DataFrame。
- 異常或空白角色安全預設為 `operator`。
- 修正 PostgreSQL boolean 欄位顯示。
- 登入、RBAC、工時、報表、帳號管理、稽核紀錄。
- Supabase Transaction Pooler 使用 `prepare_threshold=None`。

## Manage app

`Manage app` 是 Streamlit Community Cloud 提供給 App 擁有者的外層管理介面。
程式只能盡量隱藏 App 內工具列，無法保證移除擁有者登入時的管理浮層。
一般未登入擁有者 Streamlit 帳號的同仁不會取得管理權限。
