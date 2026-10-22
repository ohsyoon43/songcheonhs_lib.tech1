import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. 페이지 기본 설정 및 토스뱅크 스타일 CSS (이모지 제거 버전)
# ==========================================
st.set_page_config(
    page_title="송천 도서관 행사 관리 시스템",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #FAFAFB;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    .stButton>button {
        width: 100%;
        background-color: #3182F6 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        height: 52px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(49, 130, 246, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1B64DA !important;
        transform: translateY(-1px);
    }
    
    .clear-btn > button {
        background-color: #E5E8EB !important;
        color: #4E5968 !important;
        box-shadow: none !important;
        height: 40px !important;
        font-size: 14px !important;
    }

    .toss-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #F2F4F6;
        margin-bottom: 16px;
    }
    
    .top-bar {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 12px 20px;
        border: 1px solid #E5E8EB;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    
    .metric-box {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #E5E8EB;
        text-align: center;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        color: #3182F6;
    }
    .metric-label {
        font-size: 14px;
        color: #8B95A1;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 세션 데이터 초기화
# ==========================================
if 'events' not in st.session_state:
    st.session_state.events = [
        {"id": 1, "name": "2026 가을 독서퀴즈 골든벨", "status": "진행 중", "created_at": "2026-10-22 09:00:00"},
        {"id": 2, "name": "나만의 북마크 만들기 체험", "status": "진행 중", "created_at": "2026-10-22 10:00:00"}
    ]

if 'participants' not in st.session_state:
    st.session_state.participants = []

if 'logs' not in st.session_state:
    st.session_state.logs = []

# 학번 파싱 함수 (5자리 -> 학년, 반, 번호)
def parse_student_id(std_id):
    if len(str(std_id)) == 5 and str(std_id).isdigit():
        grade = int(str(std_id)[0])
        class_num = int(str(std_id)[1:3])
        number = int(str(std_id)[3:5])
        return True, grade, class_num, number
    return False, None, None, None

# 처리 이력 기록 함수
def add_log(category, detail, user_type="관계자"):
    st.session_state.logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "detail": detail,
        "operator": user_type
    })

# ==========================================
# 3. 사이드바 (권한 및 메뉴 선택)
# ==========================================
st.sidebar.title("송천 도서관")

user_role = st.sidebar.radio("접속 권한 선택", ["일반 참여자", "도서관 관계자"])

admin_authenticated = False
if user_role == "도서관 관계자":
    pwd = st.sidebar.text_input("관계자 비밀번호", type="password")
    if pwd == "1234":
        admin_authenticated = True
        st.sidebar.success("관계자 인증 완료")
    else:
        st.sidebar.warning("비밀번호를 입력해주세요.")

menu_options = ["참여자 등록", "통계 대시보드"]
if user_role == "도서관 관계자" and admin_authenticated:
    menu_options.insert(1, "행사 생성 및 관리")
    menu_options.append("처리 이력 (Audit Log)")

selected_menu = st.sidebar.selectbox("메뉴 이동", menu_options)

# ==========================================
# 4. 메뉴별 화면 구현
# ==========================================

