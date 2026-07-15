import streamlit as st
import pandas as pd
import json
import io
import tempfile
from pdf2image import convert_from_path
from PIL import Image
from google import genai
from google.genai import types

st.title("🎓 한양대 명부 데이터 추출기")

# 수정된 시스템 프롬프트
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

# 파일 업로드 옵션 추가 (PDF, PNG, JPG)
uploaded_file = st.file_uploader("파일을 업로드하세요 (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file and st.button("🚀 데이터 추출 시작"):
    all_results = []
    
    # 1. 파일 처리 로직 (PDF와 이미지 통합)
    images = []
    if uploaded_file.type == "application/pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            images = convert_from_path(tmp.dpi) # PDF를 이미지 리스트로 변환
    else:
        images = [Image.open(uploaded_file)] # 단일 이미지를 리스트에 담음

    progress = st.progress(0)
    
    # 2. OCR 처리 루프
    for idx, img in enumerate(images):
        response = client.models.generate_content(
            model="gemini-2.0-flash", # 더 안정적인 모델 사용 권장
            contents=[img, OCR_PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        try:
            page_data = json.loads(response.text)
            # 마스킹('*') 체크
            filtered = [r for r in page_data if r.get('phone') and '*' not in str(r['phone'])]
            all_results.extend(filtered)
        except Exception as e:
            st.error(f"{idx+1}페이지 처리 중 오류: {e}")
            
        progress.progress((idx + 1) / len(images))
    
    # 3. 결과 엑셀 생성
    if all_results:
        df = pd.DataFrame(all_results)
        # 컬럼 순서 지정
        df = df[['page', 'original_section', 'original_row', 'name', 'company_job', 'phone']]
        
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        st.download_button("📥 엑셀 파일 다운로드", excel_buffer.getvalue(), "hanyang_list.xlsx")
    else:
        st.warning("추출된 데이터가 없습니다.")
