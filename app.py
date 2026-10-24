import streamlit as st
import pandas as pd
from datetime import datetime, date, time
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
# Database Connection & Helper Functions
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

def read_table(query):
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn)

def db_get_events(): return read_table("SELECT * FROM events ORDER BY id DESC")
def db_get_participants(): return read_table("SELECT * FROM participants ORDER BY id DESC")
def db_get_logs(): return read_table("SELECT * FROM logs ORDER BY id DESC")

def db_add_event(name, status, created_at, event_type="기타", description=""):
    with get_db_connection() as conn:
        conn.execute("INSERT INTO events (name,status,created_at) VALUES (?,?,?)", (name,status,created_at))

def db_update_event_status(event_id, new_status):
    with get_db_connection() as conn:
        conn.execute("UPDATE events SET status=? WHERE id=?", (new_status,event_id))

def db_delete_event_and_records(event_id, event_name, deleted_by="관리자"):
    with get_db_connection() as conn:
        participant_ids = [row[0] for row in conn.execute("SELECT id FROM participants WHERE event_name=?", (event_name,)).fetchall()]
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
    if not ids: return 0
    placeholders = ",".join("?" for _ in ids)
    deleted_at = now_seoul().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        rows = conn.execute(f"SELECT id,event_name,student_id,grade,class,number,name,timestamp,operator FROM participants WHERE id IN ({placeholders})", ids).fetchall()
        conn.executemany("""INSERT INTO deleted_participants
            (original_id,event_name,student_id,grade,class,number,name,timestamp,operator,deleted_at,deleted_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", [(r[0], *r[1:], deleted_at, deleted_by) for r in rows])
        conn.executemany("DELETE FROM participants WHERE id=?", [(r[0],) for r in rows])
    return len(rows)

def db_add_log(category, detail, operator):
    with get_db_connection() as conn:
        conn.execute("INSERT INTO logs (timestamp,category,detail,operator) VALUES (?,?,?,?)",
                     (now_seoul().strftime("%Y-%m-%d %H:%M:%S"),category,detail,operator))

def db_clear_logs():
    with get_db_connection() as conn:
        conn.execute("DELETE FROM logs")

init_db()

# ------------------------------------------------------------
# CSS Design & Theme
# ------------------------------------------------------------
st.markdown(r'''<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
:root { --ink:#20232b; --muted:#737b8c; --blue:#3182F6; --blue2:#1B64DA; }
html, body, [class*="css"], [data-testid="stAppViewContainer"] { font-family: Pretendard, -apple-system, sans-serif; }
.stApp { color:var(--ink); background: radial-gradient(ellipse at 15% 28%,rgba(151,164,255,.19),transparent 34%), radial-gradient(ellipse at 82% 42%,rgba(164,205,255,.22),transparent 34%), linear-gradient(135deg,#f4f5fb 0%,#f9fafc 48%,#edf1f9 100%); }
.block-container { max-width:1320px; padding-top:1.4rem; padding-bottom:3rem; }
.brandbar { display:flex; justify-content:space-between; align-items:center; padding:17px 24px; margin-bottom:26px; border:1px solid rgba(255,255,255,.88); border-radius:28px; background:rgba(255,255,255,.68); backdrop-filter:blur(20px); box-shadow:0 12px 34px rgba(61,73,104,.08); }
.brandname { font-size:19px; font-weight:800; color:#20232b; }
.branddesc { color:#737b8c; font-size:13px; }
.eyebrow { display:inline-block; color:#3182F6; font-size:12px; letter-spacing:2px; font-weight:800; text-transform:uppercase; padding-bottom:9px; border-bottom:2px solid #1B64DA; margin-bottom:15px; }
.hero-card, .glass-card { border:1px solid rgba(255,255,255,.92); border-radius:28px; background:rgba(255,255,255,.74); backdrop-filter:blur(18px); box-shadow:0 18px 50px rgba(51,65,97,.09); }
.glass-card { padding:22px 24px; margin-bottom:18px; }
.section-title { font-size:27px; font-weight:820; margin:4px 0 22px; color:#20232b; }
.muted { color:#7b8291; }
.stButton > button, .stDownloadButton > button { width:100%; min-height:46px; border-radius:15px; border:1px solid rgba(255,255,255,.9); background:linear-gradient(135deg,#3182F6,#1B64DA); color:#fff; font-weight:750; box-shadow:0 8px 20px rgba(49,130,246,.22); transition:all .18s ease; }
.stButton > button p, .stButton > button span { color:#fff !important; font-weight:750; }
[data-testid="stTextInput"] input, [data-testid="stDateInput"] input, [data-testid="stTimeInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div { border-radius:13px !important; border-color:#dfe4ef !important; background:rgba(255,255,255,.82) !important; min-height:48px !important; font-size:16px !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:7px; padding:7px; border:1px solid rgba(255,255,255,.95); border-radius:20px; background:rgba(255,255,255,.58); }
[data-testid="stTabs"] button[role="tab"] { border-radius:14px; padding:11px 15px; color:#626b7b; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:#fff; box-shadow:0 5px 15px rgba(70,84,120,.12); color:#1B64DA; }
[data-testid="stDataFrame"] { border:1px solid #e6eaf2; border-radius:16px; overflow:hidden; }
</style>''', unsafe_allow_html=True)

st.markdown('''<div class="brandbar"><div class="brandname">Songcheon <span style="color:#3182F6">Lib Tech</span></div><div class="branddesc">인천송천고등학교 · 행사 관리 시스템</div></div>''', unsafe_allow_html=True)

def parse_student_id(std_id):
    value = str(std_id).strip()
    if len(value) == 5 and value.isdigit():
        return True, int(value[0]), int(value[1:3]), int(value[3:5])
    return False, None, None, None

def find_student_name(student_id):
    sid = str(student_id).strip()
    if len(sid) != 5 or not sid.isdigit(): return ""
    df = db_get_participants()
    if df.empty: return ""
    matches = df[df["student_id"].astype(str).str.strip() == sid]
    if matches.empty: return ""
    names = matches["name"].dropna().astype(str).str.strip()
    names = names[names != ""]
    return names.iloc[0] if not names.empty else ""

def event_options(df):
    return [f"[{r['status']}] {r['name']}" for _, r in df.iterrows()] if not df.empty else ["등록된 행사 없음"]
def clean_event(value):
    return value.split("] ", 1)[-1] if "] " in value else value

if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'staff_info' not in st.session_state: st.session_state.staff_info = None

# Session State Persistence
if "active_student_info" not in st.session_state:
    st.session_state.active_student_info = None  # 검색 결과 보관 {student_id, name}

# ------------------------------------------------------------
# 메인 랜딩 및 로그인
# ------------------------------------------------------------
if st.session_state.user_role is None:
    _, main, _ = st.columns([1, 1.35, 1])
    with main:
        st.markdown('''<div class="hero-card" style="padding:40px;"><div class="eyebrow">EVENT MANAGEMENT</div><div style="font-size:32px;font-weight:850;margin:10px 0;">인천송천고 도서관</div><p class="muted">행사 참여 등록 및 데이터 관리 시스템</p></div>''', unsafe_allow_html=True)
        st.write("")
        if st.button("학생 · 일반 참여자 등록", use_container_width=True):
            st.session_state.user_role = 'participant'; st.rerun()
        if st.button("사서교사 · 도서부원 관리자 로그인", use_container_width=True):
            st.session_state.user_role = 'staff_login'; st.rerun()

elif st.session_state.user_role == 'staff_login':
    _, main, _ = st.columns([1, 1.25, 1])
    with main:
        st.markdown('<div class="section-title">관리자 로그인</div>', unsafe_allow_html=True)
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
            if st.button("메인으로"):
                st.session_state.user_role = None; st.rerun()

elif st.session_state.user_role == 'participant':
    top1, top2 = st.columns([5, 1])
    with top1: st.markdown('<div class="section-title">도서관 행사 참여 등록</div>', unsafe_allow_html=True)
    with top2:
        if st.button("메인으로"): st.session_state.user_role = None; st.rerun()
    _, formcol, _ = st.columns([0.7, 2.2, 0.7])
    with formcol:
        df_events = db_get_events()
        selected = st.selectbox("참여할 행사", event_options(df_events), key="p_event")
        sid = st.text_input("학번 (5자리)", placeholder="예: 10101", max_chars=5, key="p_sid")
        pname = st.text_input("이름", placeholder="이름 입력", key="p_name")
        if st.button("참여 등록하기"):
            valid, grade, class_num, number = parse_student_id(sid)
            if not valid or not pname.strip(): st.error("학번과 이름을 올바르게 입력해 주세요.")
            else:
                event = clean_event(selected)
                db_add_participant({"event_name":event,"student_id":sid.strip(),"grade":grade,"class":class_num,"number":number,"name":pname.strip(),"timestamp":now_seoul().strftime("%Y-%m-%d %H:%M:%S"),"operator":"참여자 본인"})
                st.success("등록이 완료되었습니다!")

# ------------------------------------------------------------
# 관리자 통합 관리 대시보드 (PPT 와이어프레임 100% 일치)
# ------------------------------------------------------------
elif st.session_state.user_role == 'staff':
    h1, h2 = st.columns([5, 1])
    with h1: st.markdown(f'<div class="section-title" style="margin-bottom:8px;">행사 관리 시스템</div><p class="muted">접속 계정: {st.session_state.staff_info}</p>', unsafe_allow_html=True)
    with h2:
        if st.button("로그아웃"): st.session_state.user_role = None; st.session_state.staff_info = None; st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["참여 등록", "행사 관리", "통계 대시보드", "처리 이력", "백업/복원"])

    with tab1:
        df_e = db_get_events()

        # =========================================================
        # PPT 사진과 100% 동일한 좌/우 컬럼 레이아웃 구성
        # =========================================================
        col_left, col_right = st.columns([1, 1.6], gap="large")

        # ---------------------------------------------------------
        # [좌측 컬럼]: 1.참여자정보 -> 2.학번입력 -> 3.이름입력 -> 4.검색/초기화버튼
        # ---------------------------------------------------------
        with col_left:
            # [1] 상단: 참여자 정보 (검색 후 여기에 결과 표시)
            active_info = st.session_state.get("active_student_info")
            if active_info:
                st.markdown(
                    f'''
                    <div class="glass-card" style="padding:18px 20px;border-left:4px solid #3182F6;">
                      <div style="font-size:12px;color:#737b8c;font-weight:700;">참여자 정보 (학번, 이름)</div>
                      <div style="font-size:18px;font-weight:850;color:#20232b;margin-top:6px;">{active_info['student_id']} &nbsp;·&nbsp; {active_info['name']}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '''
                    <div class="glass-card" style="padding:18px 20px;">
                      <div style="font-size:12px;color:#737b8c;font-weight:700;">참여자 정보 (학번, 이름)</div>
                      <div style="font-size:14px;color:#a0a8b8;margin-top:6px;">학생을 검색하면 여기에 정보가 올라갑니다.</div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )

            # [2] 학번 입력
            input_sid = st.text_input("학번 입력", key="in_sid", placeholder="학번 5자리 (예: 10101)", max_chars=5)
            
            # [3] 이름 입력
            input_name = st.text_input("이름 입력", key="in_name", placeholder="학생 이름")

            # [4] 검색 버튼 & 초기화 버튼 (가로 배치)
            btn_c1, btn_c2 = st.columns(2, gap="small")
            with btn_c1:
                search_clicked = st.button("검색 버튼", key="btn_search", type="primary", use_container_width=True)
            with btn_c2:
                clear_clicked = st.button("초기화버튼 (Esc)", key="btn_clear", use_container_width=True)

            # Esc 키 누르면 초기화되도록 연결
            st.components.v1.html("""<script>
            (function(){
              try {
                const doc = window.parent.document;
                if (doc.__escBound) return;
                doc.__escBound = true;
                doc.addEventListener('keydown', function(e) {
                  if (e.key === 'Escape') {
                    const btns = Array.from(doc.querySelectorAll('button'));
                    const target = btns.find(b => (b.innerText||'').includes('초기화버튼'));
                    if (target) { e.preventDefault(); target.click(); }
                  }
                }, true);
              } catch(e) {}
            })();
            </script>""", height=0)

            # --- 검색 및 초기화 동작 처리 ---
            if search_clicked:
                valid, _, _, _ = parse_student_id(input_sid)
                if not valid or not input_name.strip():
                    st.error("올바른 5자리 학번과 이름을 모두 입력해 주세요.")
                else:
                    # 검색 정보를 상단 카드로 전달
                    st.session_state.active_student_info = {
                        "student_id": input_sid.strip(),
                        "name": input_name.strip()
                    }
                    # 입력칸 자동으로 비우기
                    st.session_state["in_sid"] = ""
                    st.session_state["in_name"] = ""
                    st.rerun()

            if clear_clicked:
                st.session_state.active_student_info = None
                st.session_state["in_sid"] = ""
                st.session_state["in_name"] = ""
                st.rerun()

        # ---------------------------------------------------------
        # [우측 컬럼]: 1.행사입력 / 날짜시간선택 / 등록버튼 -> 2.행사 참여 이력
        # ---------------------------------------------------------
        with col_right:
            # [1] 상단 컨트롤: [행사 입력] [날짜 시간 선택 입력] [등록 버튼(enter키)]
            rc1, rc2, rc3 = st.columns([1.5, 1.4, 1.1], gap="small")
            with rc1:
                selected_event = st.selectbox("행사 입력", event_options(df_e), key="r_event")
            with rc2:
                dt_c1, dt_c2 = st.columns(2, gap="small")
                with dt_c1:
                    cdate = st.date_input("날짜", value=now_seoul().date(), key="r_date")
                with dt_c2:
                    ctime = st.time_input("시간", value=now_seoul().time().replace(tzinfo=None, microsecond=0), key="r_time")
            with rc3:
                st.write("") # 버튼 수직 정렬용 여백
                st.write("")
                register_clicked = st.button("등록 버튼 (enter키)", key="r_submit", type="primary", use_container_width=True)

            st.write("") # 간격 조절

            # [2] 하단: 행사 참여 이력 (PPT 와이어프레임과 동일하게 이력 표 위치)
            st.markdown('<h4 style="margin:0 0 8px 0;">행사 참여 이력</h4>', unsafe_allow_html=True)
            
            active_info = st.session_state.get("active_student_info")
            if active_info:
                sid_target = active_info["student_id"]
                name_target = active_info["name"]

                latest_participants = db_get_participants()
                history = latest_participants[
                    (latest_participants["student_id"].astype(str).str.strip() == sid_target) &
                    (latest_participants["name"].astype(str).str.strip() == name_target)
                ].copy() if not latest_participants.empty else pd.DataFrame()

                if history.empty:
                    st.info(f"[{sid_target} {name_target}] 학생의 과거 행사 참여 이력이 없습니다.")
                else:
                    history = history.sort_values("timestamp", ascending=False)
                    st.dataframe(
                        history[["event_name", "timestamp", "operator"]].rename(
                            columns={"event_name":"행사명", "timestamp":"참여 일시", "operator":"등록자"}
                        ), use_container_width=True, hide_index=True, height=280
                    )
            else:
                st.markdown(
                    '<div class="glass-card" style="min-height:280px;display:flex;align-items:center;justify-content:center"><span class="muted">좌측에서 참여자를 검색하면 상세 이력이 표시됩니다.</span></div>',
                    unsafe_allow_html=True
                )

            # --- 행사 등록 동작 처리 ---
            if register_clicked:
                if not active_info:
                    st.warning("먼저 좌측에서 학생을 검색해 참여자 정보를 입력해 주세요.")
                elif "행사 없음" in selected_event:
                    st.error("행사를 선택해 주세요.")
                elif "[마감]" in selected_event:
                    st.error("마감된 행사입니다.")
                else:
                    event = clean_event(selected_event)
                    sid_target = active_info["student_id"]
                    name_target = active_info["name"]
                    valid, grade, class_num, number = parse_student_id(sid_target)

                    db_add_participant({
                        "event_name": event,
                        "student_id": sid_target,
                        "grade": grade,
                        "class": class_num,
                        "number": number,
                        "name": name_target,
                        "timestamp": f"{cdate} {ctime.strftime('%H:%M:%S')}",
                        "operator": st.session_state.staff_info
                    })
                    db_add_log("참여자 등록", f"[{event}] {sid_target} {name_target} 등록 완료", st.session_state.staff_info)
                    
                    # 상단 작게 초록색 팝업 알림 (토스트)
                    st.toast(f"✅ {name_target} 학생의 {event} 등록이 완료되었습니다!", icon="🎉")
                    st.rerun()

        st.divider()

        # 하단 전체 기록 관리
        st.markdown('<h3>전체 참여 기록 관리</h3>', unsafe_allow_html=True)
        all_records = db_get_participants()
        if not all_records.empty:
            st.dataframe(all_records[["id", "event_name", "student_id", "name", "timestamp", "operator"]], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown('<h3>신규 행사 개설 및 관리</h3>', unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1.5])
        with c1:
            new_name = st.text_input("행사명", placeholder="예: 독서의 달 행사", key="n_name")
            if st.button("행사 만들기"):
                if new_name.strip():
                    db_add_event(new_name.strip(), "진행 중", now_seoul().strftime("%Y-%m-%d %H:%M:%S"))
                    st.success("행사가 개설되었습니다."); st.rerun()
        with c2:
            events = db_get_events()
            if not events.empty:
                for _, ev in events.iterrows():
                    l, r = st.columns([3, 1])
                    l.write(f"**{ev['name']}** ({ev['status']})")
                    btn_label = "마감하기" if ev['status'] == "진행 중" else "재개하기"
                    if r.button(btn_label, key=f"e_{ev['id']}"):
                        new_st = "마감" if ev['status'] == "진행 중" else "진행 중"
                        db_update_event_status(ev['id'], new_st)
                        st.rerun()

    with tab3:
        st.markdown('<h3>참여 통계</h3>', unsafe_allow_html=True)
        df_all = db_get_participants()
        if not df_all.empty:
            st.bar_chart(df_all["event_name"].value_counts())

    with tab4:
        st.markdown('<h3>처리 이력 (Audit Log)</h3>', unsafe_allow_html=True)
        logs = db_get_logs()
        if not logs.empty:
            st.dataframe(logs, use_container_width=True, hide_index=True)

    with tab5:
        st.markdown('<h3>데이터 백업</h3>', unsafe_allow_html=True)
        if DB_PATH.exists():
            with open(DB_PATH, "rb") as f:
                st.download_button("데이터베이스 백업 (.db 다운로드)", data=f.read(), file_name="library_system.db")

st.markdown('<div style="text-align:center;color:#a0a8b8;font-size:12px;padding:24px 0 4px;">SONGCHEON EVENT SYSTEM</div>', unsafe_allow_html=True)
