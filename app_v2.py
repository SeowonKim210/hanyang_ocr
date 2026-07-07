import streamlit as st
import pandas as pd
import json
import os
import difflib
from pdf2image import convert_from_path
from google import genai
from google.genai import types
import io

# --- 1. 화면 및 페이지 설정 ---
st.set_page_config(page_title="한양대 OCR 명부 변환기", layout="wide", page_icon="🎓")
st.title("🎓 한양대 고정밀 명부 OCR 자동화 시스템")
st.write("로컬 환경의 방화벽 차단 문제를 해결하기 위해 클라우드(GitHub) 배포용으로 최적화된 고정밀 변환기입니다.")

# --- 2. 사이드바 설정 및 안전한 API 키 연동 ---
st.sidebar.header("⚙️ 시스템 설정")

# Streamlit Cloud의 Secrets에서 API 키를 안전하게 가져옵니다.
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    # Secrets 설정이 안 되어 있을 경우 경고 표시
    st.error("보안 경고: Streamlit Secrets에 'GEMINI_API_KEY'가 설정되지 않았습니다.")
    API_KEY = ""

client = genai.Client(api_key=API_KEY)

# Poppler 경로 자동 탐지 (로컬 PC와 깃허브 리눅스 서버 호환)
LOCAL_POPPLER = r"C:\Users\seednpc16\Desktop\graduate_pdf_prj\Release-26.02.0-0\poppler-26.02.0\Library\bin"
if os.path.exists(LOCAL_POPPLER):
    POPPLER_PATH = LOCAL_POPPLER
else:
    POPPLER_PATH = None  # 깃허브 서버(Linux)에서는 packages.txt 덕분에 시스템에 자동 등록됩니다.

# --- 3. 학과 교정용 한양대 마스터 데이터 리스트 ---
HANYANG_MASTER = [
    # 학부 주요 학과
    "건축학부", "건축공학부", "건설환경공학과", "도시공학과", "자원환경공학과", "융합전자공학부", 
    "컴퓨터소프트웨어학부", "정보시스템학과", "전기ㆍ생체공학부", "전기공학전공", "바이오메디컬공학전공", "신소재공학부", 
    "화학공학과", "생명공학과", "유기나노공학과", "에너지공학과", "기계공학부", "원자력공학과", "산업공학과", 
    "미래자동차공학과", "데이터사이언스학부", "반도체공학과", "의예과", "의학과", "간호학과", "국어국문학과", 
    "중어중문학과", "영어영문학과", "독어독문학과", "사학과", "철학과", "미래인문융합학부", "정치외교학과", 
    "사회학과", "미디어커뮤니케이션학과", "관광학부", "수학과", "물리학과", "화학과", "생명과학과", "정책학과", 
    "행정학과", "경제금융학과", "경영학부", "파이낸스경영학과", "교육학과", "교육공학과", "국어교육과", 
    "영어교육과", "수학교육과", "응용미술교육과", "의류학과", "식품영양학과", "실내건축디자인학과", "성악과", 
    "작곡과", "피아노과", "관혁악과", "국악과", "스포츠산업과학부", "무용학과", "국제학부", "글로벌콘텐츠융합학부", 
    "산업융합학부", "한양YK인터칼리지", "디자인학부", "실용음악학과",
    # 일반/전문/특수 대학원
    "일반대학원", "경영전문대학원(MBA)", "법학전문대학원(로스쿨)", "의학전문대학원", "공학대학원", 
    "공공정책대학원", "교육대학원", "언론정보대학원", "국제학대학원", "임상간호정보대학원", "부동산융합대학원", "융합산업대학원",
    # 상세 학과 및 ERICA/협동과정 계열
    "데이터사이언스학과", "배터리공학과", "융합기계공학과", "융합전자공학과", "인공지능학과", "컴퓨터‧소프트웨어학과", 
    "환경과학과", "법학과", "경영학과", "러닝사이언스학과", "응용미술학과", "한국어교육학과", "국악학과", "음악학과", 
    "글로벌스포츠산업학과", "뮤지컬학과", "연극영화학과", "체육학과", "글로벌기후환경학과", "산업데이터엔지니어링학과",
    "건설환경시스템공학과", "건축설계학과", "건축시스템공학과", "교통·물류공학과", "기계설계공학과", "로봇공학과", 
    "산업경영공학과", "재료화학공학과", "전자공학과", "컴퓨터공학과", "응용화학과", "해양융합과학과", "인공지능융합학과", 
    "휴먼컴퓨터인터랙션학과", "수리데이터사이언스학과", "약학과", "분자생명과학과", "응용물리학과", "나노광전자학과", 
    "바이오나노학과", "지능정보양자공학과", "일본언어문화학과", "중국지역통상학과", "광고홍보학과", "문화인류학과", 
    "미디어학과", "경영컨설팅학과", "금융보험학과", "응용경제학과", "전략경영학과", "공연예술학과", "스포츠과학과", 
    "나노반도체공학과", "디지털의료융합학과", "블록체인융합학과", "융합국방학과", "인공지능반도체공학과", "정보보안학과", 
    "지능형로봇학과", "컴퓨테이셔널파이낸스공학과", "헬스케어디지털공학과", "국제의료개발학과", "맞춤의료학과", "보건학과", 
    "아동심리치료학과", "대중문화·시나리오학과", "비트코인화폐철학과", "나노융합과학과", "응용통계학과", "과학기술정책학과", 
    "비즈니스인포매틱스학과", "다문화교육학과", "박물관교육학과", "평생학습학과", "아트앤스포테인먼트학과", "고령산업융합학과", 
    "음악치료과학과", "창업융합학과", "스마트시티공학과", "우주공학과", "첨단소재공학과", "장르테크놀로지와 서브컬처학과", 
    "문화콘텐츠학과", "정보보호학과", "HY-KIST 바이오융합학과", "HYU-KITECH 공동학과", "AI응용학과", 
    "디스플레이융합공학과", "미래모빌리티학과", "지능융합학과", "파워엔지니어링학과", "기능성식품학과", 
    "스마트컨스트럭션공학과", "지능정보융합공학과"
]

