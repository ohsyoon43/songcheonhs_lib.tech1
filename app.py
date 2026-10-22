import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3
import io

# ==========================================
# 1. 데이터베이스(SQLite) 연결 및 초기화
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

# DB 쿼리 함수들
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
# 2. 페이지 기본 설정 및 토스뱅크 스타일 CSS
# ==========================================
st.set_page_config(
    page_title="송천 도서관 행사 관리 시스템",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main {
        background-color: #F8F9FA;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .center-card {
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 36px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        border: 1px solid #E5E8EB;
        max-width: 520px;
        margin: 40px auto;
    }
    .stButton>button {
        width: 100%;
        background-color: #3182F6 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        height: 48px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(49, 130, 246, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1B64DA !important;
        transform: translateY(-1px);
    }
    .sub-btn > button {
        background-color: #E5E8EB !important;
        color: #4E5968 !important;
        box-shadow: none !important;
    }
    .toss-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        border: 1px solid #E5E8EB;
        margin-bottom: 20px;
    }
    .top-summary-bar {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 14px 24px;
        border: 1px solid #E5E8EB;
        margin-bottom: 20px;
        font-size: 14px;
        color: #4E5968;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    .metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #E5E8EB;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .metric-val {
        font-size: 30px;
        font-weight: 800;
        color: #3182F6;
    }
    .metric-lbl {
        font-size: 13px;
        color: #8B95A1;
        margin-top: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 세션 상태 관리
# ==========================================
if 'user_role' not in st.session_state:
    st.session_state.user_role = None  # None, 'participant', 'staff_login', 'staff'

if 'staff_info' not in st.session_state:
    st.session_state.staff_info = None

def parse_student_id(std_id):
    std_str = str(std_id).strip()
    if len(std_str) == 5 and std_str.isdigit():
        grade = int(std_str[0])
        class_num = int(std_str[1:3])
        number = int(std_str[3:5])
        return True, grade, class_num, number
    return False, None, None, None

# ==========================================
# 4. 진입 화면
# ==========================================
if st.session_state.user_role is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #191F28; font-size: 32px; font-weight: 800;'>송천 도서관 행사 관리 시스템</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8B95A1; font-size: 15px; margin-bottom: 30px;'>원하시는 접속 유형을 선택해 주세요.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        if st.button("일반 참여자 등록용 접속"):
            st.session_state.user_role = 'participant'
            st.rerun()
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        if st.button("도서관 관계자용 접속"):
            st.session_state.user_role = 'staff_login'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 도서관 관계자 로그인 화면
# ==========================================
elif st.session_state.user_role == 'staff_login':
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: #191F28; font-weight: 700; margin-bottom: 8px;'>도서관 관계자 인증</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color:#8B95A1; font-size:14px; margin-bottom: 24px;'>처리 담당자 정보를 입력해 주세요.</p>", unsafe_allow_html=True)
        
        staff_type = st.selectbox("직위 선택", ["도서부원", "사서교사"])
        
        if staff_type == "도서부원":
            staff_std_id = st.text_input("학번 (5자리)", placeholder="예: 10101")
            staff_name = st.text_input("이름", placeholder="예: 김송천")
        else:
            staff_std_id = "교직원"
            staff_name = st.text_input("이름", placeholder="예: 담당선생님")
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("접속하기"):
                if staff_type == "도서부원":
                    is_v, _, _, _ = parse_student_id(staff_std_id)
                    if not is_v or not staff_name.strip():
                        st.error("올바른 5자리 학번과 이름을 입력해 주세요.")
                    else:
                        st.session_state.staff_info = f"도서부원 {staff_std_id} {staff_name.strip()}"
                        st.session_state.user_role = 'staff'
                        db_add_log("시스템 접속", f"{st.session_state.staff_info} 접속함", st.session_state.staff_info)
                        st.rerun()
                else:
                    if not staff_name.strip():
                        st.error("이름을 입력해 주세요.")
                    else:
                        st.session_state.staff_info = f"사서교사 {staff_name.strip()}"
                        st.session_state.user_role = 'staff'
                        db_add_log("시스템 접속", f"{st.session_state.staff_info} 접속함", st.session_state.staff_info)
                        st.rerun()
        with c_btn2:
            st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
            if st.button("처음으로"):
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
        st.markdown("<h2 style='color: #191F28; font-weight: 800; margin-left: 20px;'>송천 도서관 행사 참여 등록</h2>", unsafe_allow_html=True)
    with top_r:
        st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
        if st.button("처음 화면으로"):
            st.session_state.user_role = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        
        df_events = db_get_events()
        all_events_list = []
        if not df_events.empty:
            for _, row in df_events.iterrows():
                item_str = f"[{row['status']}] {row['name']}"
                all_events_list.append(item_str)
                    
        selected_event_str = st.selectbox("참여할 행사 선택", all_events_list if all_events_list else ["등록된 행사 없음"])
        
        std_id_p = st.text_input("학번 입력 (5자리)", placeholder="예: 10101")
        name_p = st.text_input("이름 입력", placeholder="예: 김송천")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("참여 등록하기"):
            is_v, grade, class_num, number = parse_student_id(std_id_p)
            
            if not selected_event_str or "행사 없음" in selected_event_str:
                st.error("등록 실패: 등록된 행사가 없습니다. 관리자에게 문의해 주세요.")
            elif "[마감]" in selected_event_str:
                st.error("등록 실패: 마감된 행사입니다. 관리자(도서부원)에게 문의해 주세요.")
            elif not is_v or not name_p.strip():
                st.error("등록 실패: 올바른 5자리 학번(예: 10101)과 이름을 입력해 주세요.")
            else:
                event_clean = selected_event_str.split("] ")[-1] if "]" in selected_event_str else selected_event_str
                reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                new_entry = {
                    "event_name": event_clean,
                    "student_id": std_id_p.strip(),
                    "grade": grade,
                    "class": class_num,
                    "number": number,
                    "name": name_p.strip(),
                    "timestamp": reg_time,
                    "operator": "참여자 본인"
                }
                db_add_participant(new_entry)
                db_add_log("참여자 등록", f"[{event_clean}] {std_id_p} {name_p} 등록 완료", "참여자 본인")
                
                st.success(f"등록 완료: {grade}학년 {class_num}반 {name_p.strip()}님, 정상 등록되었습니다!")
                
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. 도서관 관계자 전용 메인 시스템
# ==========================================
elif st.session_state.user_role == 'staff':
    
    top_col1, top_col2 = st.columns([8, 2])
    with top_col1:
        st.markdown(f"### 송천 도서관 관리 시스템 &nbsp;|&nbsp; <span style='color:#3182F6; font-size:18px;'>담당자: {st.session_state.staff_info}</span>", unsafe_allow_html=True)
    with top_col2:
        st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
        if st.button("로그아웃"):
            st.session_state.user_role = None
            st.session_state.staff_info = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    tab_nav1, tab_nav2, tab_nav3, tab_nav4, tab_nav5 = st.tabs(["참여자 등록", "행사 생성 및 관리", "통계 대시보드", "처리 이력 (Audit Log)", "시스템 백업/복원"])
    
    # --------------------------------------
    # 탭 1: 참여자 등록 (요청하신 학번/이름 검색 우선 워크플로우 적용)
    # --------------------------------------
    with tab_nav1:
        df_all_p = db_get_participants()
        df_events = db_get_events()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_count = sum(1 for _, r in df_all_p.iterrows() if r['timestamp'].startswith(today_str)) if not df_all_p.empty else 0
        active_events_cnt = sum(1 for _, r in df_events.iterrows() if r['status'] == "진행 중") if not df_events.empty else 0
        
        st.markdown(f"""
            <div class="top-summary-bar">
                <div><b>오늘의 참여자:</b> <span style="color:#3182F6; font-weight:bold;">{today_count}명</span></div>
                <div><b>진행 중인 행사:</b> <span style="color:#3182F6; font-weight:bold;">{active_events_cnt}개</span></div>
            </div>
        """, unsafe_allow_html=True)
        
        left_col, right_col = st.columns([1, 2.5])
        
        with left_col:
            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
            st.markdown("<h4>1. 학생 검색 및 정보 확인</h4>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:13px; color:#8B95A1;'>먼저 학번과 이름을 입력해 주세요.</p>", unsafe_allow_html=True)
            
            search_std_id = st.text_input("학번 입력 (5자리)", key="staff_search_id", placeholder="예: 10101")
            search_name = st.text_input("이름 입력", key="staff_search_name", placeholder="예: 김송천")
            
            student_history = []
            is_valid_student = False
            grade, class_num, number = None, None, None
            
            if search_std_id.strip() and search_name.strip():
                is_valid_student, grade, class_num, number = parse_student_id(search_std_id)
                if is_valid_student and not df_all_p.empty:
                    student_history = df_all_p[df_all_p['student_id'] == search_std_id.strip()].to_dict('records')
            
            st.markdown("---")
            st.markdown("<h5>과거 참여 이력</h5>", unsafe_allow_html=True)
            if search_std_id.strip():
                if student_history:
                    st.success(f"총 {len(student_history)}건의 참여 이력이 있습니다.")
                    for hist in student_history:
                        st.markdown(f"- **{hist['event_name']}** ({hist['timestamp']})")
                else:
                    st.info("이 학생의 과거 참여 이력이 없습니다.")
            else:
                st.markdown("<span style='color:#8B95A1; font-size:13px;'>학번을 입력하면 과거 참여 기록이 표시됩니다.</span>", unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        with right_col:
            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
            st.markdown("<h4>2. 행사 선택 및 참여 등록</h4>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:13px; color:#8B95A1;'>이전 참여 이력 유무와 관계없이 행사를 선택하여 등록할 수 있습니다.</p>", unsafe_allow_html=True)
            
            all_events_list = [f"[{row['status']}] {row['name']}" for _, row in df_events.iterrows()] if not df_events.empty else ["등록된 행사 없음"]
            selected_event_str = st.selectbox("등록할 행사 선택", all_events_list)
            
            with st.expander("일시 수동 지정 (소급 등록)"):
                c_date = st.date_input("날짜 선택", date.today())
                c_time = st.time_input("시간 선택", datetime.now().time())
                custom_datetime_str = f"{c_date} {c_time.strftime('%H:%M:%S')}"
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("선택한 행사로 참여 등록 완료"):
                if not selected_event_str or "행사 없음" in selected_event_str:
                    st.error("행사를 선택해 주세요.")
                elif not is_valid_student or not search_name.strip():
                    st.error("왼쪽에 올바른 5자리 학번(예: 10101)과 이름을 먼저 입력해 주세요.")
                else:
                    event_clean = selected_event_str.split("] ")[-1] if "]" in selected_event_str else selected_event_str
                    reg_time = custom_datetime_str if custom_datetime_str else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    new_entry = {
                        "event_name": event_clean,
                        "student_id": search_std_id.strip(),
                        "grade": grade,
                        "class": class_num,
                        "number": number,
                        "name": search_name.strip(),
                        "timestamp": reg_time,
                        "operator": st.session_state.staff_info
                    }
                    db_add_participant(new_entry)
                    db_add_log("참여자 등록", f"[{event_clean}] {search_std_id} {search_name} 등록 완료", st.session_state.staff_info)
                    st.success(f"{search_name.strip()}님({search_std_id})의 [{event_clean}] 참여가 등록되었습니다!")
                    st.rerun()
                    
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 당일 참여 이력 및 수정/삭제 관리 영역
            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
            st.markdown("<h4>당일 참여 이력 관리 (수정 및 삭제 가능)</h4>", unsafe_allow_html=True)
            
            if not df_all_p.empty:
                df_today = df_all_p[df_all_p['timestamp'].str.startswith(today_str)]
                if not df_today.empty:
                    for _, row in df_today.iterrows():
                        c_info, c_del, c_edit = st.columns([3, 1, 1])
                        c_info.write(f"[{row['timestamp']}] **{row['event_name']}** - {row['student_id']} {row['name']}")
                        
                        # 삭제 버튼
                        if c_del.button("삭제", key=f"del_{row['id']}"):
                            db_delete_participant(row['id'])
                            db_add_log("데이터 삭제", f"참여자 ID {row['id']} ({row['student_id']} {row['name']}) 삭제됨", st.session_state.staff_info)
                            st.rerun()
                            
                        # 수정 기능 (Expander 활용)
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
                                    st.error("형식 오류")
                else:
                    st.info("오늘 등록된 참여 기록이 없습니다.")
            else:
                st.info("등록된 데이터가 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------
    # 탭 2: 행사 생성 및 상태 관리
    # --------------------------------------
    with tab_nav2:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        st.markdown("<h4>신규 행사 생성 및 상태 관리</h4>", unsafe_allow_html=True)
        
        e_col1, e_col2 = st.columns([1, 1.8])
        with e_col1:
            new_e_name = st.text_input("새 행사명 입력")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("행사 생성"):
                if new_e_name.strip():
                    db_add_event(new_e_name.strip(), "진행 중", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    db_add_log("행사 생성", f"신규 행사 [{new_e_name.strip()}] 생성", st.session_state.staff_info)
                    st.success(f"[{new_e_name.strip()}] 행사가 생성되었습니다.")
                    st.rerun()
                else:
                    st.error("행사명을 입력해 주세요.")
                    
        with e_col2:
            st.markdown("<h5>등록된 행사 목록</h5>", unsafe_allow_html=True)
            df_evs = db_get_events()
            if not df_evs.empty:
                for _, ev in df_evs.iterrows():
                    l_col, r_col = st.columns([3, 1])
                    l_col.write(f"**{ev['name']}** (상태: `{ev['status']}` / 생성일: {ev['created_at']})")
                    btn_txt = "마감하기" if ev['status'] == "진행 중" else "재개하기"
                    if r_col.button(btn_txt, key=f"e_toggle_{ev['id']}"):
                        new_st = "마감" if ev['status'] == "진행 중" else "진행 중"
                        db_update_event_status(ev['id'], new_st)
                        db_add_log("행사 상태 변경", f"[{ev['name']}] -> {new_st}", st.session_state.staff_info)
                        st.rerun()
            else:
                st.info("생성된 행사가 없습니다. 왼쪽에서 새 행사를 만들어주세요.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------
    # 탭 3: 통계 대시보드 (시각화 차트 추가)
    # --------------------------------------
    with tab_nav3:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        st.markdown("<h4>통합 통계 대시보드 및 시각화</h4>", unsafe_allow_html=True)
        
        df_all = db_get_participants()
        if df_all.empty:
            st.info("통계를 산출할 참여 데이터가 없습니다.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-val">{len(df_all)}명</div><div class="metric-lbl">누적 총 참여자</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-val">{len(df_all["event_name"].unique())}개</div><div class="metric-lbl">진행 행사 수</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-val">{df_all["grade"].value_counts().idxmax()}학년</div><div class="metric-lbl">최다 참여 학년</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card"><div class="metric-val">{df_all["class"].value_counts().idxmax()}반</div><div class="metric-lbl">최다 참여 반</div></div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 행사별 참여자 시각화 차트")
            event_counts = df_all['event_name'].value_counts()
            st.bar_chart(event_counts)
            
            st.markdown("<br>", unsafe_allow_html=True)
            t1, t2, t3, t4 = st.tabs(["행사별 통계", "학년별 통계", "반별 통계", "날짜별 통계"])
            with t1:
                st.dataframe(df_all['event_name'].value_counts().reset_index().rename(columns={'index':'행사명', 'event_name':'참여자 수'}), use_container_width=True, hide_index=True)
            with t2:
                st.dataframe(df_all['grade'].value_counts().reset_index().rename(columns={'index':'학년', 'grade':'참여자 수'}), use_container_width=True, hide_index=True)
            with t3:
                st.dataframe(df_all['class'].value_counts().reset_index().rename(columns={'index':'반', 'class':'참여자 수'}), use_container_width=True, hide_index=True)
            with t4:
                df_all['date_only'] = df_all['timestamp'].str.split().str[0]
                st.dataframe(df_all['date_only'].value_counts().reset_index().rename(columns={'index':'날짜', 'date_only':'참여자 수'}), use_container_width=True, hide_index=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="통계 데이터 CSV 파일 다운로드",
                data=csv_data,
                file_name=f"도서관_행사_참여통계_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------
    # 탭 4: 처리 이력 (Audit Log)
    # --------------------------------------
    with tab_nav4:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        st.markdown("<h4>시스템 처리 이력 (Audit Log)</h4>", unsafe_allow_html=True)
        
        df_l = db_get_logs()
        if df_l.empty:
            st.info("기록된 처리 이력이 없습니다.")
        else:
            lt1, lt2, lt3, lt4 = st.tabs(["행사 생성 기록", "참여자 등록 기록", "시스템 접속 기록", "기타 변경 기록"])
            with lt1:
                st.dataframe(df_l[df_l['category'] == '행사 생성'], use_container_width=True, hide_index=True)
            with lt2:
                st.dataframe(df_l[df_l['category'] == '참여자 등록'], use_container_width=True, hide_index=True)
            with lt3:
                st.dataframe(df_l[df_l['category'] == '시스템 접속'], use_container_width=True, hide_index=True)
            with lt4:
                st.dataframe(df_l[~df_l['category'].isin(['행사 생성', '참여자 등록', '시스템 접속'])], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------
    # 탭 5: 시스템 백업 및 복원 (데이터 유실 방지)
    # --------------------------------------
    with tab_nav5:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        st.markdown("<h4>데이터베이스 백업 및 복원</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px; color:#8B95A1;'>현재까지 저장된 모든 영구 데이터 파일(`.db`)을 백업하거나 복원할 수 있습니다.</p>", unsafe_allow_html=True)
        
        # 백업 버튼
        with open("library_system.db", "rb") as f:
            db_bytes = f.read()
        st.download_button(
            label="현재 데이터베이스 파일 백업(.db 다운로드)",
            data=db_bytes,
            file_name=f"library_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            mime="application/octet-stream"
        )
        
        st.markdown("---")
        st.markdown("##### 데이터베이스 복원 (기존 데이터 교체)")
        uploaded_db = st.file_uploader("백업해 둔 .db 파일을 업로드하세요", type=["db"])
        if uploaded_db is not None:
            if st.button("업로드한 파일로 데이터베이스 복원하기"):
                with open("library_system.db", "wb") as f:
                    f.write(uploaded_db.getbuffer())
                st.success("데이터베이스가 성공적으로 복원되었습니다! 새로고침 해주세요.")
                db_add_log("시스템 복원", "데이터베이스 파일 복원 완료", st.session_state.staff_info)
        st.markdown('</div>', unsafe_allow_html=True)
