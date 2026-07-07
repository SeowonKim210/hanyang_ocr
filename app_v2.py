import streamlit as st
import pandas as pd
import json
import os
import difflib
import io
import tempfile
from pdf2image import convert_from_path
from google import genai
from google.genai import types

# --- 1. 환경 설정 ---
st.set_page_config(page_title="한양대 OCR 명부 변환기", layout="wide", page_icon="🎓")
st.title("🎓 한양대 고정밀 명부 OCR 자동화 시스템")

# Streamlit Secrets에서 API 키 호출
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = ""
client = genai.Client(api_key=API_KEY)

# Poppler 경로 설정
LOCAL_POPPLER = r"C:\Users\seednpc16\Desktop\graduate_pdf_prj\Release-26.02.0-0\poppler-26.02.0\Library\bin"
POPPLER_PATH = LOCAL_POPPLER if os.path.exists(LOCAL_POPPLER) else None

# 학과 마스터 데이터 및 교정 함수
HANYANG_MASTER = ["건축학부", "컴퓨터소프트웨어학부", "경영학부", "의학과", "간호학과"] # 마스터 리스트는 기존과 동일하게 유지
def map_to_master_list(raw_text):
    if not raw_text or pd.isna(raw_text): return ""
    cleaned = str(raw_text).strip()
    matches = difflib.get_close_matches(cleaned, HANYANG_MASTER, n=1, cutoff=0.25)
    return matches[0] if matches else cleaned

# --- 2. 메인 로직 (파일 처리 부분 수정됨) ---
uploaded_file = st.file_uploader("명부 PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 고정밀 변환 엔진 가동"):
        with st.spinner("1단계: PDF 파일을 이미지로 변환 중..."):
            try:
                # [수정된 부분]: 업로드된 파일을 임시 파일로 저장하여 경로 인식 문제 해결
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                images = convert_from_path(tmp_path, poppler_path=POPPLER_PATH, dpi=300)
                os.remove(tmp_path) # 사용 후 삭제
            except Exception as e:
                st.error(f"PDF 파일 분할 실패: {e}")
                st.stop()

        # (중략: 데이터 추출 및 AI 분석 로직은 기존과 동일)
        
        # 엑셀 다운로드 버튼
        st.download_button(
            label="📥 정제 완료된 최종 엑셀 파일(.xlsx) 다운로드",
            data=excel_data, # 변환된 엑셀 데이터
            file_name="hanyang_ocr_clean_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
