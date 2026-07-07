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
    st.error("API 키 설정 오류. Secrets를 확인하세요.")
    st.stop()

# --- 2. 강화된 프롬프트 ---
OCR_PROMPT = """
당신은 고정밀 데이터 추출기입니다. 이미지의 명부 데이터를 행(row) 단위로 추출하여 JSON 배열로 반환하세요.

지침 (매우 중요):
1. 반드시 {'name', 'company_job', 'phone', 'major', 'student_id'} 필드를 포함한 JSON 배열 형식으로만 응답해.
2. [마스킹 규칙]: 전화번호에 '*'가 포함되어 있으면 해당 필드는 반드시 빈 문자열("")로 처리해.
3. [할루시네이션 금지]: 데이터가 이미지에 없으면 절대 지어내지 말고 null 또는 ""로 처리해.
4. 표의 좌/중/우 모든 행을 스캔하여 누락 없이 추출해.
"""

uploaded_file = st.file_uploader("명부 PDF 파일을 업로드하세요", type=["pdf"])
batch_size = 1 # 안정성을 위해 1페이지씩 처리 권장

if uploaded_file and st.button("🚀 정밀 변환 시작"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    from pdf2image import pdfinfo_from_path
    total_pages = pdfinfo_from_path(tmp_path)["Pages"]
    all_results = []
    
    for i in range(1, total_pages + 1, batch_size):
        # API 부하 방지를 위해 dpi를 200으로 조정 (속도 개선)
        images = convert_from_path(tmp_path, first_page=i, last_page=i, dpi=200)
        
        for img in images:
            # gemini-2.5-flash 모델 명시적 사용
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=[img, OCR_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            
            try:
                page_data = json.loads(response.text)
                all_results.extend(page_data)
                st.write(f"✅ {i}페이지 처리 완료 (추출 건수: {len(page_data)}건)")
                st.dataframe(pd.DataFrame(page_data))
            except:
                st.warning(f"⚠️ {i}페이지 데이터 파싱 실패, 건너뜁니다.")
            
    df = pd.DataFrame(all_results)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    
    st.download_button("📥 최종 엑셀 파일 다운로드", excel_buffer.getvalue(), "result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    os.remove(tmp_path)
    st.success("모든 처리가 완료되었습니다!")
