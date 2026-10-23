import streamlit as st
import pandas as pd
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from io import BytesIO
import sqlite3
from pathlib import Path

# ------------------------------------------------------------
# Page configuration
# ------------------------------------------------------------
st.set_page_config(page_title="송천고 행사 관리 시스템", page_icon="📚", layout="wide", initial_sidebar_state="collapsed")
SEOUL = ZoneInfo("Asia/Seoul")
def now_seoul():
    return datetime.now(SEOUL)
DB_PATH = Path(__file__).with_name("library_system.db")

# ------------------------------------------------------------
# Database: existing table names and columns are preserved
# ------------------------------------------------------------
def get_db_connection():
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event_name TEXT NOT NULL,
            student_id TEXT NOT NULL, grade INTEGER NOT NULL, class INTEGER NOT NULL,
            number INTEGER NOT NULL, name TEXT NOT NULL, timestamp TEXT NOT NULL,
            operator TEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            category TEXT NOT NULL, detail TEXT NOT NULL, operator TEXT NOT NULL)''')
        # 기존 DB를 유지하면서 행사 종류와 설명 컬럼만 필요한 경우 추가
        event_cols = {row[1] for row in cur.execute("PRAGMA table_info(events)").fetchall()}
        if 'event_type' not in event_cols:
            cur.execute("ALTER TABLE events ADD COLUMN event_type TEXT NOT NULL DEFAULT '기타'")
        if 'description' not in event_cols:
            cur.execute("ALTER TABLE events ADD COLUMN description TEXT NOT NULL DEFAULT ''")

def read_table(query):
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

def db_get_events(): return read_table("SELECT * FROM events ORDER BY id DESC")
def db_get_participants(): return read_table("SELECT * FROM participants ORDER BY id DESC")
def db_get_logs(): return read_table("SELECT * FROM logs ORDER BY id DESC")

def db_add_event(name, status, created_at, event_type="기타", description=""):
    with get_db_connection() as conn:
        conn.execute("INSERT INTO events (name,status,created_at,event_type,description) VALUES (?,?,?,?,?)", (name,status,created_at,event_type,description))

def db_update_event_status(event_id, new_status):
    with get_db_connection() as conn:
        conn.execute("UPDATE events SET status=? WHERE id=?", (new_status,event_id))

def db_delete_event_and_records(event_id, event_name):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.execute("DELETE FROM participants WHERE event_name=?", (event_name,))

def db_add_participant(data):
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO participants
            (event_name,student_id,grade,class,number,name,timestamp,operator)
            VALUES (?,?,?,?,?,?,?,?)''', (data['event_name'],data['student_id'],data['grade'],data['class'],data['number'],data['name'],data['timestamp'],data['operator']))

