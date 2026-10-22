import streamlit as st
import pandas as pd
from datetime import datetime, date

# ==========================================
# 1. 페이지 기본 설정 및 토스뱅크 스타일 CSS
# ==========================================
st.set_page_config(
    page_title="송천 도서관 행사 관리 시스템",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    /* 전체 배경 및 폰트 설정 */
    .main {
        background-color: #F2F4F6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* 중앙 정렬용 카운터/로그인 카드 */
    .center-card {
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 32px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        border: 1px solid #E5E8EB;
        max-width: 500px;
        margin: 40px auto;
        text-align: center;
    }
    
    /* 토스 블루 버튼 디자인 */
    .stButton>button {
        width: 100%;
        background-color: #3182F6 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        height: 48px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(49, 130, 246, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1B64DA !important;
    }
    
    /* 보조/지우기 버튼 */
    .sub-btn > button {
        background-color: #E5E8EB !important;
        color: #4E5968 !important;
        box-shadow: none !important;
    }

    /* 카드 컨테이너 */
    .toss-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #E5E8EB;
        margin-bottom: 16px;
    }
    
    /* 상단 요약 바 */
    .top-summary-bar {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 12px 20px;
        border: 1px solid #E5E8EB;
        margin-bottom: 16px;
        font-size: 14px;
        color: #4E5968;
    }
    
    /* 지표 카드 */
    .metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #E5E8EB;
        text-align: center;
    }
    .metric-val {
        font-size: 28px;
        font-weight: 800;
        color: #3182F6;
    }
    .metric-lbl {
        font-size: 13px;
        color: #8B95A1;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 세션 관리
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

if 'user_role' not in st.session_state:
    st.session_state.user_role = None  # None, 'participant', 'staff'

if 'staff_info' not in st.session_state:
    st.session_state.staff_info = None  # 관계자 정보 저장

# 학번 자동 파싱 (5자리 -> 학년, 반, 번호)
def parse_student_id(std_id):
    std_str = str(std_id).strip()
    if len(std_str) == 5 and std_str.isdigit():
        grade = int(std_str[0])
        class_num = int(std_str[1:3])
        number = int(std_str[3:5])
        return True, grade, class_num, number
    return False, None, None, None

# 처리 이력 로그 추가 함수
def add_log(category, detail, operator):
    st.session_state.logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "detail": detail,
        "operator": operator
    })

# ==========================================
# 3. 메인 접속 진입로 (초기 선택 화면)
# ==========================================
if st.session_state.user_role is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #191F28;'>송천 도서관 행사 관리 시스템</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8B95A1;'>접속하실 유형을 선택해 주세요.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        btn_participant = st.button("일반 참여자 등록용 접속")
        st.markdown("<br>", unsafe_allow_html=True)
        btn_staff = st.button("도서관 관계자용 접속")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if btn_participant:
            st.session_state.user_role = 'participant'
            st.rerun()
        if btn_staff:
            st.session_state.user_role = 'staff_login'
            st.rerun()

# ==========================================
# 4. 도서관 관계자 정보 입력 화면
# ==========================================
elif st.session_state.user_role == 'staff_login':
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        st.markdown("### 도서관 관계자 정보 확인")
        st.markdown("<p style='color:#8B95A1; font-size:14px;'>처리 담당자 정보를 입력 후 접속해 주세요.</p>", unsafe_allow_html=True)
        
        staff_type = st.selectbox("직위 선택", ["도서부원", "사서교사"])
        
        if staff_type == "도서부원":
            staff_std_id = st.text_input("학번 (5자리)", placeholder="예: 20601")
            staff_name = st.text_input("이름", placeholder="예: 홍길동")
        else:
            staff_std_id = "교직원"
            staff_name = st.text_input("이름", placeholder="예: 김사서")
            
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
                        add_log("시스템 접속", f"{st.session_state.staff_info} 접속함", st.session_state.staff_info)
                        st.rerun()
                else:
                    if not staff_name.strip():
                        st.error("이름을 입력해 주세요.")
                    else:
                        st.session_state.staff_info = f"사서교사 {staff_name.strip()}"
                        st.session_state.user_role = 'staff'
                        add_log("시스템 접속", f"{st.session_state.staff_info} 접속함", st.session_state.staff_info)
                        st.rerun()
        with c_btn2:
            st.markdown('<div class="sub-btn">', unsafe_allow_html=True)
            if st.button("처음으로"):
                st.session_state.user_role = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 일반 참여자 전용 화면 (학원 등원 키오스크 스타일)
