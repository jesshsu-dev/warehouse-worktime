
import streamlit as st
import pandas as pd
from datetime import date, datetime, time
from io import BytesIO

st.set_page_config(
    page_title="倉庫作業工時登錄系統",
    page_icon="📦",
    layout="wide",
)

# -----------------------------
# 基本設定
# -----------------------------
TASK_TYPES = [
    "收料單",
    "發料單",
    "調撥單",
    "出貨單",
    "上架",
    "盤點",
    "開會",
    "上課",
    "其他",
]

TASK_ICONS = {
    "收料單": "🚚",
    "發料單": "📤",
    "調撥單": "🔁",
    "出貨單": "🚛",
    "上架": "⬆️",
    "盤點": "📋",
    "開會": "👥",
    "上課": "📚",
    "其他": "📝",
}

if "records" not in st.session_state:
    st.session_state.records = []

# -----------------------------
# 樣式
# -----------------------------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12345b 0%, #0b2747 100%);
    }
    [data-testid="stSidebar"] * {
        color: white;
    }
    .system-title {
        font-size: 1.75rem;
        font-weight: 800;
        margin-bottom: 0.1rem;
    }
    .system-subtitle {
        color: #6b7280;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        min-height: 118px;
    }
    .metric-label {
        color: #64748b;
        font-size: 0.92rem;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #0f172a;
        font-size: 1.75rem;
        font-weight: 800;
    }
    .panel-title {
        font-size: 1.15rem;
        font-weight: 750;
        margin-bottom: 0.7rem;
    }
    .task-note {
        color: #64748b;
        font-size: 0.88rem;
    }
    div.stButton > button {
        border-radius: 9px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# 工具函式
# -----------------------------
def minutes_to_text(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours} 小時 {minutes} 分"

def calc_minutes(start_t: time, end_t: time, cross_day: bool) -> int:
    start_dt = datetime.combine(date.today(), start_t)
    end_dt = datetime.combine(date.today(), end_t)
    if cross_day or end_dt < start_dt:
        end_dt = end_dt + pd.Timedelta(days=1)
    return max(0, int((end_dt - start_dt).total_seconds() // 60))

def records_dataframe() -> pd.DataFrame:
    columns = [
        "序號", "作業日期", "倉管人員", "作業類型", "單據／任務編號",
        "開始時間", "結束時間", "工時", "工時分鐘", "備註"
    ]
    if not st.session_state.records:
        return pd.DataFrame(columns=columns)

    rows = []
    for idx, item in enumerate(st.session_state.records, start=1):
        rows.append({
            "序號": idx,
            "作業日期": item["作業日期"],
            "倉管人員": item["倉管人員"],
            "作業類型": item["作業類型"],
            "單據／任務編號": item["單據／任務編號"],
            "開始時間": item["開始時間"],
            "結束時間": item["結束時間"],
            "工時": item["工時"],
            "工時分鐘": item["工時分鐘"],
            "備註": item["備註"],
        })
    return pd.DataFrame(rows)

# -----------------------------
# 側邊欄
# -----------------------------
with st.sidebar:
    st.markdown("## UPRtek")
    st.markdown("### 倉庫作業通報系統")
    st.divider()
    menu = st.radio(
        "功能選單",
        ["今日工時登錄", "工時明細查詢", "工時統計報表"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("群燿光學股份有限公司")
    st.caption("Warehouse Operation System")

# -----------------------------
# 頁首
# -----------------------------
st.markdown('<div class="system-title">倉庫作業工時登錄系統</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="system-subtitle">記錄倉管人員每日作業內容、開始時間、結束時間與實際工時。</div>',
    unsafe_allow_html=True,
)

df = records_dataframe()
total_minutes = int(df["工時分鐘"].sum()) if not df.empty else 0
record_count = len(df)
target_minutes = 480
remaining_minutes = max(0, target_minutes - total_minutes)
completion = min(100, round(total_minutes / target_minutes * 100)) if target_minutes else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-label">今日已登錄工時</div>
        <div class="metric-value">⏱️ {minutes_to_text(total_minutes)}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-label">工時完成率</div>
        <div class="metric-value">✅ {completion}%</div>
        </div>""",
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-label">已登錄筆數</div>
        <div class="metric-value">🧾 {record_count} 筆</div>
        </div>""",
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        f"""<div class="metric-card">
        <div class="metric-label">剩餘工時</div>
        <div class="metric-value">📅 {minutes_to_text(remaining_minutes)}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.write("")

# -----------------------------
# 今日工時登錄
# -----------------------------
if menu == "今日工時登錄":
    left, right = st.columns([1.55, 1], gap="large")

    with left:
        st.markdown('<div class="panel-title">新增作業工時</div>', unsafe_allow_html=True)

        with st.form("work_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                work_date = st.date_input("作業日期 *", value=date.today())
            with c2:
                employee = st.text_input("倉管人員 *", placeholder="請輸入姓名")

            task_type = st.selectbox("作業類型 *", TASK_TYPES)

            c3, c4 = st.columns(2)
            with c3:
                task_no = st.text_input(
                    "單據／任務編號",
                    placeholder="例：RCV-20260718-001",
                )
            with c4:
                cross_day = st.checkbox("跨日作業")

            c5, c6 = st.columns(2)
            with c5:
                start_time = st.time_input(
                    "開始時間 *",
                    value=time(8, 0),
                    step=300,
                )
            with c6:
                end_time = st.time_input(
                    "結束時間 *",
                    value=time(8, 30),
                    step=300,
                )

            calculated_minutes = calc_minutes(start_time, end_time, cross_day)
            st.info(f"系統自動計算工時：{minutes_to_text(calculated_minutes)}")

            description = st.text_area(
                "作業內容／備註",
                placeholder="例：供應商來料點收、數量核對及送驗。",
                height=110,
            )

            b1, b2 = st.columns([1, 2])
            with b1:
                reset_clicked = st.form_submit_button(
                    "清除重填",
                    use_container_width=True,
                )
            with b2:
                submitted = st.form_submit_button(
                    "新增登錄",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                if not employee.strip():
                    st.error("請輸入倉管人員姓名。")
                elif calculated_minutes <= 0:
                    st.error("工時必須大於 0 分鐘。")
                else:
                    st.session_state.records.append({
                        "作業日期": work_date.strftime("%Y/%m/%d"),
                        "倉管人員": employee.strip(),
                        "作業類型": task_type,
                        "單據／任務編號": task_no.strip() or "—",
                        "開始時間": start_time.strftime("%H:%M"),
                        "結束時間": end_time.strftime("%H:%M"),
                        "工時": minutes_to_text(calculated_minutes),
                        "工時分鐘": calculated_minutes,
                        "備註": description.strip(),
                    })
                    st.success("工時資料已新增。")
                    st.rerun()

    with right:
        st.markdown('<div class="panel-title">快速選擇作業類型</div>', unsafe_allow_html=True)
        quick_cols = st.columns(2)
        for idx, task in enumerate(TASK_TYPES[:-1]):
            with quick_cols[idx % 2]:
                st.button(
                    f"{TASK_ICONS[task]}  {task}",
                    key=f"quick_{task}",
                    use_container_width=True,
                    disabled=True,
                    help="請於左側表單選擇作業類型",
                )

        st.info(
            """
            **填寫說明**

            - 收料單：供應商來料收貨、點收及送驗  
            - 發料單：依工單或領料單備料、發料  
            - 調撥單：不同倉別或儲位間物料移轉  
            - 出貨單：成品備貨、裝箱及交付物流  
            - 上架：物料或成品入庫上架  
            - 盤點：定期或不定期庫存盤點  
            - 開會：部門或跨部門會議  
            - 上課：教育訓練或系統操作培訓  
            """
        )

    st.divider()
    st.markdown('<div class="panel-title">今日工時登錄明細</div>', unsafe_allow_html=True)

    df = records_dataframe()
    if df.empty:
        st.warning("目前尚無工時資料。")
    else:
        display_df = df.drop(columns=["工時分鐘"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        d1, d2, d3 = st.columns([1, 1, 2])
        with d1:
            delete_index = st.number_input(
                "刪除序號",
                min_value=1,
                max_value=len(df),
                value=1,
                step=1,
            )
        with d2:
            st.write("")
            st.write("")
            if st.button("刪除指定資料", type="secondary", use_container_width=True):
                st.session_state.records.pop(int(delete_index) - 1)
                st.success("資料已刪除。")
                st.rerun()
        with d3:
            csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
            st.write("")
            st.write("")
            st.download_button(
                "下載今日工時 CSV",
                data=csv_data,
                file_name=f"warehouse_worktime_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

# -----------------------------
# 工時明細查詢
# -----------------------------
elif menu == "工時明細查詢":
    st.markdown('<div class="panel-title">工時明細查詢</div>', unsafe_allow_html=True)

    df = records_dataframe()
    if df.empty:
        st.warning("目前尚無可查詢資料。")
    else:
        f1, f2 = st.columns(2)
        with f1:
            selected_employee = st.multiselect(
                "倉管人員",
                sorted(df["倉管人員"].unique().tolist()),
            )
        with f2:
            selected_tasks = st.multiselect(
                "作業類型",
                TASK_TYPES,
            )

        filtered = df.copy()
        if selected_employee:
            filtered = filtered[filtered["倉管人員"].isin(selected_employee)]
        if selected_tasks:
            filtered = filtered[filtered["作業類型"].isin(selected_tasks)]

        st.dataframe(
            filtered.drop(columns=["工時分鐘"]),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            f"查詢結果：{len(filtered)} 筆，合計工時："
            f"{minutes_to_text(int(filtered['工時分鐘'].sum()))}"
        )

# -----------------------------
# 工時統計報表
# -----------------------------
else:
    st.markdown('<div class="panel-title">工時統計報表</div>', unsafe_allow_html=True)

    df = records_dataframe()
    if df.empty:
        st.warning("目前尚無可統計資料。")
    else:
        task_summary = (
            df.groupby("作業類型", as_index=False)["工時分鐘"]
            .sum()
            .sort_values("工時分鐘", ascending=False)
        )
        task_summary["工時（小時）"] = (task_summary["工時分鐘"] / 60).round(2)

        employee_summary = (
            df.groupby("倉管人員", as_index=False)["工時分鐘"]
            .sum()
            .sort_values("工時分鐘", ascending=False)
        )
        employee_summary["工時（小時）"] = (
            employee_summary["工時分鐘"] / 60
        ).round(2)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 各作業類型工時")
            st.bar_chart(
                task_summary.set_index("作業類型")["工時（小時）"],
                use_container_width=True,
            )
            st.dataframe(
                task_summary[["作業類型", "工時（小時）"]],
                use_container_width=True,
                hide_index=True,
            )

        with c2:
            st.markdown("#### 各人員工時")
            st.bar_chart(
                employee_summary.set_index("倉管人員")["工時（小時）"],
                use_container_width=True,
            )
            st.dataframe(
                employee_summary[["倉管人員", "工時（小時）"]],
                use_container_width=True,
                hide_index=True,
            )

st.divider()
st.caption("建議使用 Chrome 或 Microsoft Edge 瀏覽器，解析度 1366 × 768 以上。")
