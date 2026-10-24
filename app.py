import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from io import BytesIO
import sqlite3
from pathlib import Path
import tempfile
import os
import html

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
        cur.execute('''CREATE TABLE IF NOT EXISTS deleted_participants (
            archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER NOT NULL, event_name TEXT NOT NULL,
            student_id TEXT NOT NULL, grade INTEGER NOT NULL, class INTEGER NOT NULL,
            number INTEGER NOT NULL, name TEXT NOT NULL, timestamp TEXT NOT NULL,
            operator TEXT NOT NULL, deleted_at TEXT NOT NULL, deleted_by TEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS deleted_logs (
            archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
            category TEXT NOT NULL, detail TEXT NOT NULL, operator TEXT NOT NULL,
            deleted_at TEXT NOT NULL, deleted_by TEXT NOT NULL)''')
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

def db_update_event_details(event_id, old_name, new_name, event_type, description):
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE events SET name=?, event_type=?, description=? WHERE id=?",
            (new_name, event_type, description, event_id),
        )
        if old_name != new_name:
            conn.execute("UPDATE participants SET event_name=? WHERE event_name=?", (new_name, old_name))
            conn.execute("UPDATE deleted_participants SET event_name=? WHERE event_name=?", (new_name, old_name))

def db_delete_event_and_records(event_id, event_name, deleted_by="관리자"):
    with get_db_connection() as conn:
        participant_ids = [row[0] for row in conn.execute(
            "SELECT id FROM participants WHERE event_name=?", (event_name,)
        ).fetchall()]
    db_archive_and_delete_participants(participant_ids, deleted_by)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))

