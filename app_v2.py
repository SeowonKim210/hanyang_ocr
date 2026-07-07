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

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("API 키 설정 오류")
    st.stop()

# --- 2. 최적화된 프롬프트 ---
OCR_PROMPT = """
당신은 고정밀 데이터 추출기입니다. 다음 명부 이미지에서 표의 행(row) 단위로 데이터를 추출하세요.

지침 (매우 중요):
1. 반드시 JSON 배열 형식으로만 응답해.
2. 각 행별로 {'name', 'company_job', 'phone', 'major', 'student_id'} 필드를 추출해.
3. [마스킹 규칙]: 전화번호에 '*'가 포함되어 있으면 해당 전화번호 필드는 반드시 비어있는 문자열("")로 처리해.
4. [할루시네이션 방지]: 이미지에 텍스트가 확실히 보이지 않거나 없는 데이터는 절대 추측하지 말고 null 또는 ""로 처리해. 
5. 표의 좌/중/우 모든 영역을 빠짐없이 스캔하여 행을 누락하지 마.
"""

uploaded_file = st.file_uploader("명부 PDF 파일을 업로드하세요", type=["pdf"])
batch_size = st.number_input("처리 페이지 수 (추천: 1)", min_value=1, max_value=5, value=1)

if uploaded_file and st.button("🚀 정밀 변환 시작"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    from pdf2image import pdfinfo_from_path
    total_pages = pdfinfo_from_path(tmp_path)["Pages"]
    all_results = []
    
    progress_bar = st.progress(0)
    
    for i in range(1, total_pages + 1, batch_size):
        images = convert_from_path(tmp_path, first_page=i, last_page=min(i + batch_size - 1, total_pages), dpi=300)
        
        for img in images:
            # 모델 설정 강화: temperature를 낮추어 창의적 답변(환각) 억제
            response = client.models.generate_content(
                model="gemini-1.5-pro", # 더 정교한 Pro 모델 사용
                contents=[img, OCR_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0 # 환각 억제 최적값
                )
            )
            
            page_data = json.loads(response.text)
            all_results.extend(page_data)
            st.write(f"✅ {i}페이지 처리 완료 (추출 건수: {len(page_data)}건)")
            st.dataframe(pd.DataFrame(page_data)) # 중간 결과 확인용
            
        progress_bar.progress(i / total_pages)
            
    df = pd.DataFrame(all_results)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    
    st.download_button("📥 최종 엑셀 파일 다운로드", excel_buffer.getvalue(), "result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    os.remove(tmp_path)
    st.success("모든 처리가 완료되었습니다!")
