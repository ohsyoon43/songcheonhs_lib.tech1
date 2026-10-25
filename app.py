import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from io import BytesIO
import sqlite3
from pathlib import Path
import tempfile
import os

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

def db_update_event_details(event_id, old_name, new_name, event_type, description):
    """행사 정보를 수정하고, 행사명 변경 시 연결된 참여/보관 기록도 함께 갱신한다."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE events SET name=?, event_type=?, description=? WHERE id=?",
            (new_name, event_type, description, event_id),
        )
        if old_name != new_name:
            conn.execute("UPDATE participants SET event_name=? WHERE event_name=?", (new_name, old_name))
            conn.execute("UPDATE deleted_participants SET event_name=? WHERE event_name=?", (new_name, old_name))

def db_delete_event_and_records(event_id, event_name, deleted_by="관리자"):
    # 행사 삭제 시 연결된 참여 기록도 복구 보관함에 먼저 보관한다.
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

def db_participant_exists(event_name, student_id, exclude_id=None):
    """기존 호환용: 행사와 학번이 일치하는 참여 기록이 있는지 확인한다."""
    query = "SELECT 1 FROM participants WHERE event_name=? AND student_id=?"
    params = [str(event_name).strip(), str(student_id).strip()]
    if exclude_id is not None:
        query += " AND id<>?"
        params.append(int(exclude_id))
    query += " LIMIT 1"
    with get_db_connection() as conn:
        return conn.execute(query, params).fetchone() is not None

def db_count_participant_on_date(event_name, student_id, day):
    """해당 날짜에 같은 학생이 같은 행사에 등록한 횟수."""
    day_text = day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)[:10]
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM participants WHERE event_name=? AND student_id=? AND timestamp LIKE ?",
            (str(event_name).strip(), str(student_id).strip(), f"{day_text}%"),
        ).fetchone()
    return int(row[0] or 0)

def db_archive_and_delete_participants(part_ids, deleted_by):
    """Move selected participation rows to a recovery table before deleting them."""
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
        # row: archive_id, original_id, event_name, student_id, grade, class, number, name, timestamp, operator, deleted_at, deleted_by
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
    """Archive selected log rows before removing them from the active log list."""
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
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { width:100%; min-height:46px; border-radius:15px; border:1px solid rgba(255,255,255,.9); background:linear-gradient(135deg,#3182F6,#1B64DA); color:#fff; font-weight:750; box-shadow:0 8px 20px rgba(49,130,246,.22); transition:transform .18s ease,box-shadow .18s ease,filter .18s ease; }
.stButton > button p, .stButton > button span, .stDownloadButton > button p, .stFormSubmitButton > button p, .stFormSubmitButton > button span { color:#fff !important; font-weight:750; }
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover { transform:translateY(-1px); box-shadow:0 12px 26px rgba(49,130,246,.30); border-color:rgba(255,255,255,.95); filter:saturate(1.08); }
.stButton > button:focus, .stDownloadButton > button:focus, .stFormSubmitButton > button:focus { outline:2px solid rgba(49,130,246,.25); outline-offset:2px; }
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
@media (max-width: 760px) { .block-container { padding-left:.65rem !important; padding-right:.65rem !important; padding-top:.65rem; } .brandbar { padding:15px 17px; border-radius:20px; align-items:flex-start; flex-direction:column; } .hero-card { padding:28px 19px; } .glass-card { padding:19px; } .section-title { font-size:24px; } [data-testid="stTabs"] [data-baseweb="tab-list"] { flex-wrap:wrap; } [data-testid="stDataFrame"] { max-width:100%; } [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) { display:grid !important; grid-template-columns:repeat(4,minmax(0,1fr)) !important; grid-auto-flow:row !important; column-gap:3px !important; row-gap:3px !important; align-items:stretch !important; width:100% !important; max-width:100% !important; margin-left:0 !important; margin-right:0 !important; } [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="column"] { min-width:0 !important; width:auto !important; max-width:none !important; flex:none !important; padding:0 !important; margin:0 !important; } [data-testid="stMetric"] { box-sizing:border-box !important; min-width:0 !important; width:100% !important; max-width:none !important; aspect-ratio:auto !important; min-height:82px !important; padding:9px 3px !important; margin:0 !important; border-radius:11px !important; box-shadow:0 3px 10px rgba(51,65,97,.05) !important; display:flex !important; flex-direction:column !important; justify-content:center !important; overflow:hidden !important; } [data-testid="stMetricLabel"] { font-size:clamp(9px, 2.9vw, 11px) !important; line-height:1.25 !important; font-weight:650 !important; white-space:nowrap !important; overflow:visible !important; text-overflow:clip !important; word-break:keep-all !important; letter-spacing:-.35px !important; } [data-testid="stMetricValue"] { font-size:clamp(13px, 3.8vw, 16px) !important; line-height:1.25 !important; font-weight:800 !important; white-space:nowrap !important; overflow:visible !important; text-overflow:clip !important; letter-spacing:-.4px !important; } [data-testid="stMetricValue"] > div { font-weight:800 !important; } [data-testid="stMetricDelta"] { font-size:9px !important; } }
@media (hover: none) and (pointer: coarse) { .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { min-height:52px; } [data-testid="stTextInput"] input { min-height:58px !important; font-size:18px !important; } }
/* Consistent responsive behavior for iOS Safari, Android browsers, and desktop */
*, *::before, *::after { box-sizing:border-box; }
img, video, iframe { max-width:100%; }
[data-testid="stAppViewContainer"] { overflow-x:hidden; }
[data-testid="stHorizontalBlock"] { max-width:100%; }

/* Subtle transitions for layout changes and interaction feedback.
   Streamlit reruns still rebuild widgets, so keep motion short and lightweight. */
[data-testid="stHorizontalBlock"],
[data-testid="column"],
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stTextInput"],
[data-testid="stButton"],
[data-testid="stFormSubmitButton"],
[data-testid="stSelectbox"],
[data-testid="stDateInput"],
[data-testid="stTimeInput"] {
  transition: opacity .18s ease, transform .18s ease, box-shadow .18s ease;
}
.glass-card { animation: softEnter .2s ease both; }
@keyframes softEnter {
  from { opacity: .72; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
  transition: transform .14s ease, box-shadow .14s ease, filter .14s ease;
  -webkit-tap-highlight-color: transparent;
}
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
  transition: border-color .14s ease, box-shadow .14s ease, background-color .14s ease;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button { touch-action:manipulation; }
@supports (-webkit-touch-callout: none) { input, textarea, select { font-size:16px !important; } }
@media (max-width:760px) {
  .block-container { width:100% !important; max-width:100% !important; padding-left:1rem !important; padding-right:1rem !important; }
  .section-title { overflow-wrap:anywhere; }
  [data-testid="stHorizontalBlock"] { gap:.5rem !important; }
  [data-testid="stTabs"] [data-baseweb="tab-list"] { overflow-x:auto !important; flex-wrap:nowrap !important; scrollbar-width:thin; }
  [data-testid="stTabs"] button[role="tab"] { flex:0 0 auto; white-space:nowrap; }
}
</style>''', unsafe_allow_html=True)

# 학번 입력은 모바일/iPad에서 숫자 키패드를 띄우고, PC에서도 숫자만 입력되도록 제한
st.markdown(r'''<script>
(function() {
  function setNumericStudentInputs() {
    try {
      const doc = window.parent.document;
      doc.querySelectorAll('input').forEach(function(el) {
        const label = (el.getAttribute('aria-label') || '').toLowerCase();
        const placeholder = (el.getAttribute('placeholder') || '').toLowerCase();
        const isStudentId = label.includes('학번') || placeholder.includes('10101');
        if (!isStudentId || el.dataset.numericStudentId === '1') return;
        el.dataset.numericStudentId = '1';
        el.setAttribute('inputmode', 'numeric');
        el.setAttribute('pattern', '[0-9]*');
        el.setAttribute('autocomplete', 'off');
        el.addEventListener('beforeinput', function(e) {
          if (e.data && /[^0-9]/.test(e.data) && e.inputType !== 'deleteContentBackward' && e.inputType !== 'deleteContentForward') e.preventDefault();
        });
        el.addEventListener('input', function() {
          const clean = el.value.replace(/[^0-9]/g, '').slice(0, 5);
          if (el.value !== clean) {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, clean);
            el.dispatchEvent(new Event('input', {bubbles: true}));
          }
        });
      });
    } catch (e) {}
  }
  setNumericStudentInputs();
  const doc = window.parent.document;
  const observer = new MutationObserver(setNumericStudentInputs);
  observer.observe(doc.body, {childList: true, subtree: true});
})();
</script>''', unsafe_allow_html=True)

# 접근성·기기 호환 설정: Streamlit 위젯 기반 테마 전환
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
    @media (max-width:760px) {
      .block-container { padding-left:1rem !important; padding-right:1rem !important; }
      .brandbar,.hero-card,.glass-card { border-radius:18px !important; }
      [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:4px !important; }
      [data-testid="stTabs"] button[role="tab"] { padding:9px 10px !important; }
    }
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
    # 학번이 바뀌었는데 이전 학생 이름이 남아 잘못 등록되는 것을 방지
    st.session_state["participant_name"] = matched_name

def desktop_quick_sid_changed():
    sid = str(st.session_state.get("desktop_quick_sid", "")).strip()
    if len(sid) == 5 and sid.isdigit():
        st.session_state["desktop_quick_name"] = find_student_name(sid)
        st.session_state["desktop_focus_name"] = True
    else:
        st.session_state["desktop_quick_name"] = ""
        st.session_state["desktop_focus_name"] = False

def desktop_quick_name_entered():
    st.session_state["desktop_quick_submit_pending"] = True

def numeric_id_to_string(value):
    """Convert an integer ID widget value to the existing five-digit ID format."""
    if value is None or value == "":
        return ""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ""
    if number < 0 or number > 99999:
        return ""
    return str(number)

def fill_staff_student_name():
    sid = numeric_id_to_string(st.session_state.get("staff_search_id_numeric"))
    matched_name = find_student_name(sid) if len(sid) == 5 and sid.isdigit() else ""
    if matched_name:
        st.session_state["staff_search_name"] = matched_name

def event_options(df):
    return [f"[{r['status']}] {r['name']}" for _, r in df.iterrows()] if not df.empty else ["등록된 행사 없음"]
def clean_event(value):
    return value.split("] ", 1)[-1] if "] " in value else value

if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'staff_info' not in st.session_state: st.session_state.staff_info = None

# Keep the selected role across refreshes with a query parameter.
# This is convenience persistence only, not an authentication/security mechanism.
try:
    saved_role = st.query_params.get("role", "")
except Exception:
    saved_role = ""
if st.session_state.user_role is None and saved_role in ("staff", "participant"):
    st.session_state.user_role = saved_role
    # Staff identity is kept in session state only; after a refresh use a generic label.
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
        with st.expander("📘 사용 설명 보기", expanded=False):
            st.markdown("""
            **1. 학생 · 빠른 등록**
            - `빠른 등록`을 선택합니다.
            - 학년, 반, 번호를 버튼으로 선택합니다. 이름은 기존 등록 기록에 있으면 선택할 수 있으며, 몰라도 건너뛸 수 있습니다.
            - 참여할 행사를 고른 뒤 등록합니다. 같은 날 같은 행사에 이미 등록한 경우 경고가 표시됩니다.

            **2. 사서교사 · 도서부원**
            - 관리자 로그인을 선택하고 직위와 담당자 정보를 입력합니다.
            - **참여 등록** 탭에서 학생 정보를 확인하고 행사 참여를 등록할 수 있습니다.
            - **행사 관리**에서 행사를 개설·수정·마감할 수 있고, **통계 대시보드**에서 참여 현황을 확인할 수 있습니다.

            **3. 유의 사항**
            - 행사 목록에 등록할 행사가 없거나 행사가 마감된 경우 관리자에게 문의하세요.
            - 학번과 이름을 정확히 확인한 뒤 등록해 주세요.
            """)
        if st.button("빠른 등록", use_container_width=True):
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
            staff_std_id_value = st.number_input("학번 (5자리)", min_value=0, max_value=99999, value=None, step=1, key="staff_login_student_id", placeholder="숫자 5자리")
            staff_std_id = numeric_id_to_string(staff_std_id_value)
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