def db_add_participant(data):
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO participants
            (event_name,student_id,grade,class,number,name,timestamp,operator)
            VALUES (?,?,?,?,?,?,?,?)''', (data['event_name'],data['student_id'],data['grade'],data['class'],data['number'],data['name'],data['timestamp'],data['operator']))

def db_count_participant_on_date(event_name, student_id, day):
    day_text = day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)[:10]
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM participants WHERE event_name=? AND student_id=? AND timestamp LIKE ?",
            (str(event_name).strip(), str(student_id).strip(), f"{day_text}%"),
        ).fetchone()
    return int(row[0] or 0)

def db_archive_and_delete_participants(part_ids, deleted_by):
    ids = sorted({int(x) for x in part_ids})
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    deleted_at = now_seoul().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        rows = conn.execute(
            f"SELECT id,event_name,student_id,grade,class,number,name,timestamp,operator FROM participants WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        conn.executemany("""INSERT INTO deleted_participants
            (original_id,event_name,student_id,grade,class,number,name,timestamp,operator,deleted_at,deleted_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [(r[0], *r[1:], deleted_at, deleted_by) for r in rows])
        conn.executemany("DELETE FROM participants WHERE id=?", [(r[0],) for r in rows])
    return len(rows)

def db_restore_archived_participant(archive_id, restored_by):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM deleted_participants WHERE archive_id=?", (int(archive_id),)).fetchone()
        if row is None:
            return False, "복구할 기록을 찾을 수 없습니다."
        conn.execute("""INSERT INTO participants (event_name,student_id,grade,class,number,name,timestamp,operator)
            VALUES (?,?,?,?,?,?,?,?)""", (row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9]))
        conn.execute("DELETE FROM deleted_participants WHERE archive_id=?", (int(archive_id),))
    db_add_log("참여 기록 복구", f"보관 기록 #{archive_id} 복구 완료", restored_by)
    return True, "기록을 복구했습니다."

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

def db_archive_and_delete_logs(log_ids, deleted_by):
    ids = sorted({int(x) for x in log_ids})
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    deleted_at = now_seoul().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        rows = conn.execute(
            f"SELECT id,timestamp,category,detail,operator FROM logs WHERE id IN ({placeholders})", ids
        ).fetchall()
        conn.executemany("""INSERT INTO deleted_logs
            (original_id,timestamp,category,detail,operator,deleted_at,deleted_by)
            VALUES (?,?,?,?,?,?,?)""",
            [(r[0], r[1], r[2], r[3], r[4], deleted_at, deleted_by) for r in rows])
        conn.executemany("DELETE FROM logs WHERE id=?", [(r[0],) for r in rows])
    return len(rows)

def db_restore_archived_log(archive_id, restored_by):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM deleted_logs WHERE archive_id=?", (int(archive_id),)).fetchone()
        if row is None:
            return False, "복구할 처리 이력을 찾을 수 없습니다."
        conn.execute("INSERT INTO logs (timestamp,category,detail,operator) VALUES (?,?,?,?)", (row[2], row[3], row[4], row[5]))
        conn.execute("DELETE FROM deleted_logs WHERE archive_id=?", (int(archive_id),))
    db_add_log("처리 이력 복구", f"보관 이력 #{archive_id} 복구 완료", restored_by)
    return True, "처리 이력을 복구했습니다."

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
.stButton > button, .stDownloadButton > button { width:100%; min-height:46px; border-radius:15px; border:1px solid rgba(255,255,255,.9); background:linear-gradient(135deg,#3182F6,#1B64DA); color:#fff; font-weight:750; box-shadow:0 8px 20px rgba(49,130,246,.22); transition:transform .18s ease,box-shadow .18s ease,filter .18s ease; }
.stButton > button p, .stButton > button span, .stDownloadButton > button p { color:#fff !important; font-weight:750; }
.stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-1px); box-shadow:0 12px 26px rgba(49,130,246,.30); border-color:rgba(255,255,255,.95); filter:saturate(1.08); }
.stButton > button:focus, .stDownloadButton > button:focus { outline:2px solid rgba(49,130,246,.25); outline-offset:2px; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input, [data-testid="stTimeInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-radius:13px !important; border-color:#dfe4ef !important; background:rgba(255,255,255,.82) !important; min-height:43px; }
[data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus { border-color:#3182F6 !important; box-shadow:0 0 0 2px rgba(49,130,246,.12) !important; }
label, [data-testid="stWidgetLabel"] p { color:#424a5b !important; font-weight:650 !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:7px; padding:7px; border:1px solid rgba(255,255,255,.95); border-radius:20px; background:rgba(255,255,255,.58); }
[data-testid="stTabs"] button[role="tab"] { border-radius:14px; padding:11px 15px; color:#626b7b; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:#fff; box-shadow:0 5px 15px rgba(70,84,120,.12); color:#1B64DA; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background:transparent; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border:1px solid #e6eaf2; border-radius:16px; overflow:hidden; }
[data-testid="stAlert"] { border-radius:14px; }
[data-testid="stExpander"] { border:1px solid #e2e7f0; border-radius:15px; background:rgba(255,255,255,.56); }
hr { border-color:rgba(125,139,165,.18) !important; }
h1,h2,h3,h4 { color:#20232b; letter-spacing:-.65px; }
[data-testid="stTextInput"] input { min-height:48px !important; font-size:16px !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div { min-height:48px !important; font-size:16px !important; }
.stMetric { background:rgba(255,255,255,.78); border:1px solid rgba(255,255,255,.95); border-radius:20px; padding:18px 20px; box-shadow:0 10px 26px rgba(51,65,97,.06); }
</style>''', unsafe_allow_html=True)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

theme_spacer, theme_control = st.columns([7, 1.5], gap="small")
with theme_control:
    st.toggle("🌙 다크 모드", key="dark_mode", help="밝은 화면과 어두운 화면을 전환합니다.")

