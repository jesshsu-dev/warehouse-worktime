# 倉庫工時管理系統 V4.0（Supabase PostgreSQL）

## 上傳至 GitHub

請上傳：

- `warehouse_worktime_v4_supabase.py`
- 將 `requirements_v4_supabase.txt` 的內容複製到 Repository 根目錄的 `requirements.txt`

## Streamlit Cloud 部署設定

Main file path：

```text
warehouse_worktime_v4_supabase.py
```

## Streamlit Secrets

App settings → Secrets：

```toml
DATABASE_URL = "postgresql://Supabase顯示的user:URL編碼後的資料庫密碼@Shared-Pooler-Host:6543/postgres"
```

請直接複製 Supabase → Connect → Transaction pooler 的 URI，將 `[YOUR-PASSWORD]` 換成資料庫密碼。密碼若包含 `$`、`@`、`#`、`%`、`:`、`/` 等字元，必須先做 URL percent-encoding。

不要將 `.streamlit/secrets.toml` 或完整 `DATABASE_URL` 上傳到 GitHub。

## 首次登入

- 帳號：`admin`
- 密碼：`ChangeMe123!`

首次登入後必須修改密碼。

## 資料表

程式第一次啟動時會自動建立：

- `users`
- `work_logs`
- `active_timers`
- `audit_logs`

所有帳號、工時、計時狀態及稽核紀錄會儲存在 Supabase PostgreSQL。

## 重要安全事項

若資料庫密碼曾出現在截圖、聊天室或公開文件，請先在 Supabase 重設資料庫密碼，再更新 Streamlit Secrets。