# 메뉴 1: 참여자 등록 (좌측 입력 1 : 우측 검색 3 분할)
if selected_menu == "참여자 등록":
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(1 for p in st.session_state.participants if p['timestamp'].startswith(today_str))
    active_events = sum(1 for e in st.session_state.events if e['status'] == "진행 중")
    
    st.markdown(f"""
        <div class="top-bar">
            <span style="font-size: 16px; font-weight: 700; color: #191F28;">현황 안내</span>
            <span style="color: #4E5968;">오늘의 총 참여자: <b style="color:#3182F6;">{today_count}명</b> &nbsp;|&nbsp; 진행 중인 행사: <b style="color:#3182F6;">{active_events}개</b></span>
        </div>
    """, unsafe_allow_html=True)
    
    left_col, right_col = st.columns([1, 3])
    
    with left_col:
        st.markdown("### 참여 등록")
        
        event_names = [f"[{e['status']}] {e['name']}" for e in st.session_state.events]
        selected_event_str = st.selectbox("참여할 행사 선택", event_names if event_names else ["등록된 행사 없음"])
        
        if 'input_std_id' not in st.session_state:
            st.session_state.input_std_id = ""
        if 'input_name' not in st.session_state:
            st.session_state.input_name = ""
            
        def clear_inputs():
            st.session_state.input_std_id = ""
            st.session_state.input_name = ""

        std_id_input = st.text_input("학번 (5자리 예: 20601)", value=st.session_state.input_std_id, key="std_id_key")
        name_input = st.text_input("이름", value=st.session_state.input_name, key="name_key")
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            submit_btn = st.button("등록하기")
        with col_btn2:
            st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
            st.button("전체 지우기", on_click=clear_inputs)
            st.markdown('</div>', unsafe_allow_html=True)

        custom_datetime = None
        if user_role == "도서관 관계자" and admin_authenticated:
            with st.expander("[관리자] 일시 수동 지정 (소급 등록)"):
                custom_date = st.date_input("날짜 지정", datetime.now())
                custom_time = st.time_input("시간 지정", datetime.now().time())
                custom_datetime = f"{custom_date} {custom_time.strftime('%H:%M:%S')}"

        if submit_btn:
            if not selected_event_str or "등록된 행사 없음" in selected_event_str:
                st.error("행사를 먼저 선택해 주세요.")
            elif "마감" in selected_event_str and (user_role != "도서관 관계자" or not admin_authenticated):
                st.error("마감된 행사입니다. 누락자 등록은 도서관 관계자에게 문의하세요.")
            else:
                is_valid, grade, class_num, number = parse_student_id(std_id_input)
                if not is_valid or not name_input.strip():
                    st.error("올바른 5자리 학번과 이름을 입력해 주세요.")
                else:
                    event_name_clean = selected_event_str.split("] ")[-1]
                    reg_time = custom_datetime if custom_datetime else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    operator_type = "도서관 관계자" if (user_role == "도서관 관계자" and admin_authenticated) else "참여자 본인"
                    
                    new_entry = {
                        "event_name": event_name_clean,
                        "student_id": std_id_input,
                        "grade": grade,
                        "class": class_num,
                        "number": number,
                        "name": name_input.strip(),
                        "timestamp": reg_time,
                        "operator": operator_type
                    }
                    st.session_state.participants.append(new_entry)
                    add_log("참여자 등록", f"[{event_name_clean}] {std_id_input} {name_input} 등록 완료", operator_type)
                    st.success(f"{name_input}님({std_id_input}) 등록이 완료되었습니다!")

    with right_col:
        st.markdown("### 실시간 당일 참여 이력 검색")
        
        search_query = st.text_input("학번 또는 이름으로 검색해 보세요", placeholder="예: 20601 또는 홍길동")
        
        df_part = pd.DataFrame(st.session_state.participants)
        if not df_part.empty:
            df_part_today = df_part[df_part['timestamp'].str.startswith(today_str)]
            
            if search_query.strip():
                filtered_df = df_part_today[
                    df_part_today['student_id'].astype(str).str.contains(search_query) | 
                    df_part_today['name'].str.contains(search_query)
                ]
            else:
                filtered_df = df_part_today

            if not filtered_df.empty:
                display_df = filtered_df[['timestamp', 'event_name', 'student_id', 'grade', 'class', 'name', 'operator']].copy()
                display_df.columns = ['참여 시간', '행사명', '학번', '학년', '반', '이름', '등록 주체']
                st.dataframe(display_df.sort_values(by='참여 시간', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("검색 조건에 맞는 당일 참여 기록이 없습니다.")
        else:
            st.info("아직 등록된 참여 내역이 없습니다.")

# 메뉴 2: 행사 생성 및 관리 (관계자 전용)
elif selected_menu == "행사 생성 및 관리":
    st.markdown("## 행사 생성 및 상태 관리")
    
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        st.markdown("#### 신규 행사 생성")
        new_event_name = st.text_input("행사명 입력")
        if st.button("행사 만들기"):
            if new_event_name.strip():
                new_id = len(st.session_state.events) + 1
                st.session_state.events.append({
                    "id": new_id,
                    "name": new_event_name.strip(),
                    "status": "진행 중",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                add_log("행사 생성", f"신규 행사 [{new_event_name}] 생성", "도서관 관계자")
                st.success(f"[{new_event_name}] 행사가 생성되었습니다!")
                st.rerun()
            else:
                st.error("행사명을 입력하세요.")
                
    with col_c2:
        st.markdown("#### 기존 행사 상태 변경 (진행 중 / 마감)")
        for idx, ev in enumerate(st.session_state.events):
            c_name, c_status, c_btn = st.columns([3, 1, 1])
            c_name.write(f"**{ev['name']}** ({ev['created_at']})")
            c_status.write(f"`{ev['status']}`")
            btn_label = "마감하기" if ev['status'] == "진행 중" else "재개하기"
            if c_btn.button(btn_label, key=f"ev_btn_{idx}"):
                st.session_state.events[idx]['status'] = "마감" if ev['status'] == "진행 중" else "진행 중"
                add_log("행사 상태 변경", f"[{ev['name']}] 상태를 {st.session_state.events[idx]['status']}(으)로 변경", "도서관 관계자")
                st.rerun()

# 메뉴 3: 통계 대시보드
elif selected_menu == "통계 대시보드":
    st.markdown("## 통계 대시보드")
    
    df_all = pd.DataFrame(st.session_state.participants)
    
    if df_all.empty:
        st.info("통계를 산출할 참여 데이터가 아직 없습니다.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="metric-box"><div class="metric-value">{len(df_all)}명</div><div class="metric-label">전체 누적 참여자</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-box"><div class="metric-value">{len(df_all["event_name"].unique())}개</div><div class="metric-label">진행된 총 행사</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-box"><div class="metric-value">{df_all["grade"].value_counts().idxmax()}학년</div><div class="metric-label">최다 참여 학년</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-box"><div class="metric-value">{df_all["class"].value_counts().idxmax()}반</div><div class="metric-label">최다 참여 반</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["행사별 통계", "학년별 통계", "반별 통계", "날짜별 통계"])
        
        with tab1:
            st.dataframe(df_all['event_name'].value_counts().reset_index().rename(columns={'index':'행사명', 'event_name':'참여자 수'}), use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(df_all['grade'].value_counts().reset_index().rename(columns={'index':'학년', 'grade':'참여자 수'}), use_container_width=True, hide_index=True)
        with tab3:
            st.dataframe(df_all['class'].value_counts().reset_index().rename(columns={'index':'반', 'class':'참여자 수'}), use_container_width=True, hide_index=True)
        with tab4:
            df_all['date'] = df_all['timestamp'].str.split().str[0]
            st.dataframe(df_all['date'].value_counts().reset_index().rename(columns={'index':'날짜', 'date':'참여자 수'}), use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.markdown("### 엑셀 / CSV 파일 다운로드")
        csv_data = df_all.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="전체 통계 데이터 CSV 다운로드",
            data=csv_data,
            file_name=f"도서관_행사_참여통계_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# 메뉴 4: 처리 이력 (Audit Log)
elif selected_menu == "처리 이력 (Audit Log)":
    st.markdown("## 시스템 처리 이력 (Audit Log)")
    
    df_logs = pd.DataFrame(st.session_state.logs)
    if df_logs.empty:
        st.info("기록된 처리 이력이 없습니다.")
    else:
        log_tab1, log_tab2, log_tab3, log_tab4 = st.tabs(["1. 행사 생성 기록", "2. 참여자 등록 기록", "3. 통계 및 다운로드", "4. 시스템 처리 기록"])
        
        with log_tab1:
            st.dataframe(df_logs[df_logs['category'] == '행사 생성'], use_container_width=True, hide_index=True)
        with log_tab2:
            st.dataframe(df_logs[df_logs['category'] == '참여자 등록'], use_container_width=True, hide_index=True)
        with log_tab3:
            st.dataframe(df_logs[df_logs['category'] == '통계 조회'], use_container_width=True, hide_index=True)
        with log_tab4:
            st.dataframe(df_logs[df_logs['category'].isin(['행사 상태 변경', '수정 및 삭제'])], use_container_width=True, hide_index=True)