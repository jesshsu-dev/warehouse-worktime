# 倉庫工時管理系統 V4.2.1 Enterprise

## 本次修正

1. `備料作業` 已全面更名為 `上架作業`。
2. 強化倉管角色辨識，以下角色都會正規化為 `operator`：
   - operator
   - 作業人員
   - 倉管
   - 倉管人員
   - warehouse
3. 桌機保留左側功能選單。
4. 手機或側邊欄收合時，主畫面上方提供「☰ 功能選單」備援操作。
5. 倉管預設可使用：
   - 首頁 Dashboard
   - 今日工時登錄
   - 我的工時明細
   - 作業單據查詢

## Streamlit

```text
Main file path:
warehouse_worktime_enterprise_v4_2_1.py
```

原本的 `requirements.txt` 與 `DATABASE_URL` Secrets 不需要更改。