if st.session_state.dark_mode:
    st.markdown(r'''<style>
    :root { color-scheme: dark; --ink:#edf2fa; --muted:#a8b3c5; --line:rgba(170,185,210,.20); }
    html, body, [data-testid="stAppViewContainer"], .stApp {
      color:#edf2fa !important;
      background:radial-gradient(ellipse at 15% 28%,rgba(52,75,135,.20),transparent 34%),
                 radial-gradient(ellipse at 82% 42%,rgba(38,83,132,.18),transparent 34%),
                 linear-gradient(135deg,#111722 0%,#151c28 48%,#101722 100%) !important;
    }
    [data-testid="stHeader"] { background:rgba(17,23,34,.88) !important; }
    [data-testid="stAppViewContainer"] section, [data-testid="stMain"] { color:#edf2fa !important; }
    .brandbar,.hero-card,.glass-card,[data-testid="stExpander"],
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
      background:rgba(31,41,57,.90) !important; border-color:rgba(170,185,210,.18) !important;
      box-shadow:0 12px 34px rgba(0,0,0,.20) !important;
    }
    .brandname,.hero-title,.section-title,h1,h2,h3,h4,p,li,label,
    [data-testid="stWidgetLabel"] p,[data-testid="stMarkdownContainer"] { color:#edf2fa; }
    .branddesc,.hero-subtitle,.muted { color:#a8b3c5 !important; }
    .pill { color:#a9caff !important; background:rgba(49,130,246,.16) !important; border-color:rgba(115,164,255,.30) !important; }
    [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,[data-testid="stTimeInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stTextArea"] textarea {
      color:#edf2fa !important; background:#202a3a !important; border-color:#3a4960 !important;
      -webkit-text-fill-color:#edf2fa !important;
    }
    input::placeholder,textarea::placeholder { color:#a8b3c5 !important; -webkit-text-fill-color:#a8b3c5 !important; }
    [data-testid="stTabs"] button[role="tab"] { color:#c1cada !important; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:#29374b !important; color:#a9caff !important; }
    [data-testid="stMetric"] { background:#202a3a !important; border-color:#354258 !important; }
    [data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stMetricDelta"] { color:#edf2fa !important; }
    [data-testid="stDataFrame"],[data-testid="stTable"] { border-color:#354258 !important; }
    [data-testid="stAlert"] p,[data-testid="stExpander"] summary,[data-testid="stExpander"] summary p { color:#edf2fa !important; }
    [data-baseweb="popover"] > div,[data-baseweb="menu"] { background:#202a3a !important; }
    [role="option"],[role="listbox"] { color:#edf2fa !important; }
    hr { border-color:rgba(170,185,210,.20) !important; } a { color:#8dbaff !important; }
    </style>''', unsafe_allow_html=True)

st.markdown('''<div class="brandbar"><div class="brandname">Songcheon <span style="color:#3182F6">Lib Tech</span></div><div class="branddesc">인천송천고등학교 · 행사 관리 시스템</div></div>''', unsafe_allow_html=True)

def parse_student_id(std_id):
    value = str(std_id).strip()
    if len(value) == 5 and value.isdigit():
        return True, int(value[0]), int(value[1:3]), int(value[3:5])
    return False, None, None, None

def find_student_name(student_id):
    sid = str(student_id).strip()
    if len(sid) != 5 or not sid.isdigit():
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

try:
    saved_role = st.query_params.get("role", "")
except Exception:
    saved_role = ""
if st.session_state.user_role is None and saved_role in ("staff", "participant"):
    st.session_state.user_role = saved_role
    if saved_role == "staff" and not st.session_state.staff_info:
        st.session_state.staff_info = "관리자"

def persist_login(role, staff_info=None):
    try:
        st.query_params["role"] = role
    except Exception:
        pass

def clear_persisted_login():
    st.session_state.logout_requested = True
    st.session_state.user_role = None
    st.session_state.staff_info = None
    try:
        st.query_params.clear()
    except Exception:
        try:
            del st.query_params["role"]
        except Exception:
            pass

