# 倉庫工時管理系統 V3.0（登入與權限版）

## GitHub 上傳檔案

- `warehouse_worktime_v3_auth.py`
- `requirements.txt`

`requirements.txt`：

```text
streamlit>=1.41
pandas>=2.2
```

## Streamlit 部署設定

Main file path：

```text
warehouse_worktime_v3_auth.py
```

## 首次登入

- 帳號：`admin`
- 密碼：`ChangeMe123!`

首次登入後會強制更改密碼。

## 角色權限

- 系統管理員：全部功能、帳號與權限、稽核紀錄
- 主管：工時登錄、全部查詢、報表與分析
- 作業人員：登錄本人資料、查詢本人明細
- 查詢人員：僅能查詢、報表與分析

## 正式環境提醒

Streamlit Community Cloud 的本機 SQLite 不適合重要正式資料長期保存。正式上線建議改接 PostgreSQL、Supabase 或 MySQL。
