#!/usr/bin/env python3
"""
Quick test of Qwen-VL-OCR API
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
import fitz
import base64

# Initialize client
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("DASHSCOPE_API_KEY not found in environment variables")

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# Test with first page of first PDF
pdf_path = Path("销冠能力复制数据库/销售成交营销SOP和话术/《绝对成交》谈判大师.pdf")
output_dir = Path("data/processed/books")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Opening PDF: {pdf_path}")
doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")

# Process first page only
page = doc[0]
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
img_path = output_dir / "test_page_0.png"
pix.save(img_path)
print(f"Saved test image: {img_path}")

# Convert to base64
with open(img_path, 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

print("Calling Qwen-VL-OCR API...")
completion = client.chat.completions.create(
    model="qwen-vl-ocr-latest",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    },
                },
                {
                    "type": "text",
                    "text": "请识别图片中的所有文字内容，保持原有格式和结构。"
                },
            ],
        },
    ],
)

text = completion.choices[0].message.content
print(f"\n[SUCCESS] Extracted {len(text)} characters from first page")
print(f"\nFirst 200 characters:\n{text[:200]}")

doc.close()
img_path.unlink()
print("\n[OK] Test completed successfully!")
