import streamlit as st
import pandas as pd
import json
import io
import tempfile
from pdf2image import convert_from_path
from PIL import Image
from google import genai
from google.genai import types

# 1. API 설정 (가장 상단에 위치)
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("🎓 한양대 명부 데이터 추출기")

# 2. 시스템 프롬프트 정의
OCR_PROMPT = """
당신은 한양대학교 명부 데이터 추출 전문가입니다. 제공된 이미지에서 데이터를 행 단위로 추출하여 JSON 배열로 반환하세요.
반드시 다음 필드 구조를 준수하세요:
{'page': '페이지번호', 'original_section': '원본구역', 'original_row': '원본행', 'name': '이름', 'company_job': '직장명·직책', 'phone': '전화번호'}

지침:
1. '페이지', '원본구역', '원본행' 정보를 정확히 기입하십시오.
2. 전화번호에 '*' 마스킹이 포함된 행은 반드시 제외하십시오.
3. 정확도를 최우선으로 하여 오타 없이 꼼꼼하게 추출하십시오.
4. 결과는 오직 JSON 배열 형식으로만 응답하십시오.
"""

# 3. 파일 업로더
uploaded_file = st.file_uploader("파일을 업로드하세요 (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file and st.button("🚀 데이터 추출 시작"):
    all_results = []
    
    # 4. 파일 처리 로직 (PDF와 이미지 통합)
    images = []
    if uploaded_file.type == "application/pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            # PDF를 이미지 리스트로 변환 (기본값 200dpi)
            images = convert_from_path(tmp.name, dpi=200)
    else:
        images = [Image.open(uploaded_file)]

    progress = st.progress(0)
    
    # 5. OCR 처리 루프
    for idx, img in enumerate(images):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[img, OCR_PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            # 응답 데이터 파싱
            page_data = json.loads(response.text)
            
            # 마스킹('*') 체크 및 리스트 추가
            filtered = [r for r in page_data if r.get('phone') and '*' not in str(r['phone'])]
            all_results.extend(filtered)
            
        except Exception as e:
            st.error(f"{idx+1}번째 데이터 처리 중 오류 발생: {e}")
            
        progress.progress((idx + 1) / len(images))
    
    # 6. 결과 엑셀 생성
    if all_results:
        df = pd.DataFrame(all_results)
        # 컬럼 순서 고정
        column_order = ['page', 'original_section', 'original_row', 'name', 'company_job', 'phone']
        # 혹시 데이터에 해당 컬럼이 없는 경우를 대비
        existing_cols = [c for c in column_order if c in df.columns]
        df = df[existing_cols]
        
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        st.download_button(
            label="📥 엑셀 파일 다운로드", 
            data=excel_buffer.getvalue(), 
            file_name="hanyang_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("데이터 추출이 완료되었습니다!")
    else:
        st.warning("추출된 데이터가 없습니다. 원본 파일의 형식을 확인하세요.")