# ------------------------------------------------------------
# Main landing screen
# ------------------------------------------------------------
if st.session_state.user_role is None:
    spacer1, main, spacer2 = st.columns([1, 1.35, 1])
    with main:
        st.markdown('''<div class="hero-card"><div class="eyebrow">EVENT MANAGEMENT</div><div class="hero-title">인천송천고 도서관</div><p class="hero-subtitle">행사 참여 등록부터 통합 데이터 관리까지<br>한곳에서 간편하게 관리하세요.</p><span class="pill">SONGCHEON EVENT SYSTEM</span></div>''', unsafe_allow_html=True)
        st.write("")
        if st.button("학생 · 일반 참여자 등록", use_container_width=True):
            st.session_state.logout_requested = False; st.session_state.user_role = 'participant'; persist_login('participant'); st.rerun()
        if st.button("사서교사 · 도서부원 관리자 로그인", use_container_width=True):
            st.session_state.logout_requested = False; st.session_state.user_role = 'staff_login'; st.rerun()

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
                    st.session_state.logout_requested = False
                    st.session_state.user_role = 'staff'
                    persist_login('staff', st.session_state.staff_info)
                    db_add_log("시스템 접속", f"{st.session_state.staff_info} 접속함", st.session_state.staff_info)
                    st.rerun()
        with c2:
            if st.button("메인으로", key="login_home"):
                st.session_state.user_role = None; clear_persisted_login(); st.rerun()

# ------------------------------------------------------------
# Participant registration
# ------------------------------------------------------------
elif st.session_state.user_role == 'participant':
    if st.session_state.pop('clear_participant_inputs', False):
        st.session_state['participant_sid'] = ''
        st.session_state['participant_name'] = ''
    top1, top2 = st.columns([5, 1])
    with top1: st.markdown('<div class="eyebrow">EVENT CHECK-IN</div><div class="section-title">도서관 행사 참여 등록</div>', unsafe_allow_html=True)
    with top2:
        if st.button("메인으로", key="participant_home"):
            st.session_state.user_role = None; clear_persisted_login(); st.rerun()
    _, formcol, _ = st.columns([0.7, 2.2, 0.7])
    with formcol:
        st.markdown('<div class="glass-card"><b>참여 정보를 입력해 주세요</b><p class="muted">행사를 선택하고 학번을 입력하면 등록됩니다.</p></div>', unsafe_allow_html=True)
        df_events = db_get_events()
        selected = st.selectbox("참여할 행사", event_options(df_events), key="participant_event")
        sid = st.text_input("학번 (5자리)", placeholder="예: 10101", max_chars=5, key="participant_sid", on_change=lambda: st.session_state.update({"participant_name": find_student_name(st.session_state.get("participant_sid", ""))}))
        pname = st.text_input("이름", placeholder="이름 입력", key="participant_name")
        participant_day = now_seoul().date()
        pending_participant = (clean_event(selected), sid.strip(), participant_day.isoformat())
        is_pending_participant = st.session_state.get("pending_participant_duplicate") == pending_participant
        submit_participant = st.button("참여 등록하기", key="participant_submit")
        confirm_participant = False
        cancel_participant = False
        if is_pending_participant:
            st.warning("⚠️ 오늘 이 행사에 이미 등록한 기록이 있습니다. 중복 등록하시겠습니까?")
            cc1, cc2 = st.columns(2)
            with cc1: confirm_participant = st.button("네, 중복 등록", key="participant_confirm_duplicate", use_container_width=True)
            with cc2: cancel_participant = st.button("아니요, 취소", key="participant_cancel_duplicate", use_container_width=True)
        if cancel_participant:
            st.session_state.pop("pending_participant_duplicate", None)
            st.info("중복 등록을 취소했습니다.")
            st.rerun()
        if submit_participant or confirm_participant:
            valid, grade, class_num, number = parse_student_id(sid)
            if "행사 없음" in selected: st.error("등록 가능한 행사가 없습니다.")
            elif "[마감]" in selected: st.error("마감된 행사입니다.")
            elif not valid: st.error("올바른 5자리 학번을 입력해 주세요.")
            else:
                event = clean_event(selected)
                today_count = db_count_participant_on_date(event, sid.strip(), participant_day)
                if today_count > 0 and not confirm_participant:
                    st.session_state["pending_participant_duplicate"] = (event, sid.strip(), participant_day.isoformat())
                    st.rerun()
                else:
                    registered_name = pname.strip() or find_student_name(sid.strip()) or "이름 미입력"
                    db_add_participant({"event_name":event,"student_id":sid.strip(),"grade":grade,"class":class_num,"number":number,"name":registered_name,"timestamp":now_seoul().strftime("%Y-%m-%d %H:%M:%S"),"operator":"참여자 본인"})
                    db_add_log("참여자 등록", f"[{event}] {sid} {registered_name} 등록 완료", "참여자 본인")
                    st.session_state.pop("pending_participant_duplicate", None)
                    st.session_state['clear_participant_inputs'] = True
                    st.session_state["participant_registration_flash"] = f"학번 {sid} 등록이 완료되었습니다!"
                    st.rerun()
        if st.session_state.get("participant_registration_flash"):
            st.success(st.session_state.pop("participant_registration_flash"))