# ==========================================
elif st.session_state.user_role == 'participant':
    top_l, top_r = st.columns([8, 2])
    with top_l:
        st.markdown("## 송천 도서관 행사 참여 등록")
    with top_r:
        if st.button("처음 화면으로"):
            st.session_state.user_role = None
            st.rerun()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        
        # 진행 중인 행사 선택
        active_events = [e['name'] for e in st.session_state.events if e['status'] == "진행 중"]
        all_events = [f"[{e['status']}] {e['name']}" for e in st.session_state.events]
        
        selected_event_str = st.selectbox("참여할 행사 선택", all_events if all_events else ["진행 중인 행사 없음"])
        
        std_id_p = st.text_input("학번 입력 (5자리)", placeholder="예: 20601")
        name_p = st.text_input("이름 입력", placeholder="예: 홍길동")
        
        if st.button("참여 등록하기"):
            is_v, grade, class_num, number = parse_student_id(std_id_p)
            
            if not selected_event_str or "행사 없음" in selected_event_str:
                st.error("등록 실패: 선택 가능한 행사가 없습니다. 관리자에게 문의해 주세요.")
            elif "[마감]" in selected_event_str:
                st.error("등록 실패: 마감된 행사입니다. 관리자(도서부원)에게 문의해 주세요.")
            elif not is_v or not name_p.strip():
                st.error("등록 실패: 올바른 5자리 학번과 이름을 입력해 주세요.")
            else:
                event_clean = selected_event_str.split("] ")[-1] if "]" in selected_event_str else selected_event_str
                reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                st.session_state.participants.append({
                    "event_name": event_clean,
                    "student_id": std_id_p.strip(),
                    "grade": grade,
                    "class": class_num,
                    "number": number,
                    "name": name_p.strip(),
                    "timestamp": reg_time,
                    "operator": "참여자 본인"
                })
                add_log("참여자 등록", f"[{event_clean}] {std_id_p} {name_p} 등록 완료", "참여자 본인")
                
                st.success(f"등록 완료: {grade}학년 {class_num}반 {name_p}님, {event_clean} 참여가 정상 등록되었습니다!")
                
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. 도서관 관계자 전용 메인 시스템
# ==========================================
elif st.session_state.user_role == 'staff':
    
    # 상단 담당자 상태 바
    top_col1, top_col2 = st.columns([8, 2])
    with top_col1:
        st.markdown(f"### 송천 도서관 관리 시스템 `담당자: {st.session_state.staff_info}`")
    with top_col2:
        if st.button("로그아웃"):
            st.session_state.user_role = None
            st.session_state.staff_info = None
            st.rerun()
            
    # 상단 탭 네비게이션
    tab_nav1, tab_nav2, tab_nav3, tab_nav4 = st.tabs(["참여자 등록", "행사 생성 및 관리", "통계 대시보드", "처리 이력 (Audit Log)"])
    
    # --------------------------------------
    # 탭 1: 참여자 등록 (PC/아이패드 1:3 대출 시스템 레이아웃)
    # --------------------------------------
    with tab_nav1:
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_count = sum(1 for p in st.session_state.participants if p['timestamp'].startswith(today_str))
        active_events_cnt = sum(1 for e in st.session_state.events if e['status'] == "진행 중")
        
        st.markdown(f"""
            <div class="top-summary-bar">
                <b>오늘의 참여자:</b> <span style="color:#3182F6; font-weight:bold;">{today_count}명</span> &nbsp;|&nbsp; 
                <b>진행 중인 행사:</b> <span style="color:#3182F6; font-weight:bold;">{active_events_cnt}개</span>
            </div>
        """, unsafe_allow_html=True)
        
        # 1:3 분할 레이아웃
        left_col, right_col = st.columns([1, 3])
        
        with left_col:
            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
            st.markdown("#### 참여자 등록")
            
            all_events = [f"[{e['status']}] {e['name']}" for e in st.session_state.events]
            selected_event_str = st.selectbox("행사 선택", all_events if all_events else ["등록된 행사 없음"])
            
            std_id_in = st.text_input("학번 (5자리)", key="staff_std_in", placeholder="예: 20601")
            name_in = st.text_input("이름", key="staff_name_in", placeholder="예: 홍길동")
            
            # 수동 날짜/시간 지정 (소급 등록)
            with st.expander("일시 수동 지정 (소급 등록)"):
                c_date = st.date_input("날짜 선택", date.today())
                c_time = st.time_input("시간 선택", datetime.now().time())
                custom_datetime_str = f"{c_date} {c_time.strftime('%H:%M:%S')}"
            
            if st.button("등록하기"):
                is_v, grade, class_num, number = parse_student_id(std_id_in)
                if not selected_event_str or "행사 없음" in selected_event_str:
                    st.error("행사를 선택해 주세요.")
                elif not is_v or not name_in.strip():
                    st.error("올바른 5자리 학번과 이름을 입력해 주세요.")
                else:
                    event_clean = selected_event_str.split("] ")[-1] if "]" in selected_event_str else selected_event_str
                    reg_time = custom_datetime_str if custom_datetime_str else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    st.session_state.participants.append({
                        "event_name": event_clean,
                        "student_id": std_id_in.strip(),
                        "grade": grade,
                        "class": class_num,
                        "number": number,
                        "name": name_in.strip(),
                        "timestamp": reg_time,
                        "operator": st.session_state.staff_info
                    })
                    add_log("참여자 등록", f"[{event_clean}] {std_id_in} {name_in} 등록 완료", st.session_state.staff_info)
                    st.success(f"{name_in.strip()}님 등록 완료!")
                    
            st.markdown('</div>', unsafe_allow_html=True)
            
        with right_col:
            st.markdown('<div class="toss-card">', unsafe_allow_html=True)
            st.markdown("#### 참여 이력 조회 (도서 대출 시스템 방식)")
            
            filter_c1, filter_c2 = st.columns([1, 2])
            with filter_c1:
                search_date = st.date_input("조회 날짜 선택", date.today())
            with filter_c2:
                search_kw = st.text_input("학번 또는 이름 검색", placeholder="예: 20601 또는 홍길동")
                
            df_p = pd.DataFrame(st.session_state.participants)
            
            if not df_p.empty:
                search_date_str = search_date.strftime("%Y-%m-%d")
                df_filtered = df_p[df_p['timestamp'].str.startswith(search_date_str)]
                
                if search_kw.strip():
                    df_filtered = df_filtered[
                        df_filtered['student_id'].str.contains(search_kw.strip()) |
                        df_filtered['name'].str.contains(search_kw.strip())
                    ]
                    
                if not df_filtered.empty:
                    # 표 컬럼 매핑 보정
                    disp_df = df_filtered[['timestamp', 'event_name', 'student_id', 'grade', 'class', 'number', 'name', 'operator']].copy()
                    disp_df.columns = ['참여 일시', '행사명', '학번', '학년', '반', '번호', '이름', '처리 담당자']
                    st.dataframe(disp_df.sort_values(by='참여 일시', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("해당 조건의 참여 기록이 없습니다.")
            else:
                st.info("등록된 참여 데이터가 없습니다.")
                
            st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------
    # 탭 2: 행사 생성 및 상태 관리
    # --------------------------------------
    with tab_nav2:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        st.markdown("#### 신규 행사 생성 및 상태 변경")
        
        e_col1, e_col2 = st.columns([1, 2])
        with e_col1:
            new_e_name = st.text_input("새 행사명 입력")
            if st.button("행사 생성"):
                if new_e_name.strip():
                    new_id = len(st.session_state.events) + 1
                    st.session_state.events.append({
                        "id": new_id,
                        "name": new_e_name.strip(),
                        "status": "진행 중",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    add_log("행사 생성", f"신규 행사 [{new_e_name.strip()}] 생성", st.session_state.staff_info)
                    st.success(f"[{new_e_name.strip()}] 행사가 생성되었습니다.")
                    st.rerun()
                else:
                    st.error("행사명을 입력해 주세요.")
                    
        with e_col2:
            st.markdown("##### 등록된 행사 목록")
            for idx, ev in enumerate(st.session_state.events):
                l_col, r_col = st.columns([3, 1])
                l_col.write(f"**{ev['name']}** (상태: `{ev['status']}` / 생성일: {ev['created_at']})")
                btn_txt = "마감하기" if ev['status'] == "진행 중" else "재개하기"
                if r_col.button(btn_txt, key=f"e_toggle_{idx}"):
                    st.session_state.events[idx]['status'] = "마감" if ev['status'] == "진행 중" else "진행 중"
                    add_log("행사 상태 변경", f"[{ev['name']}] -> {st.session_state.events[idx]['status']}", st.session_state.staff_info)
                    st.rerun()
                    
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------
    # 탭 3: 통계 대시보드
    # --------------------------------------
    with tab_nav3:
        st.markdown('<div class="toss-card">', unsafe_allow_html=True)
        st.markdown("#### 통합 통계 대시보드")
        
        df_all = pd.DataFrame(st.session_state.participants)
        if df_all.empty:
            st.info("통계를 산출할 데이터가 없습니다.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f'<div class="metric-card"><div class="metric-val">{len(df_all)}명</div><div class="metric-lbl">누적 총 참여자</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div class="metric-val">{len(df_all["event_name"].unique())}개</div><div class="metric-lbl">진행 행사 수</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div class="metric-val">{df_all["grade"].value_counts().idxmax()}학년</div><div class="metric-lbl">최다 참여 학년</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card"><div class="metric-val">{df_all["class"].value_counts().idxmax()}반</div><div class="metric-lbl">최다 참여 반</div></div>', unsafe_allow_html=True)
            
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
        st.markdown("#### 시스템 처리 이력 (Audit Log)")
        
        df_l = pd.DataFrame(st.session_state.logs)
        if df_l.empty:
            st.info("기록된 이력이 없습니다.")
        else:
            lt1, lt2, lt3, lt4 = st.tabs(["행사 생성 기록", "참여자 등록 기록", "시스템 접속 기록", "상태 변경 기록"])
            with lt1:
                st.dataframe(df_l[df_l['category'] == '행사 생성'], use_container_width=True, hide_index=True)
            with lt2:
                st.dataframe(df_l[df_l['category'] == '참여자 등록'], use_container_width=True, hide_index=True)
            with lt3:
                st.dataframe(df_l[df_l['category'] == '시스템 접속'], use_container_width=True, hide_index=True)
            with lt4:
                st.dataframe(df_l[df_l['category'] == '행사 상태 변경'], use_container_width=True, hide_index=True)
                
        st.markdown('</div>', unsafe_allow_html=True)
