import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title='倉庫工時管理系統 企業版 V2.0', page_icon='📦', layout='wide')
DB_PATH = Path('warehouse_v2.db')
WORK_TYPES = ['收料單','發料單','出貨單','調撥單','上架','盤點','開會','上課','其他']
ICONS = {'收料單':'🚚','發料單':'📦','出貨單':'🚛','調撥單':'🔁','上架':'🏠','盤點':'📋','開會':'👥','上課':'📖','其他':'⋯'}


def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with closing(conn()) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS work_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL, employee TEXT NOT NULL, work_type TEXT NOT NULL,
            document_no TEXT, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL, note TEXT, created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_timer(
            id INTEGER PRIMARY KEY CHECK(id=1), employee TEXT NOT NULL,
            work_type TEXT NOT NULL, document_no TEXT, start_time TEXT NOT NULL,
            paused_seconds INTEGER NOT NULL DEFAULT 0, pause_started_at TEXT, note TEXT)''')
        c.commit()


def fetch_logs():
    with closing(conn()) as c:
        return pd.read_sql_query('SELECT * FROM work_logs ORDER BY work_date DESC,start_time DESC', c)


def get_timer():
    with closing(conn()) as c:
        row = c.execute('SELECT employee,work_type,document_no,start_time,paused_seconds,pause_started_at,note FROM active_timer WHERE id=1').fetchone()
    if not row:
        return None
    return dict(zip(['employee','work_type','document_no','start_time','paused_seconds','pause_started_at','note'], row))


def start_timer(employee, work_type, document_no, note):
    with closing(conn()) as c:
        c.execute('DELETE FROM active_timer')
        c.execute('INSERT INTO active_timer VALUES(1,?,?,?,?,0,NULL,?)',
                  (employee,work_type,document_no,datetime.now().isoformat(timespec='seconds'),note))
        c.commit()


def pause_timer():
    with closing(conn()) as c:
        c.execute('UPDATE active_timer SET pause_started_at=? WHERE id=1 AND pause_started_at IS NULL',
                  (datetime.now().isoformat(timespec='seconds'),))
        c.commit()


def resume_timer():
    t = get_timer()
    if not t or not t['pause_started_at']:
        return
    extra = int((datetime.now()-datetime.fromisoformat(t['pause_started_at'])).total_seconds())
    with closing(conn()) as c:
        c.execute('UPDATE active_timer SET paused_seconds=paused_seconds+?, pause_started_at=NULL WHERE id=1',(extra,))
        c.commit()


def stop_timer(note=''):
    t = get_timer()
    if not t:
        return
    end = datetime.now(); start = datetime.fromisoformat(t['start_time']); paused = int(t['paused_seconds'])
    if t['pause_started_at']:
        paused += int((end-datetime.fromisoformat(t['pause_started_at'])).total_seconds())
    duration = max(1,int((end-start).total_seconds())-paused)
    with closing(conn()) as c:
        c.execute('''INSERT INTO work_logs(work_date,employee,work_type,document_no,start_time,end_time,duration_seconds,note,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?)''',
                  (start.date().isoformat(),t['employee'],t['work_type'],t['document_no'],t['start_time'],
                   end.isoformat(timespec='seconds'),duration,note or t['note'],datetime.now().isoformat(timespec='seconds')))
        c.execute('DELETE FROM active_timer')
        c.commit()


def fmt_hm(sec):
    sec = int(sec or 0); h, r = divmod(sec,3600); m = r//60
    return f'{h} 小時 {m} 分'


def fmt_clock(sec):
    sec = int(max(0,sec)); h,r=divmod(sec,3600); m,s=divmod(r,60)
    return f'{h:02d}:{m:02d}:{s:02d}'


def elapsed(t):
    if not t: return 0
    now=datetime.now(); start=datetime.fromisoformat(t['start_time']); paused=int(t['paused_seconds'])
    if t['pause_started_at']:
        paused += int((now-datetime.fromisoformat(t['pause_started_at'])).total_seconds())
    return max(0,int((now-start).total_seconds())-paused)


init_db()
if 'selected_type' not in st.session_state:
    st.session_state.selected_type='發料單'

st.markdown('''<style>
.block-container{max-width:1800px;padding-top:1rem}.card{background:white;border:1px solid #e5eaf0;border-radius:14px;padding:16px;box-shadow:0 3px 12px rgba(8,34,67,.05)}
.kpi-label{color:#64748b;font-size:.9rem}.kpi-value{font-size:1.7rem;font-weight:850;color:#0f172a}.section{font-weight:800;color:#16365f;margin:.8rem 0}.timer{border:1px solid #dce5ef;border-radius:12px;padding:18px;text-align:center;background:#f7fbff}.timer-value{font-size:2rem;font-weight:900;color:#0aa84f}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#082f5a,#031f3d)}[data-testid="stSidebar"] *{color:white}div.stButton>button{border-radius:9px;font-weight:700}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## 🔴 UPRtek')
    st.markdown('### 倉庫工時管理系統')
    page=st.radio('功能', ['首頁 Dashboard','今日工時登錄','工時明細查詢','作業單據查詢','工時日報表','工時月報表','圖表分析','系統設定'], label_visibility='collapsed')
    st.divider(); st.caption('企業版 V2.0｜Warehouse Operation System')

st.title('倉庫工時管理系統 企業版 V2.0')
st.caption('Warehouse Work Time Management System')

raw=fetch_logs()
if not raw.empty:
    raw['work_date']=pd.to_datetime(raw['work_date']); raw['start_dt']=pd.to_datetime(raw['start_time']); raw['end_dt']=pd.to_datetime(raw['end_time'])
    raw['日期']=raw['work_date'].dt.strftime('%Y/%m/%d'); raw['時間']=raw['start_dt'].dt.strftime('%H:%M')+' - '+raw['end_dt'].dt.strftime('%H:%M'); raw['工時']=raw['duration_seconds'].apply(fmt_hm)

today=pd.Timestamp(date.today()); yesterday=today-pd.Timedelta(days=1); month_start=today.replace(day=1)
today_df=raw[raw['work_date']==today] if not raw.empty else raw
yesterday_df=raw[raw['work_date']==yesterday] if not raw.empty else raw
month_df=raw[raw['work_date']>=month_start] if not raw.empty else raw
today_sec=int(today_df['duration_seconds'].sum()) if not today_df.empty else 0
yesterday_sec=int(yesterday_df['duration_seconds'].sum()) if not yesterday_df.empty else 0
month_sec=int(month_df['duration_seconds'].sum()) if not month_df.empty else 0

if page=='首頁 Dashboard':
    main,quick=st.columns([4.5,1.25],gap='large')
    with main:
        cols=st.columns(4)
        vals=[('🕘 今日工時',fmt_hm(today_sec)),('🟢 昨日工時',fmt_hm(yesterday_sec)),('🗓️ 本月工時',f'{month_sec/3600:.1f} hr'),('👥 本月加班',f'{max(0,month_sec-176*3600)/3600:.1f} hr')]
        for c,(lab,val) in zip(cols,vals):
            with c: st.markdown(f'<div class="card"><div class="kpi-label">{lab}</div><div class="kpi-value">{val}</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="section">今日作業統計</div>',unsafe_allow_html=True)
        counts=today_df['work_type'].value_counts().to_dict() if not today_df.empty else {}
        cc=st.columns(6)
        for c,t in zip(cc,WORK_TYPES[:6]):
            with c: st.metric(f'{ICONS[t]} {t}',counts.get(t,0),'筆')
        a,b,c=st.columns([1.2,1.1,1.4])
        with a:
            st.markdown('<div class="section">今日工時占比</div>',unsafe_allow_html=True)
            if today_df.empty: st.info('今日尚無資料')
            else: st.bar_chart((today_df.groupby('work_type')['duration_seconds'].sum()/3600).rename('工時(hr)'))
        with b:
            st.markdown('<div class="section">工時排行榜（今日）</div>',unsafe_allow_html=True)
            if today_df.empty: st.info('今日尚無資料')
            else:
                r=today_df.groupby('employee',as_index=False)['duration_seconds'].sum().sort_values('duration_seconds',ascending=False).head(5); r['工時']=r['duration_seconds'].apply(fmt_hm)
                st.dataframe(r[['employee','工時']],use_container_width=True,hide_index=True)
        with c:
            st.markdown('<div class="section">近期工時趨勢（本月）</div>',unsafe_allow_html=True)
            if month_df.empty: st.info('本月尚無資料')
            else:
                s=month_df.groupby('work_date')['duration_seconds'].sum()/3600; s.index=s.index.strftime('%m/%d'); st.line_chart(s.rename('工時(hr)'))
        st.markdown('<div class="section">今日工時明細（最新）</div>',unsafe_allow_html=True)
        if today_df.empty: st.warning('目前尚無資料')
        else:
            v=today_df.head(8)[['時間','work_type','document_no','工時','note']].copy(); v.columns=['時間','作業類型','單號','工時','備註']; st.dataframe(v,use_container_width=True,hide_index=True)
    with quick:
        st.subheader('快速工時登錄')
        employee=st.text_input('人員',value='徐桂英'); st.date_input('日期',value=date.today(),disabled=True)
        grid=st.columns(3)
        for i,t in enumerate(WORK_TYPES):
            with grid[i%3]:
                if st.button(f'{ICONS[t]}\n{t}',key=f'type_{t}',use_container_width=True,type='primary' if st.session_state.selected_type==t else 'secondary'):
                    st.session_state.selected_type=t; st.rerun()
        doc=st.text_input('單號',placeholder='SO240718-098'); note=st.text_area('備註',height=80)
        t=get_timer(); e=elapsed(t)
        st.markdown(f'<div class="timer"><div>{"暫停中" if t and t["pause_started_at"] else "計時中" if t else "尚未開始"}</div><div class="timer-value">{fmt_clock(e)}</div></div>',unsafe_allow_html=True)
        if not t:
            if st.button('▶ 開始計時',type='primary',use_container_width=True):
                if employee.strip(): start_timer(employee.strip(),st.session_state.selected_type,doc.strip(),note); st.rerun()
                else: st.error('請輸入人員姓名')
        else:
            x,y=st.columns(2)
            with x:
                if t['pause_started_at']:
                    if st.button('▶ 繼續',use_container_width=True): resume_timer(); st.rerun()
                else:
                    if st.button('⏸ 暫停',use_container_width=True): pause_timer(); st.rerun()
            with y:
                if st.button('■ 停止計時',type='primary',use_container_width=True): stop_timer(note); st.rerun()
            st.caption(f'目前作業：{t["work_type"]}｜{t["document_no"] or "無單號"}')
            st.button('🔄 更新計時畫面',use_container_width=True)

elif page=='今日工時登錄':
    st.subheader('今日工時登錄')
    with st.form('manual'):
        c1,c2=st.columns(2); employee=c1.text_input('倉管人員 *',value='徐桂英'); work_type=c2.selectbox('作業類型 *',WORK_TYPES)
        doc=st.text_input('單據／任務編號'); c3,c4=st.columns(2); s=c3.time_input('開始時間'); e=c4.time_input('結束時間'); note=st.text_area('備註')
        if st.form_submit_button('新增工時',type='primary',use_container_width=True):
            sd=datetime.combine(date.today(),s); ed=datetime.combine(date.today(),e)
            if ed<=sd: ed+=timedelta(days=1)
            with closing(conn()) as c:
                c.execute('INSERT INTO work_logs(work_date,employee,work_type,document_no,start_time,end_time,duration_seconds,note,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                          (date.today().isoformat(),employee.strip(),work_type,doc.strip(),sd.isoformat(timespec='seconds'),ed.isoformat(timespec='seconds'),int((ed-sd).total_seconds()),note.strip(),datetime.now().isoformat(timespec='seconds'))); c.commit()
            st.success('工時資料已新增'); st.rerun()
    if not today_df.empty:
        v=today_df[['id','日期','employee','work_type','document_no','時間','工時','note']].copy(); v.columns=['ID','日期','人員','作業類型','單號','時間','工時','備註']; st.dataframe(v,use_container_width=True,hide_index=True)

elif page=='工時明細查詢':
    st.subheader('工時明細查詢')
    if raw.empty: st.warning('目前尚無資料')
    else:
        a,b=st.columns(2); emps=a.multiselect('人員',sorted(raw['employee'].unique())); types=b.multiselect('作業類型',WORK_TYPES)
        r=raw.copy()
        if emps: r=r[r['employee'].isin(emps)]
        if types: r=r[r['work_type'].isin(types)]
        v=r[['id','日期','employee','work_type','document_no','時間','工時','note']].copy(); v.columns=['ID','日期','人員','作業類型','單號','時間','工時','備註']; st.dataframe(v,use_container_width=True,hide_index=True)
        st.download_button('下載 CSV',v.to_csv(index=False).encode('utf-8-sig'),'warehouse_logs.csv','text/csv')

elif page=='作業單據查詢':
    st.subheader('作業單據查詢'); kw=st.text_input('輸入單據／任務編號')
    if kw and not raw.empty:
        r=raw[raw['document_no'].fillna('').str.contains(kw,case=False,na=False)]; st.dataframe(r[['日期','employee','work_type','document_no','時間','工時','note']],use_container_width=True,hide_index=True)
    else: st.info('輸入單據編號後即可查詢')

elif page=='工時日報表':
    st.subheader('工時日報表'); d=st.date_input('報表日期',value=date.today()); r=raw[raw['work_date']==pd.Timestamp(d)] if not raw.empty else raw
    if r.empty: st.warning('該日期無資料')
    else:
        s=r.groupby(['employee','work_type'],as_index=False)['duration_seconds'].sum(); s['工時']=s['duration_seconds'].apply(fmt_hm); st.dataframe(s[['employee','work_type','工時']],use_container_width=True,hide_index=True)

elif page=='工時月報表':
    st.subheader('工時月報表'); d=st.date_input('選擇月份',value=date.today().replace(day=1)); start=pd.Timestamp(d.replace(day=1)); end=start+pd.offsets.MonthEnd(1); r=raw[(raw['work_date']>=start)&(raw['work_date']<=end)] if not raw.empty else raw
    if r.empty: st.warning('該月份無資料')
    else:
        s=r.groupby('employee',as_index=False)['duration_seconds'].sum(); s['總工時(hr)']=(s['duration_seconds']/3600).round(2); st.dataframe(s[['employee','總工時(hr)']],use_container_width=True,hide_index=True); st.bar_chart(s.set_index('employee')['總工時(hr)'])

elif page=='圖表分析':
    st.subheader('圖表分析')
    if raw.empty: st.warning('目前尚無資料')
    else:
        a,b=st.columns(2)
        with a: st.bar_chart((raw.groupby('work_type')['duration_seconds'].sum()/3600).rename('工時(hr)'))
        with b: st.bar_chart((raw.groupby('employee')['duration_seconds'].sum()/3600).rename('工時(hr)'))

else:
    st.subheader('系統設定')
    st.info('目前使用 SQLite 保存資料。Streamlit Community Cloud 重新部署時，本機資料可能重建；正式上線建議改接 Supabase、MySQL 或 PostgreSQL。')

st.divider(); st.caption('建議使用 Chrome 或 Microsoft Edge；支援手機、平板及電腦。')
