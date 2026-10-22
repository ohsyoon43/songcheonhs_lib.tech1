import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3

# ==========================================
# 1. 데이터베이스(SQLite) 연결 및 연동
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('library_system.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            grade INTEGER NOT NULL,
            class INTEGER NOT NULL,
            number INTEGER NOT NULL,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            operator TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            detail TEXT NOT NULL,
            operator TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# DB 헬퍼 함수
def db_get_events():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM events ORDER BY id DESC", conn)
    conn.close()
    return df

def db_get_participants():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM participants ORDER BY id DESC", conn)
    conn.close()
    return df

def db_get_logs():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM logs ORDER BY id DESC", conn)
    conn.close()
    return df

def db_add_event(name, status, created_at):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO events (name, status, created_at) VALUES (?, ?, ?)", (name, status, created_at))
    conn.commit()
    conn.close()

def db_update_event_status(event_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET status = ? WHERE id = ?", (new_status, event_id))
    conn.commit()
    conn.close()

def db_delete_event_and_records(event_id, event_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 1. 행사 삭제
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    # 2. 해당 행사의 모든 참여 기록 삭제
    cursor.execute("DELETE FROM participants WHERE event_name = ?", (event_name,))
    conn.commit()
    conn.close()

def db_add_participant(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO participants (event_name, student_id, grade, class, number, name, timestamp, operator)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['event_name'], data['student_id'], data['grade'], data['class'], data['number'], data['name'], data['timestamp'], data['operator']))
    conn.commit()
    conn.close()

def db_delete_participant(part_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM participants WHERE id = ?", (part_id,))
    conn.commit()
    conn.close()

def db_update_participant(part_id, event_name, student_id, grade, class_num, number, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE participants 
        SET event_name = ?, student_id = ?, grade = ?, class = ?, number = ?, name = ?
        WHERE id = ?
    ''', (event_name, student_id, grade, class_num, number, name, part_id))
    conn.commit()
    conn.close()

def db_add_log(category, detail, operator):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (timestamp, category, detail, operator)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), category, detail, operator))
    conn.commit()
    conn.close()

# ==========================================
# 2. 페이지 디자인 및 다크/라이트 테마 CSS
# ==========================================
st.set_page_config(
    page_title="송천 도서관 행정 관리 시스템",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'dark'

bg_color = "#0B0F19" if st.session_state.theme_mode == 'dark' else "#F0F3F8"
card_bg = "rgba(22, 30, 46, 0.75)" if st.session_state.theme_mode == 'dark' else "rgba(255, 255, 255, 0.9)"
text_main = "#FFFFFF" if st.session_state.theme_mode == 'dark' else "#1A202C"
text_sub = "#94A3B8" if st.session_state.theme_mode == 'dark' else "#64748B"
border_color = "rgba(255, 255, 255, 0.08)" if st.session_state.theme_mode == 'dark' else "rgba(0, 0, 0, 0.06)"

st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_main} !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    
    .jaenact-card {{
        background: {card_bg};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 24px;
        padding: 32px;
        border: 1px solid {border_color};
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
        margin-bottom: 24px;
    }}
    
    .stButton>button {{
        width: 100%;
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
        color: white !important;
        border-radius: 16px !important;
        border: none !important;
        height: 50px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25) !important;
        transition: all 0.25s ease !important;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(59, 130, 246, 0.35) !important;
    }}
    
    .sub-btn > button {{
        background: rgba(148, 163, 184, 0.15) !important;
        color: {text_main} !important;
        box-shadow: none !important;
    }}
    
    .danger-btn > button {{
        background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%) !important;
        box-shadow: 0 8px 20px rgba(239, 68, 68, 0.25) !important;
    }}
    
    .badge-tag {{
        display: inline-block;
        padding: 6px 14px;
        background: rgba(59, 130, 246, 0.15);
        color: #60A5FA;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        border: 1px solid rgba(59, 130, 246, 0.3);
        margin-bottom: 12px;
    }}
    
    h1, h2, h3, h4 {{
        color: {text_main} !important;
        font-weight: 800 !important;
    }}
    p, span {{
        color: {text_sub};
    }}
    </style>
""", unsafe_allow_html=True)

def parse_student_id(std_id):
    std_str = str(std_id).strip()
    if len(std_str) == 5 and std_str.isdigit():
        grade = int(std_str[0])
        class_num = int(std_str[1:3])
        number = int(std_str[3:5])
        return True, grade, class_num, number
    return False, None, None, None

# ==========================================
# 3. 세션 상태 및 상단 헤더
# ==========================================
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

if 'staff_info' not in st.session_state:
    st.session_state.staff_info = None

nav_col1, nav_col2, nav_col3 = st.columns([4, 5, 2])
with nav_col1:
    st.markdown("<h2 style='margin:0; font-size: 26px;'>Songcheon Lib Tech</h2>", unsafe_allow_html=True)
with nav_col3:
    mode_txt = "라이트 모드" if st.session_state.theme_mode == 'dark' else "다크 모드"
    if st.button(mode_txt):
        st.session_state.theme_mode = 'light' if st.session_state.theme_mode == 'dark' else 'dark'
        st.rerun()

st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin-bottom: 30px;'>", unsafe_allow_html=True)

# ==========================================
# 4. 진입 메인 화면
# ==========================================
if st.session_state.user_role is None:
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="jaenact-card" style="text-align: center;">', unsafe_allow_html=True)
        st.markdown('<div class="badge-tag">LIBRARY SYSTEM</div>', unsafe_allow_html=True)
        st.markdown("<h1 style='font-size: 36px; margin-bottom: 8px;'>인천송천고 도서관</h1>", unsafe_allow_html=True)
        st.markdown("<p style='margin-bottom: 32px;'>행사 출석 등록 및 데이터 관리 시스템</p>", unsafe_allow_html=True)
        
        if st.button("학생 / 일반 참여자 등록"):
            st.session_state.user_role = 'participant'
            st.rerun()
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        if st.button("사서교사 & 도서부원 관리자 로그인"):
            st.session_state.user_role = 'staff_login'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 관계자 로그인
# ==========================================
elif st.session_state.user_role == 'staff_login':
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
        st.markdown('<div class="badge-tag">ADMIN AUTH</div>', unsafe_allow_html=True)
        st.markdown("<h3>관리자 인증</h3>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px; margin-bottom: 24px;'>처리 담당자 정보를 입력해 주세요.</p>", unsafe_allow_html=True)
        
        staff_type = st.selectbox("직위 구분", ["도서부원", "사서교사"])
        
        if staff_type == "도서부원":
            staff_std_id = st.text_input("학번 (5자리)", placeholder="예: 10101")
            staff_name = st.text_input("이름", placeholder="예: 김송천")
        else:
            staff_std_id = "교직원"
            staff_name = st.text_input("이름", placeholder="예: 담당선생님")
            
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("관리자 접속"):
                if staff_type == "도서부원":
                    is_v, _, _, _ = parse_student_id(staff_std_id)
                    if not is_v or not staff_name.strip():
                        st.error("올바른 5자리 학번과 이름을 입력해 주세요.")
                    else:
                        st.session_state.staff_info = f"도서부원 {staff_std_id} {staff_name.strip()}"
                        st.session_state.user_role = 'staff'
                        db_add_log("시스템 접속", f"{st.session_state.staff_info} 관리자 접속함", st.session_state.staff_info)
                        st.rerun()
                else:
                    if not staff_name.strip():
                        st.error("이름을 입력해 주세요.")
                    else:
                        st.session_state.staff_info = f"사서교사 {staff_name.strip()}"
                        st.session_state.user_role = 'staff'
                        db_add_log("시스템 접속", f"{st.session_state.staff_info} 관리자 접속함", st.session_state.staff_info)
                        st.rerun()
        with c_btn2:
            st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
            if st.button("메인 화면으로 이동"):
                st.session_state.user_role = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. 일반 참여자 전용 화면
# ==========================================
elif st.session_state.user_role == 'participant':
    top_l, top_r = st.columns([8, 2])
    with top_l:
        st.markdown("<h2>도서관 행사 참여 등록</h2>", unsafe_allow_html=True)
    with top_r:
        st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
        if st.button("메인 화면으로 이동"):
            st.session_state.user_role = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
        df_events = db_get_events()
        all_events_list = [f"[{row['status']}] {row['name']}" for _, row in df_events.iterrows()] if not df_events.empty else ["등록된 행사 없음"]
                    
        selected_event_str = st.selectbox("참여할 행사 선택", all_events_list)
        std_id_p = st.text_input("학번 입력 (5자리)", placeholder="예: 10101")
        name_p = st.text_input("이름 입력", placeholder="예: 김송천")
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        if st.button("참여 등록하기"):
            is_v, grade, class_num, number = parse_student_id(std_id_p)
            
            if not selected_event_str or "행사 없음" in selected_event_str:
                st.error("등록 실패: 선택 가능한 행사가 없습니다.")
            elif "[마감]" in selected_event_str:
                st.error("등록 실패: 마감된 행사입니다. 도서부원에게 문의해 주세요.")
            elif not is_v or not name_p.strip():
                st.error("등록 실패: 올바른 5자리 학번과 이름을 입력해 주세요.")
            else:
                event_clean = selected_event_str.split("] ")[-1] if "]" in selected_event_str else selected_event_str
                reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                db_add_participant({
                    "event_name": event_clean,
                    "student_id": std_id_p.strip(),
                    "grade": grade,
                    "class": class_num,
                    "number": number,
                    "name": name_p.strip(),
                    "timestamp": reg_time,
                    "operator": "참여자 본인"
                })
                db_add_log("참여자 등록", f"[{event_clean}] {std_id_p} {name_p} 등록 완료", "참여자 본인")
                st.success(f"등록 완료: {name_p.strip()}님, 정상 등록되었습니다!")
                
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. 도서관 관계자 메인 행정 시스템
# ==========================================
elif st.session_state.user_role == 'staff':
    top_col1, top_col2 = st.columns([8, 2])
    with top_col1:
        st.markdown(f"<h3>도서관 행정 시스템 &nbsp;|&nbsp; <span style='color:#60A5FA; font-size:18px;'>{st.session_state.staff_info}</span></h3>", unsafe_allow_html=True)
    with top_col2:
        st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
        if st.button("로그아웃"):
            st.session_state.user_role = None
            st.session_state.staff_info = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    tab_nav1, tab_nav2, tab_nav3, tab_nav4, tab_nav5 = st.tabs(["참여자 출석 등록", "행사 개설 및 마감 관리", "통계 대시보드", "처리 이력 (Audit Log)", "백업/복원"])
    
    # 탭 1: 참여자 출석 등록
    with tab_nav1:
        df_all_p = db_get_participants()
        df_events = db_get_events()
        
        left_col, right_col = st.columns([1, 2.3])
        
        with left_col:
            st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
            st.markdown("<h4>1. 학생 검색</h4>", unsafe_allow_html=True)
            search_std_id = st.text_input("학번 입력 (5자리)", key="staff_search_id", placeholder="예: 10101")
            search_name = st.text_input("이름 입력", key="staff_search_name", placeholder="예: 김송천")
            
            student_history = []
            is_valid_student = False
            grade, class_num, number = None, None, None
            
            if search_std_id.strip() and search_name.strip():
                is_valid_student, grade, class_num, number = parse_student_id(search_std_id)
                if is_valid_student and not df_all_p.empty:
                    student_history = df_all_p[df_all_p['student_id'] == search_std_id.strip()].to_dict('records')
            
            st.markdown("<hr style='border-color:rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            st.markdown("<h5>과거 참여 이력</h5>", unsafe_allow_html=True)
            if search_std_id.strip():
                if student_history:
                    st.success(f"총 {len(student_history)}건의 이력이 있습니다.")
                    for hist in student_history:
                        st.markdown(f"- **{hist['event_name']}** ({hist['timestamp']})")
                else:
                    st.info("과거 참여 이력이 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with right_col:
            st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
            st.markdown("<h4>2. 행사 출석 확인 및 등록</h4>", unsafe_allow_html=True)
            all_events_list = [f"[{row['status']}] {row['name']}" for _, row in df_events.iterrows()] if not df_events.empty else ["등록된 행사 없음"]
            selected_event_str = st.selectbox("등록할 행사 선택", all_events_list)
            
            with st.expander("일시 수동 지정 (소급 등록)"):
                c_date = st.date_input("날짜 선택", date.today())
                c_time = st.time_input("시간 선택", datetime.now().time())
                custom_datetime_str = f"{c_date} {c_time.strftime('%H:%M:%S')}"
            
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            if st.button("출석 등록 완료"):
                if not selected_event_str or "행사 없음" in selected_event_str:
                    st.error("행사를 선택해 주세요.")
                elif not is_valid_student or not search_name.strip():
                    st.error("왼쪽에 올바른 5자리 학번과 이름을 먼저 입력해 주세요.")
                else:
                    event_clean = selected_event_str.split("] ")[-1] if "]" in selected_event_str else selected_event_str
                    reg_time = custom_datetime_str if custom_datetime_str else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    db_add_participant({
                        "event_name": event_clean,
                        "student_id": search_std_id.strip(),
                        "grade": grade,
                        "class": class_num,
                        "number": number,
                        "name": search_name.strip(),
                        "timestamp": reg_time,
                        "operator": st.session_state.staff_info
                    })
                    db_add_log("참여자 등록", f"[{event_clean}] {search_std_id} {search_name} 등록 완료", st.session_state.staff_info)
                    st.success(f"{search_name.strip()}님 출석 등록 완료!")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 금일 출석 현황 관리
            st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
            st.markdown("<h4>금일 참여자 출석 현황 관리</h4>", unsafe_allow_html=True)
            today_str = datetime.now().strftime("%Y-%m-%d")
            if not df_all_p.empty:
                df_today = df_all_p[df_all_p['timestamp'].str.startswith(today_str)]
                if not df_today.empty:
                    for _, row in df_today.iterrows():
                        c_info, c_del, c_edit = st.columns([3, 1, 1])
                        c_info.write(f"[{row['timestamp']}] **{row['event_name']}** - {row['student_id']} {row['name']}")
                        
                        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                        if c_del.button("삭제", key=f"del_{row['id']}"):
                            db_delete_participant(row['id'])
                            db_add_log("데이터 삭제", f"참여자 ID {row['id']} 삭제됨", st.session_state.staff_info)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        with c_edit.expander("수정"):
                            mod_name = st.text_input("이름", value=row['name'], key=f"m_name_{row['id']}")
                            mod_std = st.text_input("학번", value=row['student_id'], key=f"m_std_{row['id']}")
                            if st.button("저장", key=f"m_save_{row['id']}"):
                                v_ok, g, cl, num = parse_student_id(mod_std)
                                if v_ok and mod_name.strip():
                                    db_update_participant(row['id'], row['event_name'], mod_std.strip(), g, cl, num, mod_name.strip())
                                    db_add_log("데이터 수정", f"참여자 ID {row['id']} 수정 완료", st.session_state.staff_info)
                                    st.success("수정 완료!")
                                    st.rerun()
                else:
                    st.info("오늘 등록된 출석 기록이 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

    # 탭 2: 행사 개설 및 마감 관리 (삭제 기능 추가)
    with tab_nav2:
        st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
        st.markdown("<h4>신규 행사 개설</h4>", unsafe_allow_html=True)
        e_col1, e_col2 = st.columns([1, 1.8])
        with e_col1:
            new_e_name = st.text_input("새 행사명 입력")
            if st.button("행사 개설"):
                if new_e_name.strip():
                    db_add_event(new_e_name.strip(), "진행 중", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    db_add_log("행사 생성", f"신규 행사 [{new_e_name.strip()}] 생성", st.session_state.staff_info)
                    st.success(f"[{new_e_name.strip()}] 행사가 개설되었습니다.")
                    st.rerun()
        with e_col2:
            st.markdown("<h5>개설된 행사 목록 및 관리</h5>", unsafe_allow_html=True)
            df_evs = db_get_events()
            if not df_evs.empty:
                for _, ev in df_evs.iterrows():
                    l_col, m_col, r_col = st.columns([2.5, 1, 1])
                    l_col.write(f"**{ev['name']}** (상태: `{ev['status']}`)")
                    
                    # 마감/재개 버튼
                    btn_txt = "마감하기" if ev['status'] == "진행 중" else "재개하기"
                    if m_col.button(btn_txt, key=f"e_toggle_{ev['id']}"):
                        new_st = "마감" if ev['status'] == "진행 중" else "진행 중"
                        db_update_event_status(ev['id'], new_st)
                        db_add_log("행사 상태 변경", f"[{ev['name']}] -> {new_st}", st.session_state.staff_info)
                        st.rerun()
                        
                    # 마감된 행사 삭제 버튼 및 경고 모달
                    if ev['status'] == "마감":
                        with r_col.expander("행사 삭제"):
                            st.error("⚠️ 경고: 행사 삭제 시 해당 행사에 포함된 모든 학생의 참여 기록도 함께 완전히 삭제됩니다!")
                            if st.button("정말 영구 삭제", key=f"e_del_{ev['id']}"):
                                db_delete_event_and_records(ev['id'], ev['name'])
                                db_add_log("행사 삭제", f"행사 [{ev['name']}] 및 연관 참여 데이터 영구 삭제 완료", st.session_state.staff_info)
                                st.success("행사 및 연관 기록이 정상적으로 삭제 되었습니다.")
                                st.rerun()
                    else:
                        r_col.write("-")
            else:
                st.info("개설된 행사가 없습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 탭 3: 통계 대시보드
    with tab_nav3:
        st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
        st.markdown("<h4>통합 통계 대시보드 및 시각화</h4>", unsafe_allow_html=True)
        df_all = db_get_participants()
        if df_all.empty:
            st.info("통계를 산출할 참여 데이터가 없습니다.")
        else:
            st.bar_chart(df_all['event_name'].value_counts())
            t1, t2 = st.tabs(["행사별 통계", "학년별 통계"])
            with t1:
                st.dataframe(df_all['event_name'].value_counts().reset_index(), use_container_width=True, hide_index=True)
            with t2:
                st.dataframe(df_all['grade'].value_counts().reset_index(), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 탭 4: 처리 이력
    with tab_nav4:
        st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
        st.markdown("<h4>시스템 감사 로그 (Audit Log)</h4>", unsafe_allow_html=True)
        df_l = db_get_logs()
        if not df_l.empty:
            st.dataframe(df_l, use_container_width=True, hide_index=True)
        else:
            st.info("이력이 없습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 탭 5: 백업 및 복원
    with tab_nav5:
        st.markdown('<div class="jaenact-card">', unsafe_allow_html=True)
        st.markdown("<h4>데이터 백업 및 복원</h4>", unsafe_allow_html=True)
        with open("library_system.db", "rb") as f:
            db_bytes = f.read()
        st.download_button(
            label="데이터베이스 파일 백업 (.db 다운로드)",
            data=db_bytes,
            file_name=f"library_backup_{datetime.now().strftime('%Y%m%d')}.db",
            mime="application/octet-stream"
        )
        st.markdown('</div>', unsafe_allow_html=True)
