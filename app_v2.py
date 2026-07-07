import streamlit as st
import pandas as pd
import json
import os
import io
import tempfile
from pdf2image import convert_from_path
from google import genai
from google.genai import types

# --- 1. 환경 설정 ---
st.set_page_config(page_title="한양대 OCR 변환기", layout="wide", page_icon="🎓")
st.title("🎓 한양대 고정밀 명부 OCR 자동화 시스템")

# Streamlit Secrets에서 API 키 호출
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("API 키가 설정되지 않았습니다. Secrets를 확인하세요.")
    st.stop()

# --- 2. 메인 UI 및 분할 처리 로직 ---
uploaded_file = st.file_uploader("명부 PDF 파일을 업로드하세요", type=["pdf"])
batch_size = st.number_input("한 번에 처리할 페이지 수 (API 부하 방지용)", min_value=1, max_value=10, value=3)

if uploaded_file and st.button("🚀 분할 변환 엔진 가동"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    # 전체 페이지 확인
    from pdf2image import pdfinfo_from_path
    info = pdfinfo_from_path(tmp_path)
    total_pages = info["Pages"]
    
    all_results = []
    
    # 페이지를 batch_size만큼 나누어 처리
    for i in range(1, total_pages + 1, batch_size):
        end = min(i + batch_size - 1, total_pages)
        st.write(f"⏳ 처리 중: {i} ~ {end} 페이지 (총 {total_pages} 페이지)")
        
        images = convert_from_path(tmp_path, first_page=i, last_page=end, dpi=300)
        
        for img in images:
            prompt = "이 명부 이미지에서 정보를 JSON 배열(name, company_job, phone, major, student_id)로 추출해."
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[img, prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            all_results.extend(json.loads(response.text))
            
    # 결과 저장
    df = pd.DataFrame(all_results)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    
    st.download_button("📥 엑셀 파일 다운로드", excel_buffer.getvalue(), "result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    os.remove(tmp_path)
    st.success("완료!")