def map_to_master_list(raw_text):
    if not raw_text or pd.isna(raw_text):
        return ""
    cleaned = str(raw_text).strip()
    # 글자 유사도가 25% 이상인 가장 가까운 정식 학과 명칭을 매핑합니다.
    matches = difflib.get_close_matches(cleaned, HANYANG_MASTER, n=1, cutoff=0.25)
    return matches[0] if matches else cleaned

# --- 4. 메인 어드민 기능 ---
uploaded_file = st.file_uploader("명부 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    st.info(f"📁 파일 선택됨: {uploaded_file.name}")
    
    col1, col2 = st.columns(2)
    with col1:
        start_p = st.number_input("시작 페이지 번호", min_value=1, value=1)
    with col2:
        end_p = st.number_input("끝 페이지 번호", min_value=1, value=1)
        
    if st.button("🚀 고정밀 변환 엔진 가동"):
        if not API_KEY:
            st.error("API 키가 설정되지 않아 작업을 시작할 수 없습니다. Streamlit Secrets 설정을 확인해주세요.")
            st.stop()
            
        all_records = []
        
        with st.spinner("1단계: PDF 명부를 고해상도 인쇄급 이미지(300 DPI)로 분할하고 있습니다..."):
            try:
                images = convert_from_path(
                    uploaded_file,
                    poppler_path=POPPLER_PATH,
                    dpi=300,
                    first_page=start_p,
                    last_page=end_p
                )
            except Exception as e:
                st.error(f"PDF 파일 분할 실패 (Poppler 에러): {e}")
                st.stop()
                
        progress_bar = st.progress(0)
        
        for i, img in enumerate(images):
            actual_page = start_p + i
            st.text(f"⏳ {actual_page}페이지의 열 구조 및 원본 데이터 추출 중...")
            
            # 오동작을 줄이고 순수 텍스트 추출에 집중하게 만드는 정밀 프롬프트
            prompt = f"""
            이 이미지(명부 스캔본)에서 사람들의 모든 정보를 '눈에 보이는 그대로' 100% 누락 없이 긁어와줘.
            데이터 변형이나 요약을 절대 금지하며, 원본 문서의 구조를 고스란히 유지하는 것이 핵심이다.

            [필수 데이터 수집 및 구조화 규칙]
            1. 'section': 원본 문서가 좌/우 2단 구조라면 "좌" 또는 "우"로 채우고, 단일 구조면 "단일"로 써라.
            2. 'row': 해당 구역(좌/우) 내에서 위에서 아래로 정렬된 순서대로 누락 없이 행 번호(1부터 시작하는 숫자)를 부여해라.
            3. 'major': 이미지에 적힌 학과 또는 대학원 이름을 오타나 축약어(예: 컴공, 경영대 등)까지 '보이는 문자 그대로' 추출해라.
            4. 'student_id': 학번, 입학년도, 졸업년도 정보를 괄호와 문자를 포함해 똑같이 적어라. (예: 89학번(1989/1993))
            5. 'phone': 전화번호에 별표(*) 등 마스킹 부호가 섞여있더라도 수집에서 누락하지 말고 텍스트 그대로 일단 모두 적어라.

            [출력 JSON 배열 양식]
            [
              {{
                "page": {actual_page},
                "section": "좌",
                "row": 1,
                "name": "이름",
                "company_job": "직장명 및 직책",
                "phone": "전화번호",
                "major": "기록된 학과명 그대로",
                "student_id": "기록된 학번정보 그대로"
              }}
            ]
            """
            
            try:
                # 2.5-flash 모델로 속도 향상 및 대량 페이지 처리 최적화
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                page_data = json.loads(response.text)
                all_records.extend(page_data)
            except Exception as e:
                st.error(f"❌ {actual_page}페이지 AI 분석 중 에러 발생: {e}")
                
            progress_bar.progress((i + 1) / len(images))
            
        if all_records:
            with st.spinner("2단계: 파이썬 알고리즘을 이용한 정밀 데이터 가공 및 학과 정규화 진행 중..."):
                df = pd.DataFrame(all_records)
                
                # 규칙 1: 전화번호에 별표(*)가 들어간 불완전한 번호는 데이터 DB 수집 대상에서 완전히 거름
                if 'phone' in df.columns:
                    df = df[~df['phone'].str.contains(r'\*', na=False, regex=True)]
                
                # 규칙 2: 파이썬 내부 교정 알고리즘을 활용한 유사 학과 자동 매핑
                if 'major' in df.columns:
                    df['major'] = df['major'].apply(map_to_master_list)
                
                # 컬럼 순서 및 이름 최종 정렬 강제 매핑
                column_mapping = {
                    "page": "페이지", "section": "원본구역 (좌/우 표시)", "row": "원본행",
                    "name": "이름", "company_job": "직장명•직책", "phone": "전화번호",
                    "major": "학과", "student_id": "학번(입학년도/졸업연도)"
                }
                df = df.rename(columns=column_mapping)
                
                target_cols = ["페이지", "원본구역 (좌/우 표시)", "원본행", "이름", "직장명•직책", "전화번호", "학과", "학번(입학년도/졸업연도)"]
                for col in target_cols:
                    if col not in df.columns:
                        df[col] = ""
                df = df[target_cols]
                
                # 최종 결과 엑셀 파일 생성 (바이너리 버퍼 활용)
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='OCR_정제결과')
                excel_data = excel_buffer.getvalue()
                
                st.subheader("📊 정제 완료된 데이터프레임 미리보기 (상위 30개 항목)")
                st.dataframe(df.head(30))
                
                st.download_button(
                    label="📥 정제 완료된 최종 엑셀 파일(.xlsx) 다운로드",
                    data=excel_data,
                    file_name=f"hanyang_ocr_clean_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("🎯 모든 작업이 성공적으로 끝났습니다! 위 다운로드 버튼을 눌러주세요.")
