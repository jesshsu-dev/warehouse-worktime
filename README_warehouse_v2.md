# 倉庫工時管理系統 企業版 V2.0

## 功能

- Dashboard KPI 與工時趨勢
- 快速作業類型選擇
- 開始、暫停、繼續、停止計時
- SQLite 工時保存
- 手動新增工時
- 人員、作業類型及單據查詢
- 日報、月報、圖表與 CSV 匯出
- 支援手機、平板與電腦

## 本機執行

```bash
pip install -r requirements_v2.txt
streamlit run warehouse_worktime_v2.py
```

## Streamlit Cloud

Main file path：

```text
warehouse_worktime_v2.py
```

請將 `requirements_v2.txt` 改名為 `requirements.txt`，或把內容合併到原本的 `requirements.txt`。

## 資料保存提醒

目前使用 SQLite。Streamlit Community Cloud 在重新部署或容器重建時，可能不保證本機資料永久保留。正式上線建議改接 Supabase、MySQL 或 PostgreSQL。
