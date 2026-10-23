# 아래 코드를 기존 코드의 2번 섹션( st.markdown(""" <style> ... </style> """) )과 교체하세요.
# 기존 Streamlit 기능/DB 로직은 변경하지 않는 스타일 교체안입니다.
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

:root {
  --ink: #202127;
  --muted: #737987;
  --blue: #5d7cf5;
  --line: rgba(118, 130, 157, .17);
  --glass: rgba(255,255,255,.68);
}
html, body, [class*="css"], .stApp, p, div, label, span, input, button {
  font-family: 'Pretendard Variable', Pretendard, sans-serif !important;
}
.stApp {
  color: var(--ink) !important;
  background:
    radial-gradient(ellipse at 14% 35%, rgba(164,157,255,.19), transparent 34%),
    radial-gradient(ellipse at 78% 28%, rgba(133,176,255,.19), transparent 32%),
    radial-gradient(ellipse at 60% 85%, rgba(186,215,255,.20), transparent 35%),
    linear-gradient(135deg,#f8f9fc 0%,#eef1f8 48%,#fafbfe 100%) !important;
  background-attachment: fixed !important;
}
[data-testid="stHeader"] { background: rgba(248,249,252,.68) !important; backdrop-filter: blur(18px); }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { max-width: 1320px; padding-top: 2rem !important; padding-bottom: 4rem !important; }

/* 상단 브랜드 영역 */
.nav-pill {
  display:flex; justify-content:space-between; align-items:center; gap:1rem;
  padding: 16px 24px; margin: 4px 0 28px;
  border:1px solid rgba(255,255,255,.9); border-radius:999px;
  background:rgba(255,255,255,.58); backdrop-filter:blur(22px);
  box-shadow:0 12px 34px rgba(79,91,125,.08), inset 0 1px 0 rgba(255,255,255,.95);
}

/* 주요 카드 */
.main-box {
  position:relative; overflow:hidden;
  background:linear-gradient(145deg,rgba(255,255,255,.88),rgba(255,255,255,.62));
  border:1px solid rgba(255,255,255,.95); border-radius:28px;
  padding:38px 40px; margin-bottom:22px;
  box-shadow:0 24px 60px rgba(77,88,119,.12), inset 0 1px 0 rgba(255,255,255,.95);
  backdrop-filter:blur(20px);
}
.main-box:before {
  content:''; position:absolute; left:9%; right:9%; top:0; height:2px;
  background:linear-gradient(90deg,transparent,#8da6ff,#b7a2ff,transparent);
}
.badge-pill {
  display:inline-flex; align-items:center; padding:7px 13px; margin-bottom:15px;
  border:1px solid rgba(93,124,245,.15); border-radius:999px;
  background:rgba(226,234,255,.75); color:#5576ec !important;
  font-size:12px; font-weight:750; letter-spacing:.11em;
}

/* 버튼 */
.stButton > button, [data-testid="stDownloadButton"] button {
  width:100%; min-height:48px; border-radius:15px !important;
  border:1px solid rgba(255,255,255,.9) !important;
  background:linear-gradient(135deg,#6887ff 0%,#526de7 100%) !important;
  color:#fff !important; font-weight:700 !important; font-size:15px !important;
  box-shadow:0 9px 22px rgba(82,109,231,.22) !important;
  transition:transform .18s ease, box-shadow .18s ease, filter .18s ease !important;
}
.stButton > button p, .stButton > button span,
[data-testid="stDownloadButton"] button p,
[data-testid="stDownloadButton"] button span { color:#fff !important; }
.stButton > button:hover, [data-testid="stDownloadButton"] button:hover {
  transform:translateY(-2px); filter:brightness(1.025);
  box-shadow:0 14px 28px rgba(82,109,231,.28) !important;
}
.sub-btn > button {
  background:rgba(255,255,255,.76) !important; color:#4b5567 !important;
  border:1px solid var(--line) !important; box-shadow:none !important;
}
.sub-btn > button p, .sub-btn > button span { color:#4b5567 !important; }

/* 입력창과 선택 상자 */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
.stSelectbox [data-baseweb="select"] > div, .stMultiSelect [data-baseweb="select"] > div {
  min-height:46px; border-radius:13px !important;
  border:1px solid rgba(130,143,169,.24) !important;
  background:rgba(255,255,255,.78) !important; color:#252936 !important;
  box-shadow:inset 0 1px 2px rgba(35,45,70,.025);
}
.stTextInput input:focus, .stNumberInput input:focus { border-color:#8da4ff !important; box-shadow:0 0 0 3px rgba(93,124,245,.12) !important; }

/* 제목과 본문 */
h1,h2,h3,h4,h5 { color:#202127 !important; letter-spacing:-.035em !important; }
h1 { font-size:clamp(2rem,3vw,2.65rem) !important; font-weight:800 !important; }
h2 { font-size:1.9rem !important; font-weight:800 !important; }
h3 { font-size:1.45rem !important; font-weight:750 !important; }
h4 { font-size:1.18rem !important; font-weight:750 !important; }
p, .stMarkdown { color:#555d6c; line-height:1.7; }

/* 탭 메뉴를 가볍고 정돈된 형태로 */
.stTabs [data-baseweb="tab-list"] {
  gap:8px; padding:7px; border:1px solid rgba(255,255,255,.95);
  border-radius:18px; background:rgba(255,255,255,.56); backdrop-filter:blur(16px);
}
.stTabs [data-baseweb="tab"] {
  height:43px; padding:0 17px; border-radius:13px; color:#626a79;
  background:transparent; border:1px solid transparent;
}
.stTabs [aria-selected="true"] {
  color:#263047 !important; background:rgba(255,255,255,.96) !important;
  border:1px solid rgba(220,226,240,.9) !important;
  box-shadow:0 4px 15px rgba(75,88,125,.11);
}
.stTabs [data-baseweb="tab-highlight"] { background:transparent !important; }

/* 표와 차트 */
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border:1px solid rgba(135,147,173,.16); border-radius:16px; overflow:hidden;
  background:rgba(255,255,255,.72);
}
[data-testid="stMetric"] {
  padding:19px 21px; border-radius:19px; border:1px solid rgba(255,255,255,.95);
  background:rgba(255,255,255,.68); box-shadow:0 10px 28px rgba(75,88,125,.07);
}
[data-testid="stExpander"] {
  border:1px solid rgba(130,143,169,.18) !important; border-radius:15px !important;
  background:rgba(255,255,255,.55) !important;
}
hr { border-color:rgba(130,143,169,.2) !important; }

/* 좁은 화면 */
@media (max-width: 760px) {
  .block-container { padding:1rem 1rem 3rem !important; }
  .main-box { padding:26px 22px; border-radius:22px; }
  .nav-pill { padding:13px 16px; border-radius:20px; align-items:flex-start; flex-direction:column; }
  h1 { font-size:2rem !important; }
  .stTabs [data-baseweb="tab"] { padding:0 10px; font-size:13px; }
}
</style>
""", unsafe_allow_html=True)
