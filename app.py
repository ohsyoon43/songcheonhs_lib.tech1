import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3

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

# DB 쿼리 함수
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
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
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

def db_clear_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs")
    conn.commit()
    conn.close()

# ==========================================
# 2. 페이지 설정 및 PC 최적화 글로벌 CSS
# ==========================================
st.set_page_config(
    page_title="송천 도서관 행정 시스템",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

    /* 전체 앱 배경 및 폰트 */
    .stApp {
        background-color: #F8FAFC !important;
        font-family: "Pretendard Variable", Pretendard, sans-serif !important;
        color: #0F172A !important;
    }

    html, body, [class*="css"], .stMarkdown, p, div, label, span {
        font-family: "Pretendard Variable", Pretendard, sans-serif !important;
        color: #1E293B;
    }

    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
        padding-top: 20px;
    }

    /* 메인 버튼 스타일 (선명한 블루 + 흰색 글씨) */
    .stButton>button {
        width: 100%;
        background: #2563EB !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        height: 46px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button span, .stButton>button p {
        color: #FFFFFF !important;
        font-size: 15px !important;
    }
    .stButton>button:hover {
        background: #1D4ED8 !important;
        transform: translateY(-1px);
    }

    /* 입력 폼 필드 스타일 */
    .stTextInput input, .stSelectbox select {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        height: 44px !important;
    }

    /* 대시보드 지표 카드 스타일 */
    .metric-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        text-align: center;
    }
    .metric-num {
        font-size: 28px;
        font-weight: 800;
        color: #2563EB;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* 타이틀 크기 고정 */
    h1 { font-size: 28px !important; font-weight: 800 !important; color: #0F172A !important; }
    h2 { font-size: 24px !important; font-weight: 800 !important; color: #0F172A !important; }
    h3 { font-size: 20px !important; font-weight: 700 !important; color: #0F172A !important; }
    h4 { font-size: 16px !important; font-weight: 700 !important; color: #0F172A !important; }
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
# 3. 사이드바 네비게이션 및 시스템 제어
# ==========================================
st.sidebar.markdown("### 🏛️ 송천고 도서관 시스템")
st.sidebar.markdown("<p style='font-size: 13px; color: #64748B; margin-top: -10px;'>Library Event & Attendance</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'staff_info' not in st.session_state:
    st.session_state.staff_info = None

# 사이드바 메뉴 선택
menu_mode = st.sidebar.radio(
    "접속 메뉴 선택", 
    ["🏠 홈 (메인 화면)", "📝 학생 참여 등록 (키오스크)", "🔑 도서관 관리자 시스템"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 12px; color: #94A3B8; text-align: center;'>Incheon Songcheon High School<br>Library Management System v2.0</p>", unsafe_allow_html=True)

# 메뉴 모드에 따른 세션 동기화
if menu_mode == "🏠 홈 (메인 화면)":
    st.session_state.user_role = None
elif menu_mode == "📝 학생 참여 등록 (키오스크)":
    st.session_state.user_role = 'participant'
elif menu_mode == "🔑 도서관 관리자 시스템":
    if st.session_state.user_role != 'staff':
        st.session_state.user_role = 'staff_login'

# ==========================================
# 4. 화면별 렌더링 (PC 최적화 대시보드)
# ==========================================

# ------------------------------------------
# [홈 화면]
# ------------------------------------------
if st.session_state.user_role is None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("# 📚 인천송천고등학교 도서관")
    st.markdown("도서관 행사 참여 출석 확인 및 통합 데이터 관리 시스템에 오신 것을 환영합니다.")
    st.markdown("<br>", unsafe_allow_html=True)

    # 상단 요약 지표 카드
    df_all_p = db_get_participants()
    df_events = db_get_events()
    total_participants = len(df_all_p) if not df_all_p.empty else 0
    active_events = len(df_events[df_events['status'] == '진행 중']) if not df_events.empty else 0
    total_events = len(df_events) if not df_events.empty else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">누적 총 참여 건수</div>
                <div class="metric-num">{total_participants}명</div>
            </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">진행 중인 행사</div>
                <div class="metric-num" style="color: #10B981;">{active_events}개</div>
            </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">등록된 전체 행사</div>
                <div class="metric-num" style="color: #6366F1;">{total_events}개</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 빠른 진입 카드 영역
    col_c1, col_c2 = st.columns(2, gap="large")
    with col_c1:
        st.markdown("### 📝 학생 참여 등록")
        st.markdown("도서관 행사에 참여한 학생분들께서 직접 학번과 이름을 입력하여 출석을 등록하는 공간입니다.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("학생 참여 등록 페이지로 이동하기"):
            st.session_state.user_role = 'participant'
            st.rerun()
            
    with col_c2:
        st.markdown("### 🔑 도서관 관리자 시스템")
        st.markdown("사서 선생님 및 도서부원 전용 공간으로, 행사 개설, 출석 관리, 통계 및 백업을 수행합니다.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("관리자 로그인 페이지로 이동하기"):
            st.session_state.user_role = 'staff_login'
            st.rerun()

# ------------------------------------------
# [학생 참여 등록 화면]
# ------------------------------------------
elif st.session_state.user_role == 'participant':
    st.markdown("## 📝 도서관 행사 참여 등록")
    st.markdown("참여 중이신 행사를 선택하고 학번과 이름을 입력해 주세요.")
    st.markdown("---")

    col_p1, col_p2 = st.columns([1.2, 1], gap="large")
    with col_p1:
        df_events = db_get_events()
        all_events_list = [f"[{row['status']}] {row['name']}" for _, row in df_events.iterrows()] if not df_events.empty else ["등록된 행사 없음"]
                    
        selected_event_str = st.selectbox("참여할 행사 선택", all_events_list)
        std_id_p = st.text_input("학번 입력 (5자리)", placeholder="예: 10101")
        name_p = st.text_input("이름 입력", placeholder="예: 김송천")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("출석 등록 완료"):
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
                st.success(f"🎉 등록 완료: {grade}학년 {class_num}반 {name_p.strip()}님, 정상 등록되었습니다!")

    with col_p2:
        st.markdown("### 💡 이용 안내")
        st.info(
            "1. **학번 형식**: 반드시 5자리 숫자로 입력해 주세요 (예: 1학년 1반 1번 -> `10101`).\n"
            "2. **행사 상태**: `[진행 중]` 상태인 행사만 참여 등록이 가능합니다.\n"
            "3. **문의 사항**: 등록에 실패하거나 오류가 발생할 경우 도서관 데스크의 도서부원에게 문의해 주세요."
        )

# ------------------------------------------
# [관리자 로그인 화면]
# ------------------------------------------
elif st.session_state.user_role == 'staff_login':
    st.markdown("## 🔑 도서관 관리자 인증")
    st.markdown("시스템 관리를 위해 담당자 정보를 입력해 주세요.")
    st.markdown("---")

    col_l1, col_l2 = st.columns([1, 1.2], gap="large")
    with col_l1:
        staff_type = st.selectbox("직위 구분", ["도서부원", "사서교사"])
        
        if staff_type == "도서부원":
            staff_std_id = st.text_input("학번 (5자리)", placeholder="예: 10101")
            staff_name = st.text_input("이름", placeholder="예: 김송천")
        else:
            staff_std_id = "교직원"
            staff_name = st.text_input("이름", placeholder="예: 담당선생님")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("관리자 시스템 접속"):
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
                    
    with col_l2:
        st.markdown("### 🔒 보안 및 권한 안내")
        st.warning(
            "관리자 권한을 통해 도서관 행사를 개설·마감하고, 학생들의 출석 기록을 수정·삭제할 수 있습니다.\n\n"
            "작업 완료 후에는 반드시 상단 또는 메뉴에서 로그아웃을 진행해 주세요."
        )

# ------------------------------------------
# [관리자 행정 대시보드 시스템]
# ------------------------------------------
elif st.session_state.user_role == 'staff':
    # 상단 관리자 타이틀 및 로그아웃 바
    top_c1, top_c2 = st.columns([8, 2])
    with top_c1:
        st.markdown(f"## ⚙️ 도서관 행정 대시보드")
        st.markdown(f"현재 접속 담당자: **{st.session_state.staff_info}**")
    with top_c2:
        if st.button("로그아웃"):
            st.session_state.user_role = None
            st.session_state.staff_info = None
            st.rerun()
            
    st.markdown("---")
    
    # PC 최적화 상단 탭 네비게이션
    tab_nav1, tab_nav2, tab_nav3, tab_nav4, tab_nav5 = st.tabs([
        "📋 참여자 출석 등록 및 관리", 
        "🏷️ 행사 개설 및 마감 관리", 
        "📊 통합 통계 대시보드", 
        "📜 처리 이력 (Audit Log)", 
        "💾 백업 및 복원"
    ])
    
    # --------------------------------------
    # 탭 1: 참여자 출석 등록 및 관리
    # --------------------------------------
    with tab_nav1:
        df_all_p = db_get_participants()
        df_events = db_get_events()
        
        col_s1, col_s2 = st.columns([1, 1.5], gap="large")
        
        with col_s1:
            st.markdown("### 1. 학생 검색")
            st.markdown("학번과 이름을 입력하면 과거 참여 이력이 조회됩니다.")
            search_std_id = st.text_input("학번 입력 (5자리)", key="staff_search_id", placeholder="예: 10101")
            search_name = st.text_input("이름 입력", key="staff_search_name", placeholder="예: 김송천")
            
            student_history = []
            is_valid_student = False
            grade, class_num, number = None, None, None
            
            if search_std_id.strip() and search_name.strip():
                is_valid_student, grade, class_num, number = parse_student_id(search_std_id)
                if is_valid_student and not df_all_p.empty:
                    student_history = df_all_p[df_all_p['student_id'] == search_std_id.strip()].to_dict('records')
            
            st.markdown("<hr style='border-color:#E2E8F0; margin: 20px 0;'>", unsafe_allow_html=True)
            st.markdown("#### 📖 과거 참여 이력 조회결과")
            if search_std_id.strip():
                if student_history:
                    st.success(f"총 {len(student_history)}건의 참여 이력이 있습니다.")
                    for hist in student_history:
                        st.markdown(f"- **{hist['event_name']}** ({hist['timestamp']})")
                else:
                    st.info("과거 참여 이력이 없습니다.")
            else:
                st.markdown("<p style='color: #94A3B8; font-size: 14px;'>학번을 입력하면 과거 기록이 나타납니다.</p>", unsafe_allow_html=True)
            
        with col_s2:
            st.markdown("### 2. 행사 출석 확인 및 등록")
            st.markdown("이전 참여 이력 유무와 관계없이 행사를 선택하여 등록할 수 있습니다.")
            
            all_events_list = [f"[{row['status']}] {row['name']}" for _, row in df_events.iterrows()] if not df_events.empty else ["등록된 행사 없음"]
            selected_event_str = st.selectbox("등록할 행사 선택", all_events_list)
            
            with st.expander("⏱️ 일시 수동 지정 (소급 등록 필요 시)"):
                c_date = st.date_input("날짜 선택", date.today())
                c_time = st.time_input("시간 선택", datetime.now().time())
                custom_datetime_str = f"{c_date} {c_time.strftime('%H:%M:%S')}"
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("출석 등록 완료 처리"):
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
                    st.success(f"✨ {search_name.strip()}님 출석 등록 완료!")
                    st.rerun()
            
            st.markdown("<hr style='border-color:#E2E8F0; margin: 30px 0;'>", unsafe_allow_html=True)
            st.markdown("### 📋 금일 참여자 출석 현황 및 관리")
            today_str = datetime.now().strftime("%Y-%m-%d")
            if not df_all_p.empty:
                df_today = df_all_p[df_all_p['timestamp'].str.startswith(today_str)]
                if not df_today.empty:
                    for _, row in df_today.iterrows():
                        c_info, c_del, c_edit = st.columns([3, 1, 1])
                        c_info.write(f"[{row['timestamp']}] **{row['event_name']}** - {row['student_id']} {row['name']}")
                        
                        if c_del.button("삭제", key=f"del_{row['id']}"):
                            db_delete_participant(row['id'])
                            db_add_log("데이터 삭제", f"참여자 ID {row['id']} 삭제됨", st.session_state.staff_info)
                            st.rerun()
                        
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

    # --------------------------------------
    # 탭 2: 행사 개설 및 마감 관리
    # --------------------------------------
    with tab_nav2:
        st.markdown("<br>", unsafe_allow_html=True)
        col_e1, col_e2 = st.columns([1, 1.8], gap="large")
        with col_e1:
            st.markdown("### 🏷️ 신규 행사 개설")
            new_e_name = st.text_input("새 행사명 입력", placeholder="예: 2026 겨울 독서 캠프")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("행사 개설하기"):
                if new_e_name.strip():
                    db_add_event(new_e_name.strip(), "진행 중", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    db_add_log("행사 생성", f"신규 행사 [{new_e_name.strip()}] 생성", st.session_state.staff_info)
                    st.success(f"[{new_e_name.strip()}] 행사가 개설되었습니다.")
                    st.rerun()
                else:
                    st.error("행사명을 입력해 주세요.")
                    
        with col_e2:
            st.markdown("### 📋 개설된 행사 목록 및 관리")
            df_evs = db_get_events()
            if not df_evs.empty:
                for _, ev in df_evs.iterrows():
                    l_col, m_col, r_col = st.columns([2.5, 1, 1])
                    l_col.write(f"**{ev['name']}** (상태: `{ev['status']}`)")
                    
                    btn_txt = "마감하기" if ev['status'] == "진행 중" else "재개하기"
                    if m_col.button(btn_txt, key=f"e_toggle_{ev['id']}"):
                        new_st = "마감" if ev['status'] == "진행 중" else "진행 중"
                        db_update_event_status(ev['id'], new_st)
                        db_add_log("행사 상태 변경", f"[{ev['name']}] -> {new_st}", st.session_state.staff_info)
                        st.rerun()
                        
                    if ev['status'] == "마감":
                        with r_col.expander("행사 삭제"):
                            st.warning("⚠️ 해당 행사에 포함된 모든 학생의 참여 기록도 함께 완전히 삭제됩니다!")
                            if st.button("영구 삭제", key=f"e_del_{ev['id']}"):
                                db_delete_event_and_records(ev['id'], ev['name'])
                                db_add_log("행사 삭제", f"행사 [{ev['name']}] 영구 삭제 완료", st.session_state.staff_info)
                                st.success("삭제되었습니다.")
                                st.rerun()
                    else:
                        r_col.write("-")
            else:
                st.info("개설된 행사가 없습니다.")

    # --------------------------------------
    # 탭 3: 통계 대시보드
    # --------------------------------------
    with tab_nav3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 통합 통계 대시보드 및 시각화")
        df_all = db_get_participants()
        if df_all.empty:
            st.info("통계를 산출할 참여 데이터가 없습니다.")
        else:
            st.bar_chart(df_all['event_name'].value_counts())
            st.markdown("<br>", unsafe_allow_html=True)
            t1, t2 = st.tabs(["행사별 통계 테이블", "학년별 통계 테이블"])
            with t1:
                st.dataframe(df_all['event_name'].value_counts().reset_index(), use_container_width=True, hide_index=True)
            with t2:
                st.dataframe(df_all['grade'].value_counts().reset_index(), use_container_width=True, hide_index=True)

    # --------------------------------------
    # 탭 4: 처리 이력 (Audit Log)
    # --------------------------------------
    with tab_nav4:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📜 시스템 감사 로그 (Audit Log)")
        df_l = db_get_logs()
        if not df_l.empty:
            st.dataframe(df_l, use_container_width=True, hide_index=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("⚠️ 처리 이력(로그) 전체 비우기"):
                st.warning("모든 시스템 감사 로그가 데이터베이스에서 영구적으로 삭제됩니다.")
                if st.button("모든 처리 이력 삭제 실행"):
                    db_clear_logs()
                    st.success("모든 처리 이력이 비워졌습니다.")
                    st.rerun()
        else:
            st.info("기록된 처리 이력이 없습니다.")

    # --------------------------------------
    # 탭 5: 백업 및 복원
    # --------------------------------------
    with tab_nav5:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 💾 데이터베이스 백업 및 복원")
        st.markdown("현재 영구 저장된 모든 SQLite 데이터베이스 파일(`library_system.db`)을 백업하거나 복원합니다.")
        
        with open("library_system.db", "rb") as f:
            db_bytes = f.read()
        st.download_button(
            label="데이터베이스 파일 백업 (.db 다운로드)",
            data=db_bytes,
            file_name=f"library_backup_{datetime.now().strftime('%Y%m%d')}.db",
            mime="application/octet-stream"
        )