def db_delete_participant(part_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM participants WHERE id=?", (part_id,))

def db_update_participant(part_id, event_name, student_id, grade, class_num, number, name):
    with get_db_connection() as conn:
        conn.execute('''UPDATE participants SET event_name=?,student_id=?,grade=?,class=?,number=?,name=? WHERE id=?''',
                     (event_name,student_id,grade,class_num,number,name,part_id))

def db_add_log(category, detail, operator):
    with get_db_connection() as conn:
        conn.execute("INSERT INTO logs (timestamp,category,detail,operator) VALUES (?,?,?,?)",
                     (now_seoul().strftime("%Y-%m-%d %H:%M:%S"),category,detail,operator))

def db_clear_logs():
    with get_db_connection() as conn:
        conn.execute("DELETE FROM logs")

init_db()

# ------------------------------------------------------------
# Jaenact-inspired glassmorphism design, embedded in this file
# ------------------------------------------------------------
st.markdown(r'''<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
:root { --ink:#20232b; --muted:#737b8c; --blue:#3182F6; --blue2:#1B64DA; --line:rgba(133,145,169,.20); }
html, body, [class*="css"], [data-testid="stAppViewContainer"] { font-family: Pretendard, -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { color:var(--ink); background: radial-gradient(ellipse at 15% 28%,rgba(151,164,255,.19),transparent 34%), radial-gradient(ellipse at 82% 42%,rgba(164,205,255,.22),transparent 34%), linear-gradient(135deg,#f4f5fb 0%,#f9fafc 48%,#edf1f9 100%); }
[data-testid="stHeader"] { background:rgba(248,249,253,.78); backdrop-filter:blur(18px); }
[data-testid="stToolbar"] { right:1rem; }
.block-container { max-width:1320px; padding-top:1.4rem; padding-bottom:3rem; }
/* Top brand panel */
.brandbar { display:flex; justify-content:space-between; align-items:center; gap:1rem; padding:17px 24px; margin:0 0 26px; border:1px solid rgba(255,255,255,.88); border-radius:28px; background:rgba(255,255,255,.68); backdrop-filter:blur(20px); box-shadow:0 12px 34px rgba(61,73,104,.08); }
.brandname { font-size:19px; font-weight:800; letter-spacing:-.5px; color:#20232b; }
.branddesc { color:#737b8c; font-size:13px; }
.eyebrow { display:inline-block; color:#3182F6; font-size:12px; letter-spacing:2px; font-weight:800; text-transform:uppercase; padding-bottom:9px; border-bottom:2px solid #1B64DA; margin-bottom:15px; }
.hero-card, .glass-card { border:1px solid rgba(255,255,255,.92); border-radius:28px; background:rgba(255,255,255,.74); backdrop-filter:blur(18px); box-shadow:0 18px 50px rgba(51,65,97,.09); }
.hero-card { padding:42px 36px; text-align:center; }
.hero-title { font-size:clamp(30px,4vw,44px); line-height:1.15; letter-spacing:-1.7px; font-weight:850; margin:8px 0 12px; color:#20232b; }
.hero-subtitle { color:#687184; font-size:16px; line-height:1.7; margin:0 0 18px; }
.glass-card { padding:25px 27px; margin-bottom:18px; }
.section-title { font-size:27px; letter-spacing:-.8px; font-weight:820; margin:4px 0 22px; color:#20232b; }
.muted { color:#7b8291; }
.pill { display:inline-block; border:1px solid rgba(104,133,245,.18); color:#1B64DA; background:rgba(224,233,255,.72); padding:7px 13px; border-radius:999px; font-size:12px; font-weight:750; }
/* Streamlit buttons */
.stButton > button, .stDownloadButton > button { width:100%; min-height:46px; border-radius:15px; border:1px solid rgba(255,255,255,.9); background:linear-gradient(135deg,#3182F6,#1B64DA); color:#fff; font-weight:750; box-shadow:0 8px 20px rgba(49,130,246,.22); transition:transform .18s ease,box-shadow .18s ease,filter .18s ease; }
.stButton > button p, .stButton > button span, .stDownloadButton > button p { color:#fff !important; font-weight:750; }
.stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-1px); box-shadow:0 12px 26px rgba(49,130,246,.30); border-color:rgba(255,255,255,.95); filter:saturate(1.08); }
.stButton > button:focus, .stDownloadButton > button:focus { outline:2px solid rgba(49,130,246,.25); outline-offset:2px; }
/* Inputs */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input, [data-testid="stTimeInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-radius:13px !important; border-color:#dfe4ef !important; background:rgba(255,255,255,.82) !important; min-height:43px; }
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus { border-color:#3182F6 !important; box-shadow:0 0 0 2px rgba(49,130,246,.12) !important; }
label, [data-testid="stWidgetLabel"] p { color:#424a5b !important; font-weight:650 !important; }
/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:7px; padding:7px; border:1px solid rgba(255,255,255,.95); border-radius:20px; background:rgba(255,255,255,.58); }
[data-testid="stTabs"] button[role="tab"] { border-radius:14px; padding:11px 15px; color:#626b7b; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:#fff; box-shadow:0 5px 15px rgba(70,84,120,.12); color:#1B64DA; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background:transparent; }
/* Data tables and alerts */
[data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid #e6eaf2; border-radius:16px; overflow:hidden; }
[data-testid="stAlert"] { border-radius:14px; }
[data-testid="stExpander"] { border:1px solid #e2e7f0; border-radius:15px; background:rgba(255,255,255,.56); }
hr { border-color:rgba(125,139,165,.18) !important; }
h1,h2,h3,h4 { color:#20232b; letter-spacing:-.65px; }
[data-testid="stTextInput"] input { min-height:54px !important; font-size:17px !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div { min-height:54px !important; font-size:16px !important; }
.stMetric { background:rgba(255,255,255,.78); border:1px solid rgba(255,255,255,.95); border-radius:20px; padding:18px 20px; box-shadow:0 10px 26px rgba(51,65,97,.06); }
@media (max-width: 760px) { .block-container { padding-left:1rem; padding-right:1rem; padding-top:1rem; } .brandbar { padding:15px 17px; border-radius:20px; align-items:flex-start; flex-direction:column; } .hero-card { padding:28px 19px; } .glass-card { padding:19px; } .section-title { font-size:24px; } [data-testid="stTabs"] [data-baseweb="tab-list"] { flex-wrap:wrap; } }
</style>''', unsafe_allow_html=True)

st.markdown('''<div class="brandbar"><div class="brandname">Songcheon <span style="color:#3182F6">Lib Tech</span></div><div class="branddesc">인천송천고등학교 · 행사 관리 시스템</div></div>''', unsafe_allow_html=True)

def parse_student_id(std_id):
    value = str(std_id).strip()
    if len(value) == 5 and value.isdigit():
        return True, int(value[0]), int(value[1:3]), int(value[3:5])
    return False, None, None, None

def find_student_name(student_id):
    sid = str(student_id).strip()
    if not sid:
        return ""
    df = db_get_participants()
    if df.empty:
        return ""
    matches = df[df["student_id"].astype(str).str.strip() == sid]
    if matches.empty:
        return ""
    names = matches["name"].dropna().astype(str).str.strip()
    names = names[names != ""]
    return names.iloc[0] if not names.empty else ""

def fill_participant_name():
    sid = st.session_state.get("participant_sid", "").strip()
    matched_name = find_student_name(sid) if len(sid) == 5 and sid.isdigit() else ""
    if matched_name:
        st.session_state["participant_name"] = matched_name

def fill_staff_student_name():
    sid = st.session_state.get("staff_search_id", "").strip()
    matched_name = find_student_name(sid) if len(sid) == 5 and sid.isdigit() else ""
    if matched_name:
        st.session_state["staff_search_name"] = matched_name

def event_options(df):
    return [f"[{r['status']}] {r['name']}" for _, r in df.iterrows()] if not df.empty else ["등록된 행사 없음"]
def clean_event(value):
    return value.split("] ", 1)[-1] if "] " in value else value

if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'staff_info' not in st.session_state: st.session_state.staff_info = None

# ------------------------------------------------------------
# Main landing screen
# ------------------------------------------------------------
if st.session_state.user_role is None:
    spacer1, main, spacer2 = st.columns([1, 1.35, 1])
    with main:
        st.markdown('''<div class="hero-card"><div class="eyebrow">EVENT MANAGEMENT</div><div class="hero-title">인천송천고 도서관</div><p class="hero-subtitle">행사 출석 등록부터 통합 데이터 관리까지<br>한곳에서 간편하게 관리하세요.</p><span class="pill">SONGCHEON EVENT SYSTEM</span></div>''', unsafe_allow_html=True)
        st.write("")
        if st.button("학생 · 일반 참여자 등록", use_container_width=True):
            st.session_state.user_role = 'participant'; st.rerun()
        if st.button("사서교사 · 도서부원 관리자 로그인", use_container_width=True):
            st.session_state.user_role = 'staff_login'; st.rerun()

# ------------------------------------------------------------
# Staff login
# ------------------------------------------------------------
elif st.session_state.user_role == 'staff_login':
    _, main, _ = st.columns([1, 1.25, 1])
    with main:
        st.markdown('<div class="eyebrow">STAFF LOGIN</div><div class="section-title">관리자 로그인</div><p class="muted">담당자 정보를 입력해 로그인해 주세요.</p>', unsafe_allow_html=True)
        staff_type = st.selectbox("직위 구분", ["도서부원", "사서교사"])
        if staff_type == "도서부원":
            staff_std_id = st.text_input("학번 (5자리)", placeholder="예: 10101", max_chars=5)
            staff_name = st.text_input("이름", placeholder="이름을 입력하세요")
        else:
            staff_std_id = "교직원"
            staff_name = st.text_input("이름", placeholder="담당 선생님 이름")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("관리자 접속"):
                valid, *_ = parse_student_id(staff_std_id) if staff_type == "도서부원" else (True, None, None, None)
                if not valid or not staff_name.strip(): st.error("올바른 학번과 이름을 입력해 주세요.")
                else:
                    st.session_state.staff_info = f"{staff_type} {staff_std_id} {staff_name.strip()}" if staff_type == "도서부원" else f"사서교사 {staff_name.strip()}"
                    st.session_state.user_role = 'staff'
                    db_add_log("시스템 접속", f"{st.session_state.staff_info} 접속함", st.session_state.staff_info)
                    st.rerun()
        with c2:
            if st.button("메인으로", key="login_home"):
                st.session_state.user_role = None; st.rerun()
        st.caption("안내: 현재는 담당자 정보만 입력해 접속합니다. 비밀번호 확인 기능은 아직 없습니다.")

# ------------------------------------------------------------
# Participant registration
# ------------------------------------------------------------
elif st.session_state.user_role == 'participant':
    top1, top2 = st.columns([5, 1])
    with top1: st.markdown('<div class="eyebrow">EVENT CHECK-IN</div><div class="section-title">도서관 행사 참여 등록</div>', unsafe_allow_html=True)
    with top2:
        if st.button("메인으로", key="participant_home"):
            st.session_state.user_role = None; st.rerun()
    _, formcol, _ = st.columns([0.7, 2.2, 0.7])
    with formcol:
        st.markdown('<div class="glass-card"><b>참여 정보를 입력해 주세요</b><p class="muted">행사를 선택하고 학번과 이름을 입력하면 등록됩니다.</p></div>', unsafe_allow_html=True)
        df_events = db_get_events()
        selected = st.selectbox("참여할 행사", event_options(df_events), key="participant_event")
        sid = st.text_input("학번 (5자리)", placeholder="예: 10101", max_chars=5, key="participant_sid", on_change=fill_participant_name, help="학번을 입력하면 기존 등록 정보가 있을 때 이름이 자동으로 채워집니다.")
        pname = st.text_input("이름", placeholder="학번과 이름을 확인해 주세요", key="participant_name")
        if st.button("참여 등록하기"):
            valid, grade, class_num, number = parse_student_id(sid)
            if "행사 없음" in selected: st.error("등록 가능한 행사가 없습니다.")
            elif "[마감]" in selected: st.error("마감된 행사입니다. 도서부원에게 문의해 주세요.")
            elif not valid or not pname.strip(): st.error("올바른 5자리 학번과 이름을 입력해 주세요.")
            else:
                event = clean_event(selected)
                db_add_participant({"event_name":event,"student_id":sid.strip(),"grade":grade,"class":class_num,"number":number,"name":pname.strip(),"timestamp":now_seoul().strftime("%Y-%m-%d %H:%M:%S"),"operator":"참여자 본인"})
                db_add_log("참여자 등록", f"[{event}] {sid} {pname.strip()} 등록 완료", "참여자 본인")
                st.success(f"{pname.strip()}님, 정상적으로 등록되었습니다!")

# ------------------------------------------------------------
# Staff administration dashboard
# ------------------------------------------------------------
elif st.session_state.user_role == 'staff':
    h1, h2 = st.columns([5, 1])
    with h1:
        st.markdown(f'<div class="eyebrow">ADMIN WORKSPACE</div><div class="section-title">행사 관리 시스템</div><p class="muted">접속 계정: {st.session_state.staff_info}</p>', unsafe_allow_html=True)
    with h2:
        if st.button("로그아웃"):
            st.session_state.user_role = None; st.session_state.staff_info = None; st.rerun()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["출석 등록", "행사 관리", "통계 대시보드", "처리 이력", "백업/복원"])

    with tab1:
        df_p = db_get_participants(); df_e = db_get_events()
        left, right = st.columns([1, 1.7], gap="large")
        with left:
            st.markdown('<div class="eyebrow">STUDENT LOOKUP</div><h3>학생 검색</h3><p class="muted">학번과 이름으로 과거 참여 이력을 확인합니다.</p>', unsafe_allow_html=True)
            search_id = st.text_input("학번 (5자리)", key="staff_search_id", placeholder="예: 10101", max_chars=5, on_change=fill_staff_student_name)
            search_name = st.text_input("이름", key="staff_search_name", placeholder="학생 이름")
            valid, grade, class_num, number = parse_student_id(search_id)
            if search_id.strip() or search_name.strip():
                if not search_id.strip() or not search_name.strip():
                    st.caption("학번과 이름을 모두 입력해야 참여 이력을 확인할 수 있습니다.")
                elif not df_p.empty:
                    history = df_p[(df_p['student_id'].astype(str).str.strip() == search_id.strip()) & (df_p['name'].astype(str).str.strip() == search_name.strip())]
                    if not history.empty:
                        st.success(f"학번과 이름이 모두 일치합니다 · 참여 이력 {len(history)}건")
                        for _, row in history.iterrows(): st.markdown(f"- **{row['event_name']}** · {row['timestamp']}")
                    else: st.info("학번과 이름이 모두 일치하는 참여 이력이 없습니다.")
                else:
                    st.info("과거 참여 이력이 없습니다.")
        with right:
            st.markdown('<div class="eyebrow">ATTENDANCE</div><h3>행사 출석 확인 및 등록</h3><p class="muted">행사를 선택하고 학생 정보를 확인한 뒤 등록합니다.</p>', unsafe_allow_html=True)
            selected = st.selectbox("등록할 행사", event_options(df_e), key="staff_event")
            with st.expander("일시 수동 지정 (소급 등록)"):
                cdate = st.date_input("날짜", value=now_seoul().date(), key="retro_date")
                ctime = st.time_input("시간", value=now_seoul().time().replace(tzinfo=None, microsecond=0), key="retro_time")
            if st.button("출석 등록 완료"):
                if "행사 없음" in selected: st.error("행사를 선택해 주세요.")
                elif not valid or not search_name.strip(): st.error("올바른 5자리 학번과 이름을 입력해 주세요.")
                elif "[마감]" in selected: st.error("마감된 행사입니다. 행사 상태를 확인해 주세요.")
                else:
                    event = clean_event(selected)
                    db_add_participant({"event_name":event,"student_id":search_id.strip(),"grade":grade,"class":class_num,"number":number,"name":search_name.strip(),"timestamp":f"{cdate} {ctime.strftime('%H:%M:%S')}","operator":st.session_state.staff_info})
                    db_add_log("참여자 등록", f"[{event}] {search_id} {search_name.strip()} 등록 완료", st.session_state.staff_info)
                    st.success(f"{search_name.strip()}님 출석 등록 완료!"); st.rerun()
        st.divider()
        st.markdown('<h3>금일 참여자 출석 현황 관리</h3>', unsafe_allow_html=True)
        today = now_seoul().strftime("%Y-%m-%d")
        todays = df_p[df_p['timestamp'].astype(str).str.startswith(today)] if not df_p.empty else pd.DataFrame()
        if todays.empty: st.info("오늘 등록된 출석 기록이 없습니다.")
        else:
            for _, row in todays.iterrows():
                with st.container(border=True):
                    info, delete_col, edit_col = st.columns([5, 1, 1])
                    info.markdown(f"**{row['event_name']}**  \n{row['student_id']} {row['name']} · {row['timestamp']}")
                    if delete_col.button("삭제", key=f"del_{row['id']}"):
                        db_delete_participant(int(row['id'])); db_add_log("데이터 삭제", f"참여자 ID {row['id']} 삭제됨", st.session_state.staff_info); st.rerun()
                    with edit_col.popover("수정"):
                        mod_name = st.text_input("이름", value=row['name'], key=f"edit_name_{row['id']}")
                        mod_sid = st.text_input("학번", value=str(row['student_id']), key=f"edit_sid_{row['id']}", max_chars=5)
                        if st.button("변경 저장", key=f"save_{row['id']}"):
                            ok, g, cl, num = parse_student_id(mod_sid)
                            if ok and mod_name.strip():
                                db_update_participant(int(row['id']), row['event_name'], mod_sid.strip(), g, cl, num, mod_name.strip())
                                db_add_log("데이터 수정", f"참여자 ID {row['id']} 수정 완료", st.session_state.staff_info); st.success("수정 완료"); st.rerun()
                            else: st.error("올바른 학번과 이름을 입력해 주세요.")

    with tab2:
        st.markdown('<div class="eyebrow">EVENT MANAGEMENT</div><h3>신규 행사 개설</h3>', unsafe_allow_html=True)
        create_col, list_col = st.columns([1, 1.7], gap="large")
        with create_col:
            with st.container(border=True):
                new_name = st.text_input("행사명", placeholder="예: 독서의 달 행사", key="new_event_name")
                new_type = st.selectbox("행사 종류", ["독서·독서토론", "도서관 이용 교육", "독서 문화 행사", "전시·캠페인", "대회·공모전", "기타"], key="new_event_type")
                new_description = st.text_area("행사 설명", placeholder="행사 내용, 참여 대상, 안내 사항 등을 적어 주세요.", key="new_event_description", height=110)
                if st.button("행사 만들기"):
                    if new_name.strip():
                        db_add_event(new_name.strip(), "진행 중", now_seoul().strftime("%Y-%m-%d %H:%M:%S"), new_type, new_description.strip())
                        db_add_log("행사 생성", f"신규 행사 [{new_name.strip()}] 생성", st.session_state.staff_info); st.success("행사가 개설되었습니다."); st.rerun()
                    else: st.warning("행사명을 입력해 주세요.")
        with list_col:
            st.markdown("### 개설된 행사 목록")
            events = db_get_events()
            if events.empty: st.info("개설된 행사가 없습니다.")
            for _, ev in events.iterrows():
                with st.container(border=True):
                    name_col, status_col, action_col, delete_col = st.columns([3, 1.2, 1.2, 1.1])
                    name_col.markdown(f"**{ev['name']}**")
                    name_col.caption(f"{ev.get('event_type', '기타')} · {ev.get('description', '')}")
                    status_col.markdown("🟢 진행 중" if ev['status'] == "진행 중" else "🔒 마감")
                    label = "마감하기" if ev['status'] == "진행 중" else "재개하기"
                    if action_col.button(label, key=f"toggle_{ev['id']}"):
                        new_status = "마감" if ev['status'] == "진행 중" else "진행 중"
                        db_update_event_status(int(ev['id']), new_status); db_add_log("행사 상태 변경", f"[{ev['name']}] -> {new_status}", st.session_state.staff_info); st.rerun()
                    if ev['status'] == "마감":
                        if delete_col.button("영구 삭제", key=f"delete_event_{ev['id']}"):
                            st.session_state[f"confirm_event_delete_{ev['id']}"] = True
                        if st.session_state.get(f"confirm_event_delete_{ev['id']}", False):
                            st.warning("행사와 연결된 모든 참여 기록이 삭제됩니다.")
                            yes, no = st.columns(2)
                            if yes.button("삭제 확인", key=f"confirm_yes_{ev['id']}"):
                                db_delete_event_and_records(int(ev['id']), ev['name']); db_add_log("행사 삭제", f"행사 [{ev['name']}] 영구 삭제 완료", st.session_state.staff_info); st.session_state.pop(f"confirm_event_delete_{ev['id']}", None); st.rerun()
                            if no.button("취소", key=f"confirm_no_{ev['id']}"):
                                st.session_state.pop(f"confirm_event_delete_{ev['id']}", None); st.rerun()

    with tab3:
        st.markdown('<div class="eyebrow">STATISTICS</div><h3>참여 통계</h3><p class="muted">주요 수치를 먼저 확인하고, 아래에서 행사별·학년별 현황을 살펴보세요.</p>', unsafe_allow_html=True)
        df_all = db_get_participants()
        if df_all.empty:
            st.info("통계를 표시할 참여 기록이 없습니다.")
        else:
            total_records = len(df_all)
            unique_students = df_all["student_id"].nunique()
            unique_events = df_all["event_name"].nunique()
            m1, m2, m3 = st.columns(3)
            m1.metric("총 참여 기록", f"{total_records:,}건")
            m2.metric("참여 학생 수", f"{unique_students:,}명")
            m3.metric("참여한 행사 수", f"{unique_events:,}개")
            event_counts = df_all["event_name"].value_counts().rename_axis("행사명").reset_index(name="참여 건수")
            grade_counts = df_all["grade"].value_counts().sort_index().rename_axis("학년").reset_index(name="참여 건수")
            monthly = df_all.copy()
            monthly["월"] = monthly["timestamp"].astype(str).str[:7]
            monthly_counts = monthly.groupby("월").size().reset_index(name="참여 건수").sort_values("월")
            st.markdown("#### 행사별 참여 현황")
            st.bar_chart(event_counts.set_index("행사명"), use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 학년별 참여 현황")
                st.bar_chart(grade_counts.set_index("학년"), use_container_width=True)
            with c2:
                st.markdown("#### 월별 참여 현황")
                st.line_chart(monthly_counts.set_index("월"), use_container_width=True)
            st.markdown("#### 통계 표")
            t1, t2 = st.tabs(["행사별", "학년별"])
            with t1: st.dataframe(event_counts, use_container_width=True, hide_index=True)
            with t2: st.dataframe(grade_counts, use_container_width=True, hide_index=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_all.to_excel(writer, sheet_name="참여 기록", index=False)
                event_counts.to_excel(writer, sheet_name="행사별 통계", index=False)
                grade_counts.to_excel(writer, sheet_name="학년별 통계", index=False)
                monthly_counts.to_excel(writer, sheet_name="월별 통계", index=False)
            st.download_button("통계 엑셀 파일 다운로드", data=output.getvalue(), file_name=f"행사_참여_통계_{now_seoul().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab4:
        st.markdown('<div class="eyebrow">ACTIVITY LOG</div><h3>처리 이력</h3><p class="muted">필터로 필요한 기록만 확인하거나 선택한 기록만 삭제할 수 있습니다.</p>', unsafe_allow_html=True)
        logs = db_get_logs()
        if logs.empty:
            st.info("기록된 처리 이력이 없습니다.")
        else:
            f1, f2, f3 = st.columns(3)
            categories = sorted(logs["category"].dropna().astype(str).unique().tolist())
            operators = sorted(logs["operator"].dropna().astype(str).unique().tolist())
            with f1: chosen_categories = st.multiselect("분류", categories, default=[], key="log_categories")
            with f2: chosen_operators = st.multiselect("담당자", operators, default=[], key="log_operators")
            with f3: log_query = st.text_input("내용 검색", placeholder="내용이나 담당자 검색", key="log_query")
            use_date_filter = st.checkbox("날짜 범위로 좁혀 보기", key="use_log_date_filter")
            date_from = date_to = None
            if use_date_filter:
                d1, d2 = st.columns(2)
                with d1: date_from = st.date_input("시작 날짜", value=now_seoul().date(), key="log_date_from")
                with d2: date_to = st.date_input("종료 날짜", value=now_seoul().date(), key="log_date_to")
            shown = logs.copy()
            if chosen_categories: shown = shown[shown["category"].astype(str).isin(chosen_categories)]
            if chosen_operators: shown = shown[shown["operator"].astype(str).isin(chosen_operators)]
            if log_query.strip():
                mask = shown.astype(str).apply(lambda col: col.str.contains(log_query.strip(), case=False, na=False)).any(axis=1)
                shown = shown[mask]
            if date_from: shown = shown[shown["timestamp"].astype(str).str[:10] >= date_from.strftime("%Y-%m-%d")]
            if date_to: shown = shown[shown["timestamp"].astype(str).str[:10] <= date_to.strftime("%Y-%m-%d")]
            st.caption(f"필터 결과 {len(shown):,}건 / 전체 {len(logs):,}건")
            st.dataframe(shown, use_container_width=True, hide_index=True)
            options = {f"#{int(row['id'])} · {row['timestamp']} · {row['category']} · {row['detail'][:45]}": int(row['id']) for _, row in shown.iterrows()}
            with st.expander("선택한 처리 이력 삭제"):
                if options:
                    selected_log_labels = st.multiselect("삭제할 기록 선택", list(options.keys()), key="selected_log_ids")
                    st.warning("선택한 처리 이력만 삭제됩니다. 삭제 후에는 복구할 수 없습니다.")
                    if st.button("선택한 기록 삭제", type="primary", disabled=not selected_log_labels):
                        ids = [options[label] for label in selected_log_labels]
                        with get_db_connection() as conn:
                            conn.executemany("DELETE FROM logs WHERE id = ?", [(log_id,) for log_id in ids])
                        st.success(f"처리 이력 {len(ids)}건을 삭제했습니다.")
                        st.rerun()
                else:
                    st.caption("삭제할 기록이 없습니다.")
            with st.expander("모든 처리 이력 삭제"):
                st.warning("모든 처리 이력이 삭제됩니다. 이 작업은 되돌릴 수 없습니다.")
                confirm = st.checkbox("전체 삭제를 확인했습니다.", key="confirm_clear_logs")
                if st.button("모든 처리 이력 삭제", disabled=not confirm):
                    db_clear_logs(); st.success("처리 이력을 삭제했습니다."); st.rerun()

    with tab5:
        st.markdown('<div class="eyebrow">DATA MANAGEMENT</div><h3>데이터 백업 및 복원</h3><p class="muted">현재 SQLite 데이터베이스 파일을 내려받아 백업할 수 있습니다.</p>', unsafe_allow_html=True)
        if DB_PATH.exists():
            st.download_button("데이터베이스 백업 (.db 다운로드)", data=DB_PATH.read_bytes(), file_name=f"library_backup_{now_seoul().strftime('%Y%m%d_%H%M%S')}.db", mime="application/octet-stream")
        else: st.error("데이터베이스 파일을 찾을 수 없습니다.")
        st.info("복원은 백업 파일을 안전한 위치에 보관한 뒤, 앱을 중지하고 기존 library_system.db를 교체하는 방식으로 진행하세요. 운영 중인 DB를 덮어쓰면 데이터가 손실될 수 있습니다.")

st.markdown('<div style="text-align:center;color:#a0a8b8;font-size:12px;padding:24px 0 4px;letter-spacing:1px">SONGCHEON EVENT SYSTEM · GLASS UI</div>', unsafe_allow_html=True)
