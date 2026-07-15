import streamlit as st
import pandas as pd
import json
import io
import tempfile
from pdf2image import convert_from_path
from google import genai
from google.genai import types

st.title("🎓 한양대 명부 전체 추출기")

# API 설정 및 OCR 프롬프트
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
OCR_PROMPT = """
당신은 고정밀 데이터 추출기입니다. 이미지의 명부 데이터를 행(row) 단위로 추출하여 JSON 배열로 반환하세요.
필드: {'name', 'company_job', 'phone'}
지침: 
1. 전화번호에 '*'가 포함되어 있으면 해당 행은 제외하세요.
2. JSON 배열 형식으로만 응답하세요.
"""

uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"])

if uploaded_file and st.button("🚀 전체 데이터 추출"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    # PDF 전체 페이지 변환 (고해상도)
    images = convert_from_path(tmp_path, dpi=200)
    all_results = []
    
    progress = st.progress(0)
    for idx, img in enumerate(images):
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[img, OCR_PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        try:
            page_data = json.loads(response.text)
            # 마스킹('*')이 포함된 전화번호 제거
            filtered = [r for r in page_data if r.get('phone') and '*' not in r['phone']]
            all_results.extend(filtered)
        except:
            pass
        progress.progress((idx + 1) / len(images))
    
    # 엑셀 저장
    df = pd.DataFrame(all_results)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    st.download_button("📥 엑셀 파일 다운로드", excel_buffer.getvalue(), "hanyang_list.xlsx")