# ------------------------------------------------------------
# Staff administration dashboard
# ------------------------------------------------------------
elif st.session_state.user_role == 'staff':
    h1, h2 = st.columns([5, 1])
    with h1:
        st.markdown(f'<div class="eyebrow">ADMIN WORKSPACE</div><div class="section-title">행사 관리 시스템</div><p class="muted">접속 계정: {st.session_state.staff_info}</p>', unsafe_allow_html=True)
    with h2:
        if st.button("로그아웃"):
            st.session_state.user_role = None; st.session_state.staff_info = None; clear_persisted_login(); st.rerun()

    overview_p = db_get_participants()
    overview_e = db_get_events()
    today_key = now_seoul().strftime("%Y-%m-%d")
    today_count = int(overview_p["timestamp"].astype(str).str.startswith(today_key).sum()) if not overview_p.empty else 0
    active_events = int((overview_e["status"] == "진행 중").sum()) if not overview_e.empty else 0
    overview_cols = st.columns([1, 1, 1, 1], gap="small")
    overview_cols[0].metric("오늘 등록", f"{today_count:,}건")
    overview_cols[1].metric("전체 기록", f"{len(overview_p):,}건")
    overview_cols[2].metric("진행 행사", f"{active_events:,}개")
    overview_cols[3].metric("참여 학생", f"{overview_p['student_id'].nunique():,}명" if not overview_p.empty else "0명")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["참여 등록", "행사 관리", "통계 대시보드", "처리 이력", "백업/복원"])

    with tab1:
        # PPT 와이어프레임 구조에 따른 정확한 도형/컴포넌트 배치 적용
        df_e = db_get_events()
        if st.session_state.pop("clear_staff_search_inputs", False):
            st.session_state["staff_search_id"] = ""
            st.session_state["staff_search_name"] = ""

        # 상단 행: [행사 입력] [날짜 시간 선택 입력] [등록 버튼(enter키)]
        top_ctrl1, top_ctrl2, top_ctrl3 = st.columns([1.5, 1.4, 1.1], gap="small")
        with top_ctrl1:
            selected = st.selectbox("행사 입력", event_options(df_e), key="staff_event")
        with top_ctrl2:
            dt_col1, dt_col2 = st.columns(2, gap="small")
            with dt_col1:
                cdate = st.date_input("날짜", value=now_seoul().date(), key="retro_date")
            with dt_col2:
                ctime = st.time_input("시간", value=now_seoul().time().replace(tzinfo=None, microsecond=0), key="retro_time")
        with top_ctrl3:
            st.write("") # 수직 정렬 맞춤용 공백
            st.write("")
            register_clicked = st.button("등록 버튼 (Enter)", key="staff_attendance_submit", type="primary", use_container_width=True)

        st.divider()

        # 하단 영역: 좌측([참여자 정보] + [학번 입력] + [이름 입력] + [검색/초기화 버튼]) / 우측([행사 참여 이력])
        left_area, right_area = st.columns([1, 1.6], gap="large")

        with left_area:
            st.markdown("### 참여자 정보 (학번, 이름)")
            search_id = st.text_input("학번 입력", key="staff_search_id", placeholder="학번 5자리", max_chars=5, on_change=fill_staff_student_name)
            search_name = st.text_input("이름 입력", key="staff_search_name", placeholder="학생 이름")
            
            btn_col1, btn_col2 = st.columns(2, gap="small")
            with btn_col1:
                search_clicked = st.button("검색 버튼", key="staff_student_search", use_container_width=True, type="primary")
            with btn_col2:
                clear_clicked = st.button("초기화 버튼 (Esc)", key="staff_student_clear", use_container_width=True)

            # ESC 키 바인딩 (초기화)
            st.components.v1.html("""<script>
            (function(){
              try {
                const doc = window.parent.document;
                if (doc.__songcheonEscClearBound) return;
                doc.__songcheonEscClearBound = true;
                doc.addEventListener('keydown', function(e) {
                  if (e.key !== 'Escape') return;
                  const buttons = Array.from(doc.querySelectorAll('button'));
                  const clear = buttons.find(b => (b.innerText || '').trim().includes('초기화 버튼'));
                  if (clear) { e.preventDefault(); clear.click(); }
                }, true);
              } catch(e) {}
            })();
            </script>""", height=0)

            if clear_clicked:
                st.session_state["staff_search_id"] = ""
                st.session_state["staff_search_name"] = ""
                st.session_state.pop("pending_admin_duplicate", None)
                st.rerun()

            # 검색 또는 입력된 학번/이름 기준으로 정보 및 이력 매칭
            active_sid = st.session_state.get("staff_search_id", "").strip()
            active_name = st.session_state.get("staff_search_name", "").strip()
            valid_active, _, _, _ = parse_student_id(active_sid)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if valid_active and active_name:
                st.markdown(
                    f"""
                    <div class="glass-card" style="padding:16px 20px;">
                      <div style="font-size:13px;color:#737b8c;font-weight:700">조회된 참여자</div>
                      <div style="font-size:17px;font-weight:800;margin-top:6px">{active_sid} &nbsp;·&nbsp; {active_name}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="glass-card" style="padding:16px 20px;"><span class="muted">학번과 이름을 입력한 뒤 검색하면 여기에 표시됩니다.</span></div>',
                    unsafe_allow_html=True
                )

        with right_area:
            st.markdown("### 행사 참여 이력")
            if valid_active and active_name:
                latest_participants = db_get_participants()
                history = latest_participants[
                    (latest_participants["student_id"].astype(str).str.strip() == active_sid) &
                    (latest_participants["name"].astype(str).str.strip() == active_name)
                ].copy() if not latest_participants.empty else pd.DataFrame()

                if history.empty:
                    st.info("이 참여자의 과거 행사 참여 이력이 없습니다.")
                else:
                    history = history.sort_values("timestamp", ascending=False)
                    st.dataframe(
                        history[["event_name", "timestamp", "operator"]].rename(
                            columns={"event_name":"행사명", "timestamp":"참여 일시", "operator":"등록자"}
                        ), use_container_width=True, hide_index=True, height=220
                    )
            else:
                st.markdown(
                    '<div class="glass-card" style="min-height:220px;display:flex;align-items:center;justify-content:center"><span class="muted">참여자를 검색하면 상세 이력이 여기에 표시됩니다.</span></div>',
                    unsafe_allow_html=True
                )

        # 등록 처리 로직 (중복 체크 및 새로고침 없는 토스트 알림)
        pending_admin = (clean_event(selected), active_sid, cdate.isoformat())
        is_pending_admin = st.session_state.get("pending_admin_duplicate") == pending_admin
        confirm_admin = False
        cancel_admin = False

        if is_pending_admin:
            st.warning("⚠️ 선택한 날짜에 해당 학생의 행사 참여 기록이 이미 있습니다. 중복 등록하시겠습니까?")
            cc1, cc2 = st.columns(2)
            with cc1: confirm_admin = st.button("네, 중복 등록", key="staff_attendance_confirm_duplicate", use_container_width=True)
            with cc2: cancel_admin = st.button("아니요, 취소", key="staff_attendance_cancel_duplicate", use_container_width=True)
        if cancel_admin:
            st.session_state.pop("pending_admin_duplicate", None)
            st.info("중복 등록을 취소했습니다.")
            st.rerun()

        if register_clicked or confirm_admin:
            valid, grade, class_num, number = parse_student_id(active_sid)
            if "행사 없음" in selected:
                st.error("행사를 선택해 주세요.")
            elif "[마감]" in selected:
                st.error("마감된 행사입니다.")
            elif not valid or not active_name:
                st.error("올바른 5자리 학번과 이름을 모두 입력해 주세요.")
            else:
                event = clean_event(selected)
                same_day_count = db_count_participant_on_date(event, active_sid, cdate)
                if same_day_count > 0 and not confirm_admin:
                    st.session_state["pending_admin_duplicate"] = (event, active_sid, cdate.isoformat())
                    st.rerun()
                else:
                    db_add_participant({"event_name":event,"student_id":active_sid,"grade":grade,"class":class_num,"number":number,"name":active_name,"timestamp":f"{cdate} {ctime.strftime('%H:%M:%S')}","operator":st.session_state.staff_info})
                    db_add_log("참여자 등록", f"[{event}] {active_sid} {active_name} 등록 완료", st.session_state.staff_info)
                    st.session_state.pop("pending_admin_duplicate", None)
                    # 입력칸 초기화 및 상단 토스트 팝업 띄우기
                    st.session_state["staff_search_id"] = ""
                    st.session_state["staff_search_name"] = ""
                    st.toast(f"✅ {active_name} 학생의 {event} 참여 등록이 완료되었습니다!", icon="🎉")
                    st.rerun()

        st.divider()
        st.markdown('<h3>참여 기록 관리</h3><p class="muted">오늘 기록 및 전체 참여 기록을 검색하고 관리할 수 있습니다.</p>', unsafe_allow_html=True)
        all_records = db_get_participants()
        if all_records.empty:
            st.info("참여 기록이 없습니다.")
        else:
            r1, r2, r3 = st.columns([1.2, 1.2, 1.6])
            with r1: record_scope = st.selectbox("기록 범위", ["오늘", "전체 기록"], key="record_scope")
            with r2:
                record_event_options = ["전체 행사"] + sorted(all_records["event_name"].dropna().astype(str).unique().tolist())
                record_event = st.selectbox("행사", record_event_options, key="record_event_filter")
            with r3: record_query = st.text_input("학번 또는 이름 검색", key="record_search", placeholder="학번/이름 검색")
            record_view = all_records.copy()
            if record_scope == "오늘":
                record_view = record_view[record_view["timestamp"].astype(str).str.startswith(now_seoul().strftime("%Y-%m-%d"))]
            if record_event != "전체 행사":
                record_view = record_view[record_view["event_name"].astype(str) == record_event]
            if record_query.strip():
                q = record_query.strip()
                record_view = record_view[record_view["student_id"].astype(str).str.contains(q, case=False, na=False) | record_view["name"].astype(str).str.contains(q, case=False, na=False)]
            st.caption(f"검색 결과 {len(record_view):,}건")
            if record_view.empty:
                st.info("조건에 맞는 기록이 없습니다.")
            else:
                st.dataframe(record_view[["id", "event_name", "student_id", "name", "timestamp", "operator"]], use_container_width=True, hide_index=True)
                record_labels = {f"#{int(row['id'])} · {row['event_name']} · {row['student_id']} {row['name']} · {row['timestamp']}": int(row['id']) for _, row in record_view.iterrows()}
                selected_record_labels = st.multiselect("삭제할 기록 선택", list(record_labels.keys()), key="bulk_delete_records")
                confirm_bulk_delete = st.checkbox("선택한 기록 삭제에 동의합니다.", key="confirm_bulk_delete_records", disabled=not selected_record_labels)
                if st.button("선택한 참여 기록 삭제", type="primary", disabled=(not selected_record_labels or not confirm_bulk_delete), key="bulk_delete_records_btn"):
                    ids_to_delete = [record_labels[label] for label in selected_record_labels]
                    deleted_count = db_archive_and_delete_participants(ids_to_delete, st.session_state.staff_info)
                    db_add_log("데이터 삭제", f"참여 기록 {deleted_count}건 삭제", st.session_state.staff_info)
                    st.success(f"참여 기록 {deleted_count}건을 삭제했습니다.")
                    st.rerun()

    with tab2:
        st.markdown('<div class="eyebrow">EVENT MANAGEMENT</div><h3>신규 행사 개설</h3>', unsafe_allow_html=True)
        create_col, list_col = st.columns([1, 1.7], gap="large")
        with create_col:
            with st.container(border=True):
                new_name = st.text_input("행사명", placeholder="예: 독서의 달 행사", key="new_event_name")
                new_type = st.selectbox("행사 종류", ["독서·독서토론", "도서관 이용 교육", "독서 문화 행사", "전시·캠페인", "대회·공모전", "기타"], key="new_event_type")
                new_description = st.text_area("행사 설명", placeholder="행사 내용 안내", key="new_event_description", height=110)
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
                            db_delete_event_and_records(int(ev['id']), ev['name'], st.session_state.staff_info)
                            db_add_log("행사 삭제", f"행사 [{ev['name']}] 삭제", st.session_state.staff_info)
                            st.success("행사를 삭제했습니다.")
                            st.rerun()

    with tab3:
        st.markdown('<div class="eyebrow">STATISTICS</div><h3>참여 통계</h3>', unsafe_allow_html=True)
        df_all = db_get_participants()
        if df_all.empty:
            st.info("통계를 표시할 참여 기록이 없습니다.")
        else:
            event_counts = df_all["event_name"].value_counts().rename_axis("행사명").reset_index(name="참여 건수")
            grade_counts = df_all["grade"].value_counts().sort_index().rename_axis("학년").reset_index(name="참여 건수")
            st.markdown("#### 행사별 참여 현황")
            st.bar_chart(event_counts.set_index("행사명"), use_container_width=True)
            st.markdown("#### 학년별 참여 현황")
            st.bar_chart(grade_counts.set_index("학년"), use_container_width=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_all.to_excel(writer, sheet_name="전체 참여 기록", index=False)
                event_counts.to_excel(writer, sheet_name="행사별 통계", index=False)
            st.download_button("전체 결과 엑셀 다운로드", data=output.getvalue(), file_name=f"행사_참여_통계_{now_seoul().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab4:
        st.markdown('<div class="eyebrow">ACTIVITY LOG</div><h3>처리 이력</h3>', unsafe_allow_html=True)
        logs = db_get_logs()
        if logs.empty:
            st.info("기록된 처리 이력이 없습니다.")
        else:
            st.dataframe(logs, use_container_width=True, hide_index=True)
            if st.button("모든 처리 이력 삭제"):
                db_clear_logs()
                st.success("처리 이력을 모두 삭제했습니다.")
                st.rerun()

    with tab5:
        st.markdown('<div class="eyebrow">DATA MANAGEMENT</div><h3>데이터 백업 및 복원</h3>', unsafe_allow_html=True)
        if DB_PATH.exists():
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button("현재 데이터베이스 백업 (.db)", data=db_bytes, file_name=f"library_backup_{now_seoul().strftime('%Y%m%d')}.db", mime="application/octet-stream")

st.markdown('<div style="text-align:center;color:#a0a8b8;font-size:12px;padding:24px 0 4px;letter-spacing:1px">SONGCHEON EVENT SYSTEM · GLASS UI</div>', unsafe_allow_html=True)
