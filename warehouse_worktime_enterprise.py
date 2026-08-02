import hashlib
import hmac
import os
import secrets
from contextlib import closing
from datetime import date, datetime, time, timedelta
import pandas as pd
import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
import streamlit as st

st.set_page_config(
    page_title="倉庫工時管理系統 V4.2 Enterprise",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Role-based access control settings
ROLE_LABELS = {
    "admin": "系統管理員",
    "manager": "主管",
    "operator": "作業人員",
    "viewer": "查詢人員",
}

WORK_TYPES = [
    "收料作業",
    "發料單",
    "出貨作業",
    "調撥作業",
    "盤點作業",
    "退料作業",
    "備料作業",
    "其他作業",
]

ICONS = {
    "收料作業": "📥",
    "發料單": "📤",
    "出貨作業": "🚚",
    "調撥作業": "🔄",
    "盤點作業": "📋",
    "退料作業": "↩️",
    "備料作業": "📦",
    "其他作業": "🛠️",
}

ROLE_PAGES = {
    "admin": [
        "首頁 Dashboard",
        "今日工時登錄",
        "工時明細查詢",
        "作業單據查詢",
        "工時日報表",
        "工時月報表",
        "圖表分析",
        "帳號與權限",
    ],
    "manager": [
        "首頁 Dashboard",
        "今日工時登錄",
        "工時明細查詢",
        "作業單據查詢",
        "工時日報表",
        "工時月報表",
        "圖表分析",
    ],
    "operator": [
        "首頁 Dashboard",
        "今日工時登錄",
        "我的工時明細",
        "作業單據查詢",
    ],
    "viewer": [
        "首頁 Dashboard",
        "工時明細查詢",
        "作業單據查詢",
        "工時日報表",
        "工時月報表",
        "圖表分析",
    ],
}

def parse_hhmm(value: str) -> time:
    """Parse an HH:MM string and return a time object."""
    cleaned = value.strip().replace("：", ":")
    try:
        return datetime.strptime(cleaned, "%H:%M").time()
    except ValueError as exc:
        raise ValueError("時間格式請輸入 HH:MM，例如 08:30 或 17:05。") from exc


def dropdown_time(prefix: str, default: time) -> time:
    """Render hour/minute dropdowns and return the selected time."""
    hour_col, minute_col = st.columns(2)
    hour = hour_col.selectbox(
        "時",
        list(range(24)),
        index=default.hour,
        format_func=lambda value: f"{value:02d}",
        key=f"{prefix}_hour",
    )
    minute_values = list(range(60))
    minute = minute_col.selectbox(
        "分",
        minute_values,
        index=default.minute,
        format_func=lambda value: f"{value:02d}",
        key=f"{prefix}_minute",
    )
    return time(hour=int(hour), minute=int(minute))


def database_url() -> str:
    """Read the PostgreSQL URL from Streamlit Secrets or an environment variable."""
    try:
        value = str(st.secrets["DATABASE_URL"]).strip()
    except Exception:
        value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "尚未設定 DATABASE_URL。請到 Streamlit Cloud → App settings → Secrets 設定 Supabase 連線字串。"
        )
    return value


def conn() -> psycopg.Connection:
    # Supabase Transaction Pooler (port 6543) does not support prepared statements.
    return psycopg.connect(
        database_url(),
        row_factory=dict_row,
        prepare_threshold=None,
        connect_timeout=15,
    )


def read_df(query: str, params: tuple | None = None) -> pd.DataFrame:
    """Execute a query with dict rows and convert safely to a DataFrame."""
    with closing(conn()) as c:
        rows = c.execute(query, params or ()).fetchall()
    return pd.DataFrame([dict(row) for row in rows])


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def init_db() -> None:
    with closing(conn()) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id BIGSERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin','manager','operator','viewer')),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS work_logs(
                id BIGSERIAL PRIMARY KEY,
                work_date TEXT NOT NULL,
                employee TEXT NOT NULL,
                username TEXT NOT NULL,
                work_type TEXT NOT NULL,
                document_no TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds BIGINT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS active_timers(
                username TEXT PRIMARY KEY,
                employee TEXT NOT NULL,
                work_type TEXT NOT NULL,
                document_no TEXT,
                start_time TEXT NOT NULL,
                paused_seconds BIGINT NOT NULL DEFAULT 0,
                pause_started_at TEXT,
                note TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs(
                id BIGSERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                detail TEXT,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_work_logs_date ON work_logs(work_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_work_logs_username ON work_logs(username)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_work_logs_document ON work_logs(document_no)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)")

        user_count = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if user_count == 0:
            bootstrap_user = os.getenv("WAREHOUSE_ADMIN_USER", "admin")
            bootstrap_password = os.getenv("WAREHOUSE_ADMIN_PASSWORD", "ChangeMe123!")
            now = datetime.now().isoformat(timespec="seconds")
            c.execute(
                """INSERT INTO users(username, display_name, password_hash, role, is_active,
                                     must_change_password, created_at, updated_at)
                   VALUES(%s,%s,%s,%s,TRUE,TRUE,%s,%s)""",
                (bootstrap_user, "系統管理員", hash_password(bootstrap_password), "admin", now, now),
            )
        c.commit()


def audit(username: str, action: str, target: str = "", detail: str = "") -> None:
    with closing(conn()) as c:
        c.execute(
            "INSERT INTO audit_logs(username,action,target,detail,created_at) VALUES(%s,%s,%s,%s,%s)",
            (username, action, target, detail, datetime.now().isoformat(timespec="seconds")),
        )
        c.commit()


def authenticate(username: str, password: str):
    with closing(conn()) as c:
        row = c.execute(
            "SELECT * FROM users WHERE lower(username)=lower(%s)", (username.strip(),)
        ).fetchone()
    if not row or not row["is_active"] or not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def current_user() -> dict:
    return st.session_state.get("auth_user", {})


def logout() -> None:
    user = current_user()
    if user:
        audit(user["username"], "LOGOUT")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def fetch_logs() -> pd.DataFrame:
    return read_df("SELECT * FROM work_logs ORDER BY work_date DESC, start_time DESC")


def get_timer(username: str):
    with closing(conn()) as c:
        row = c.execute("SELECT * FROM active_timers WHERE username=%s", (username,)).fetchone()
    return dict(row) if row else None


def start_timer(username: str, employee: str, work_type: str, document_no: str, note: str) -> None:
    with closing(conn()) as c:
        c.execute("DELETE FROM active_timers WHERE username=%s", (username,))
        c.execute(
            """INSERT INTO active_timers(username,employee,work_type,document_no,start_time,
                                         paused_seconds,pause_started_at,note)
               VALUES(%s,%s,%s,%s,%s,0,NULL,%s)""",
            (username, employee, work_type, document_no, datetime.now().isoformat(timespec="seconds"), note),
        )
        c.commit()
    audit(username, "TIMER_START", document_no, work_type)


def pause_timer(username: str) -> None:
    with closing(conn()) as c:
        c.execute(
            "UPDATE active_timers SET pause_started_at=%s WHERE username=%s AND pause_started_at IS NULL",
            (datetime.now().isoformat(timespec="seconds"), username),
        )
        c.commit()
    audit(username, "TIMER_PAUSE")


def resume_timer(username: str) -> None:
    timer = get_timer(username)
    if not timer or not timer["pause_started_at"]:
        return
    extra = int((datetime.now() - datetime.fromisoformat(timer["pause_started_at"])).total_seconds())
    with closing(conn()) as c:
        c.execute(
            """UPDATE active_timers
               SET paused_seconds=paused_seconds+%s, pause_started_at=NULL
               WHERE username=%s""",
            (extra, username),
        )
        c.commit()
    audit(username, "TIMER_RESUME")


def stop_timer(username: str, final_note: str = "") -> None:
    timer = get_timer(username)
    if not timer:
        return
    end = datetime.now()
    start = datetime.fromisoformat(timer["start_time"])
    paused = int(timer["paused_seconds"])
    if timer["pause_started_at"]:
        paused += int((end - datetime.fromisoformat(timer["pause_started_at"])).total_seconds())
    duration = max(1, int((end - start).total_seconds()) - paused)
    with closing(conn()) as c:
        c.execute(
            """INSERT INTO work_logs(work_date,employee,username,work_type,document_no,start_time,
                                     end_time,duration_seconds,note,created_at,created_by)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                start.date().isoformat(), timer["employee"], username, timer["work_type"],
                timer["document_no"], timer["start_time"], end.isoformat(timespec="seconds"),
                duration, final_note or timer["note"], datetime.now().isoformat(timespec="seconds"), username,
            ),
        )
        c.execute("DELETE FROM active_timers WHERE username=%s", (username,))
        c.commit()
    audit(username, "TIMER_STOP", timer["document_no"] or "", f"{timer['work_type']} / {duration}s")


def fmt_hm(seconds) -> str:
    seconds = int(seconds or 0)
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours} 小時 {minutes} 分"


def fmt_clock(seconds) -> str:
    seconds = int(max(0, seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def elapsed(timer) -> int:
    if not timer:
        return 0
    now = datetime.now()
    start = datetime.fromisoformat(timer["start_time"])
    paused = int(timer["paused_seconds"])
    if timer["pause_started_at"]:
        paused += int((now - datetime.fromisoformat(timer["pause_started_at"])).total_seconds())
    return max(0, int((now - start).total_seconds()) - paused)


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    user = authenticate(username, old_password)
    if not user:
        return False, "原密碼不正確。"
    if len(new_password) < 10 or not any(x.isalpha() for x in new_password) or not any(x.isdigit() for x in new_password):
        return False, "新密碼至少 10 碼，且須包含英文字母與數字。"
    now = datetime.now().isoformat(timespec="seconds")
    with closing(conn()) as c:
        c.execute(
            "UPDATE users SET password_hash=%s, must_change_password=FALSE, updated_at=%s WHERE username=%s",
            (hash_password(new_password), now, username),
        )
        c.commit()
    audit(username, "PASSWORD_CHANGE")
    return True, "密碼已更新，請重新登入。"


try:
    init_db()
except Exception as exc:
    st.error("無法連線至 Supabase PostgreSQL。")
    st.code(str(exc))
    st.info("請確認 Streamlit Secrets 的 DATABASE_URL、資料庫密碼與 Shared Pooler（port 6543）設定。")
    st.stop()

st.markdown("""
<style>
.block-container{max-width:1800px;padding-top:1rem}.login-wrap{max-width:470px;margin:7vh auto 0 auto}
.login-card{background:white;border:1px solid #dfe7f1;border-radius:18px;padding:30px;box-shadow:0 18px 55px rgba(15,35,65,.12)}
.card{background:white;border:1px solid #e5eaf0;border-radius:14px;padding:16px;box-shadow:0 3px 12px rgba(8,34,67,.05)}
.kpi-label{color:#64748b;font-size:.9rem}.kpi-value{font-size:1.7rem;font-weight:850;color:#0f172a}
.section{font-weight:800;color:#16365f;margin:.8rem 0}.timer{border:1px solid #dce5ef;border-radius:12px;padding:18px;text-align:center;background:#f7fbff}
.timer-value{font-size:2rem;font-weight:900;color:#0aa84f}.role-badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#eaf2ff;color:#174b8d;font-weight:700;font-size:.8rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#082f5a,#031f3d)}[data-testid="stSidebar"] *{color:white}
div.stButton>button{border-radius:9px;font-weight:700}
/* Best-effort hiding of Streamlit chrome inside the app canvas.
   The Community Cloud owner-only Manage app overlay is rendered by the hosting platform
   and may still appear while the App owner is signed in. Ordinary users do not have admin access. */
[data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.viewerBadge_container__1QSob,
.stDeployButton,
#MainMenu,
footer{display:none!important;visibility:hidden!important}
</style>
""", unsafe_allow_html=True)

# ---------- Login ----------
if "auth_user" not in st.session_state:
    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)
    st.markdown("## 🔐 倉庫工時管理系統")
    st.caption("UPRtek Warehouse Work Time Management System")
    with st.form("login_form"):
        username = st.text_input("帳號", placeholder="請輸入帳號")
        password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
        submitted = st.form_submit_button("登入系統", type="primary", use_container_width=True)
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.auth_user = user
            st.session_state.selected_type = "發料單"
            audit(user["username"], "LOGIN")
            st.rerun()
        else:
            st.error("帳號或密碼錯誤，或此帳號已停用。")
    with st.expander("首次登入說明"):
        st.write("預設管理員帳號為 `admin`，預設密碼為 `ChangeMe123!`。首次登入後系統會要求立即更改密碼。")
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

user = current_user()

# ---------- Forced password change ----------
if user.get("must_change_password"):
    st.warning("為確保系統安全，首次登入必須先更改密碼。")
    with st.form("forced_change_password"):
        old_password = st.text_input("目前密碼", type="password")
        new_password = st.text_input("新密碼", type="password")
        confirm_password = st.text_input("確認新密碼", type="password")
        submitted = st.form_submit_button("更新密碼", type="primary")
    if submitted:
        if new_password != confirm_password:
            st.error("兩次輸入的新密碼不一致。")
        else:
            ok, message = change_password(user["username"], old_password, new_password)
            if ok:
                st.success(message)
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            else:
                st.error(message)
    st.stop()

allowed_pages = ROLE_PAGES.get(user.get("role"), ROLE_PAGES["viewer"])

with st.sidebar:
    st.markdown("## 🔴 UPRtek")
    st.markdown("### 倉庫工時管理系統")
    st.markdown(f"**{user['display_name']}**")
    st.markdown(f'<span class="role-badge">{ROLE_LABELS.get(user.get("role"), "未知角色")}</span>', unsafe_allow_html=True)
    page = st.radio("功能", allowed_pages, label_visibility="collapsed")
    st.divider()
    if st.button("🔑 變更密碼", use_container_width=True):
        st.session_state.show_password_dialog = True
    if st.button("🚪 登出", use_container_width=True):
        logout()
    st.caption("企業版 V4.2 Enterprise｜Supabase PostgreSQL｜Login & RBAC")

if st.session_state.get("show_password_dialog"):
    with st.expander("變更密碼", expanded=True):
        with st.form("change_password_form"):
            old_password = st.text_input("目前密碼", type="password", key="cp_old")
            new_password = st.text_input("新密碼", type="password", key="cp_new")
            confirm_password = st.text_input("確認新密碼", type="password", key="cp_confirm")
            a, b = st.columns(2)
            save = a.form_submit_button("儲存", type="primary", use_container_width=True)
            cancel = b.form_submit_button("取消", use_container_width=True)
        if cancel:
            st.session_state.show_password_dialog = False
            st.rerun()
        if save:
            if new_password != confirm_password:
                st.error("兩次輸入的新密碼不一致。")
            else:
                ok, message = change_password(user["username"], old_password, new_password)
                if ok:
                    st.success(message)
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                else:
                    st.error(message)

st.title("倉庫工時管理系統 企業版 V4.2 Enterprise")
st.caption(f"登入者：{user['display_name']}｜權限：{ROLE_LABELS.get(user.get('role'), '未知角色')}")

raw = fetch_logs()
if not raw.empty:
    raw["work_date"] = pd.to_datetime(raw["work_date"])
    raw["start_dt"] = pd.to_datetime(raw["start_time"])
    raw["end_dt"] = pd.to_datetime(raw["end_time"])
    raw["日期"] = raw["work_date"].dt.strftime("%Y/%m/%d")
    raw["時間"] = raw["start_dt"].dt.strftime("%H:%M") + " - " + raw["end_dt"].dt.strftime("%H:%M")
    raw["工時"] = raw["duration_seconds"].apply(fmt_hm)

# Operator can only see own detailed data.
visible_raw = raw
if user["role"] == "operator" and not raw.empty:
    visible_raw = raw[raw["username"] == user["username"]].copy()

today = pd.Timestamp(date.today())
yesterday = today - pd.Timedelta(days=1)
month_start = today.replace(day=1)
today_df = visible_raw[visible_raw["work_date"] == today] if not visible_raw.empty else visible_raw
yesterday_df = visible_raw[visible_raw["work_date"] == yesterday] if not visible_raw.empty else visible_raw
month_df = visible_raw[visible_raw["work_date"] >= month_start] if not visible_raw.empty else visible_raw
today_sec = int(today_df["duration_seconds"].sum()) if not today_df.empty else 0
yesterday_sec = int(yesterday_df["duration_seconds"].sum()) if not yesterday_df.empty else 0
month_sec = int(month_df["duration_seconds"].sum()) if not month_df.empty else 0

if page == "首頁 Dashboard":
    cols = st.columns(4)
    values = [
        ("🕘 今日工時", fmt_hm(today_sec)),
        ("🟢 昨日工時", fmt_hm(yesterday_sec)),
        ("🗓️ 本月工時", f"{month_sec / 3600:.1f} hr"),
        ("🧾 今日筆數", f"{len(today_df)} 筆"),
    ]
    for column, (label, value) in zip(cols, values):
        with column:
            st.markdown(f'<div class="card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)

    left, right = st.columns([4.5, 1.35], gap="large")
    with left:
        st.markdown('<div class="section">今日作業統計</div>', unsafe_allow_html=True)
        counts = today_df["work_type"].value_counts().to_dict() if not today_df.empty else {}
        stat_cols = st.columns(6)
        for column, work_type in zip(stat_cols, WORK_TYPES[:6]):
            with column:
                st.metric(f"{ICONS[work_type]} {work_type}", counts.get(work_type, 0), "筆")
        a, b = st.columns(2)
        with a:
            st.markdown('<div class="section">本月作業工時</div>', unsafe_allow_html=True)
            if month_df.empty:
                st.info("本月尚無資料")
            else:
                st.bar_chart((month_df.groupby("work_type")["duration_seconds"].sum() / 3600).rename("工時(hr)"))
        with b:
            st.markdown('<div class="section">近期工時趨勢</div>', unsafe_allow_html=True)
            if month_df.empty:
                st.info("本月尚無資料")
            else:
                trend = month_df.groupby("work_date")["duration_seconds"].sum() / 3600
                trend.index = trend.index.strftime("%m/%d")
                st.line_chart(trend.rename("工時(hr)"))
        st.markdown('<div class="section">今日工時明細</div>', unsafe_allow_html=True)
        if today_df.empty:
            st.warning("目前尚無資料")
        else:
            view = today_df.head(10)[["時間", "employee", "work_type", "document_no", "工時", "note"]].copy()
            view.columns = ["時間", "人員", "作業類型", "單號", "工時", "備註"]
            st.dataframe(view, use_container_width=True, hide_index=True)

    with right:
        if user["role"] in ("admin", "manager", "operator"):
            st.subheader("快速工時登錄")
            employee = st.text_input("人員", value=user["display_name"], disabled=user["role"] == "operator")
            grid = st.columns(3)
            for index, work_type in enumerate(WORK_TYPES):
                with grid[index % 3]:
                    if st.button(
                        f"{ICONS[work_type]}\n{work_type}",
                        key=f"type_{work_type}",
                        use_container_width=True,
                        type="primary" if st.session_state.get("selected_type") == work_type else "secondary",
                    ):
                        st.session_state.selected_type = work_type
                        st.rerun()
            document_no = st.text_input("單號", placeholder="SO240718-098")
            note = st.text_area("備註", height=75)
            timer = get_timer(user["username"])
            seconds = elapsed(timer)
            state_text = "暫停中" if timer and timer["pause_started_at"] else "計時中" if timer else "尚未開始"
            st.markdown(f'<div class="timer"><div>{state_text}</div><div class="timer-value">{fmt_clock(seconds)}</div></div>', unsafe_allow_html=True)
            if not timer:
                if st.button("▶ 開始計時", type="primary", use_container_width=True):
                    if employee.strip():
                        start_timer(user["username"], employee.strip(), st.session_state.get("selected_type", "發料單"), document_no.strip(), note.strip())
                        st.rerun()
                    else:
                        st.error("請輸入人員姓名。")
            else:
                x, y = st.columns(2)
                with x:
                    if timer["pause_started_at"]:
                        if st.button("▶ 繼續", use_container_width=True):
                            resume_timer(user["username"]); st.rerun()
                    else:
                        if st.button("⏸ 暫停", use_container_width=True):
                            pause_timer(user["username"]); st.rerun()
                with y:
                    if st.button("■ 停止計時", type="primary", use_container_width=True):
                        stop_timer(user["username"], note.strip()); st.rerun()
                st.caption(f"目前作業：{timer['work_type']}｜{timer['document_no'] or '無單號'}")
                st.button("🔄 更新計時畫面", use_container_width=True)
        else:
            st.info("目前帳號為查詢權限，無法新增工時。")

elif page == "今日工時登錄":
    st.subheader("今日工時登錄")

    # 必須放在 st.form 外面，切換選項時 Streamlit 才會立即重新渲染欄位。
    input_mode = st.radio(
        "時間輸入方式",
        ["手動 Key in", "下拉選擇（時／分）"],
        horizontal=True,
        key="manual_time_input_mode",
        help="手動輸入請使用 HH:MM；下拉模式可分別選擇小時與分鐘。",
    )

    default_start = datetime.now().replace(second=0, microsecond=0).time()
    default_end = (datetime.now() + timedelta(hours=1)).replace(second=0, microsecond=0).time()
    time_error = None

    with st.form("manual_entry"):
        c1, c2 = st.columns(2)
        employee = c1.text_input("倉管人員 *", value=user["display_name"], disabled=user["role"] == "operator")
        work_type = c2.selectbox("作業類型 *", WORK_TYPES)
        document_no = st.text_input("單據／任務編號")

        if input_mode == "手動 Key in":
            c3, c4 = st.columns(2)
            start_text = c3.text_input(
                "開始時間（HH:MM）",
                value=default_start.strftime("%H:%M"),
                placeholder="08:30",
                key="manual_start_text",
            )
            end_text = c4.text_input(
                "結束時間（HH:MM）",
                value=default_end.strftime("%H:%M"),
                placeholder="17:30",
                key="manual_end_text",
            )
            try:
                start_time = parse_hhmm(start_text)
                end_time = parse_hhmm(end_text)
            except ValueError as exc:
                start_time = end_time = None
                time_error = str(exc)
        else:
            c3, c4 = st.columns(2)
            with c3:
                st.markdown("**開始時間**")
                start_time = dropdown_time("manual_start_dropdown", default_start)
            with c4:
                st.markdown("**結束時間**")
                end_time = dropdown_time("manual_end_dropdown", default_end)

        note = st.text_area("備註")
        submitted = st.form_submit_button("新增工時", type="primary", use_container_width=True)
    if submitted:
        if time_error or start_time is None or end_time is None:
            st.error(time_error or "請輸入有效的開始及結束時間。")
            st.stop()
        start_dt = datetime.combine(date.today(), start_time)
        end_dt = datetime.combine(date.today(), end_time)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        with closing(conn()) as c:
            c.execute(
                """INSERT INTO work_logs(work_date,employee,username,work_type,document_no,start_time,
                                         end_time,duration_seconds,note,created_at,created_by)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    date.today().isoformat(), employee.strip(), user["username"], work_type,
                    document_no.strip(), start_dt.isoformat(timespec="seconds"), end_dt.isoformat(timespec="seconds"),
                    int((end_dt - start_dt).total_seconds()), note.strip(), datetime.now().isoformat(timespec="seconds"), user["username"],
                ),
            )
            c.commit()
        audit(user["username"], "WORKLOG_CREATE", document_no.strip(), work_type)
        st.success("工時資料已新增。")
        st.rerun()

elif page in ("工時明細查詢", "我的工時明細"):
    st.subheader(page)
    data = visible_raw.copy()
    if data.empty:
        st.warning("目前尚無資料。")
    else:
        if page == "工時明細查詢":
            a, b = st.columns(2)
            employees = a.multiselect("人員", sorted(data["employee"].dropna().unique()))
            types = b.multiselect("作業類型", WORK_TYPES)
            if employees:
                data = data[data["employee"].isin(employees)]
            if types:
                data = data[data["work_type"].isin(types)]
        view = data[["id", "日期", "employee", "work_type", "document_no", "時間", "工時", "note"]].copy()
        view.columns = ["ID", "日期", "人員", "作業類型", "單號", "時間", "工時", "備註"]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("下載 CSV", view.to_csv(index=False).encode("utf-8-sig"), "warehouse_logs.csv", "text/csv")

elif page == "作業單據查詢":
    st.subheader("作業單據查詢")
    keyword = st.text_input("輸入單據／任務編號")
    if keyword and not visible_raw.empty:
        result = visible_raw[visible_raw["document_no"].fillna("").str.contains(keyword, case=False, na=False)]
        st.dataframe(result[["日期", "employee", "work_type", "document_no", "時間", "工時", "note"]], use_container_width=True, hide_index=True)
    else:
        st.info("輸入單據編號後即可查詢。")

elif page == "工時日報表":
    st.subheader("工時日報表")
    report_date = st.date_input("報表日期", value=date.today())
    result = visible_raw[visible_raw["work_date"] == pd.Timestamp(report_date)] if not visible_raw.empty else visible_raw
    if result.empty:
        st.warning("該日期無資料。")
    else:
        summary = result.groupby(["employee", "work_type"], as_index=False)["duration_seconds"].sum()
        summary["工時"] = summary["duration_seconds"].apply(fmt_hm)
        st.dataframe(summary[["employee", "work_type", "工時"]], use_container_width=True, hide_index=True)

elif page == "工時月報表":
    st.subheader("工時月報表")
    selected_month = st.date_input("選擇月份", value=date.today().replace(day=1))
    start = pd.Timestamp(selected_month.replace(day=1))
    end = start + pd.offsets.MonthEnd(1)
    result = visible_raw[(visible_raw["work_date"] >= start) & (visible_raw["work_date"] <= end)] if not visible_raw.empty else visible_raw
    if result.empty:
        st.warning("該月份無資料。")
    else:
        summary = result.groupby("employee", as_index=False)["duration_seconds"].sum()
        summary["總工時(hr)"] = (summary["duration_seconds"] / 3600).round(2)
        st.dataframe(summary[["employee", "總工時(hr)"]], use_container_width=True, hide_index=True)
        st.bar_chart(summary.set_index("employee")["總工時(hr)"])

elif page == "圖表分析":
    st.subheader("圖表分析")
    if visible_raw.empty:
        st.warning("目前尚無資料。")
    else:
        a, b = st.columns(2)
        with a:
            st.bar_chart((visible_raw.groupby("work_type")["duration_seconds"].sum() / 3600).rename("工時(hr)"))
        with b:
            st.bar_chart((visible_raw.groupby("employee")["duration_seconds"].sum() / 3600).rename("工時(hr)"))

elif page == "帳號與權限":
    st.subheader("帳號與權限管理")
    tab1, tab2, tab3 = st.tabs(["帳號清單", "新增帳號", "稽核紀錄"])
    with tab1:
        users_df = read_df(
            "SELECT id,username,display_name,role,is_active,must_change_password,created_at,updated_at FROM users ORDER BY id"
        )
        users_df["role"] = users_df["role"].fillna("operator").where(users_df["role"].isin(ROLE_LABELS), "operator")
        users_df["角色"] = users_df["role"].map(ROLE_LABELS)
        users_df["狀態"] = users_df["is_active"].map({True: "啟用", False: "停用", 1: "啟用", 0: "停用"}).fillna("未知")
        users_df["首次改密碼"] = users_df["must_change_password"].map({True: "是", False: "否", 1: "是", 0: "否"}).fillna("未知")
        st.dataframe(users_df[["id", "username", "display_name", "角色", "狀態", "首次改密碼", "created_at"]], use_container_width=True, hide_index=True)

        st.markdown("#### 修改帳號")
        usernames = users_df["username"].tolist()
        selected_username = st.selectbox("選擇帳號", usernames)
        selected = users_df[users_df["username"] == selected_username].iloc[0]
        with st.form("edit_user"):
            display_name = st.text_input("顯示姓名", value=selected["display_name"])
            selected_role = selected.get("role") if hasattr(selected, "get") else selected["role"]
            if selected_role not in ROLE_LABELS:
                selected_role = "operator"
            role_options = list(ROLE_LABELS)
            role = st.selectbox(
                "角色",
                role_options,
                index=role_options.index(selected_role),
                format_func=lambda x: ROLE_LABELS[x],
            )
            active = st.checkbox("啟用帳號", value=bool(selected["is_active"]))
            reset_password = st.text_input("重設密碼（不變更請留白）", type="password")
            save = st.form_submit_button("儲存變更", type="primary")
        if save:
            if selected_username == user["username"] and not active:
                st.error("不可停用目前登入中的管理員帳號。")
            elif reset_password and len(reset_password) < 10:
                st.error("重設密碼至少需要 10 碼。")
            else:
                now = datetime.now().isoformat(timespec="seconds")
                with closing(conn()) as c:
                    if reset_password:
                        c.execute(
                            """UPDATE users SET display_name=%s,role=%s,is_active=%s,password_hash=%s,
                                                must_change_password=TRUE,updated_at=%s WHERE username=%s""",
                            (display_name.strip(), role, bool(active), hash_password(reset_password), now, selected_username),
                        )
                    else:
                        c.execute(
                            "UPDATE users SET display_name=%s,role=%s,is_active=%s,updated_at=%s WHERE username=%s",
                            (display_name.strip(), role, bool(active), now, selected_username),
                        )
                    c.commit()
                audit(user["username"], "USER_UPDATE", selected_username, f"role={role}, active={active}")
                st.success("帳號已更新。")
                st.rerun()

    with tab2:
        with st.form("create_user"):
            new_username = st.text_input("登入帳號 *")
            new_display_name = st.text_input("姓名 *")
            new_role = st.selectbox("角色 *", list(ROLE_LABELS), format_func=lambda x: ROLE_LABELS[x])
            new_password = st.text_input("初始密碼 *", type="password")
            create = st.form_submit_button("建立帳號", type="primary", use_container_width=True)
        if create:
            if not new_username.strip() or not new_display_name.strip():
                st.error("帳號與姓名不可空白。")
            elif len(new_password) < 10:
                st.error("初始密碼至少需要 10 碼。")
            else:
                now = datetime.now().isoformat(timespec="seconds")
                try:
                    with closing(conn()) as c:
                        c.execute(
                            """INSERT INTO users(username,display_name,password_hash,role,is_active,
                                                 must_change_password,created_at,updated_at)
                               VALUES(%s,%s,%s,%s,TRUE,TRUE,%s,%s)""",
                            (new_username.strip(), new_display_name.strip(), hash_password(new_password), new_role, now, now),
                        )
                        c.commit()
                    audit(user["username"], "USER_CREATE", new_username.strip(), new_role)
                    st.success("帳號已建立；使用者首次登入時必須更改密碼。")
                except UniqueViolation:
                    st.error("此登入帳號已存在。")

    with tab3:
        audit_df = read_df("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 500")
        st.dataframe(audit_df, use_container_width=True, hide_index=True)

else:
    st.subheader("系統設定")
    st.markdown("#### 權限矩陣")
    matrix = pd.DataFrame({
        "角色": ["系統管理員", "主管", "作業人員", "查詢人員"],
        "新增工時": ["✓", "✓", "✓（本人）", "—"],
        "查詢全部資料": ["✓", "✓", "—", "✓"],
        "報表與分析": ["✓", "✓", "—", "✓"],
        "帳號管理": ["✓", "—", "—", "—"],
    })
    st.dataframe(matrix, use_container_width=True, hide_index=True)
    st.success("目前資料已儲存於 Supabase PostgreSQL；Streamlit 重新部署或休眠不會刪除資料庫內容。")
    st.warning("仍建議定期執行資料庫備份，並妥善保管 DATABASE_URL。")
    st.info("公開網址仍可被任何人開啟，但未通過帳號與密碼驗證者無法進入系統功能。")

st.divider()
st.caption("建議使用 Chrome 或 Microsoft Edge；請勿將初始密碼或 DATABASE_URL 透過公開群組傳送。")
