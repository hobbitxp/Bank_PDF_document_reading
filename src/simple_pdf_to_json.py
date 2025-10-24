#!/usr/bin/env python3
"""
Simple PDF to JSON converter - อ่าน PDF แล้วเอา text มาใส่ใน JSON
"""
import fitz  # PyMuPDF
import json
import sys
from pathlib import Path
from datetime import datetime


def pdf_to_json(pdf_path: str, output_path: str = None, password: str = None):
    """
    อ่าน PDF แล้วแปลงเป็น JSON object
    
    Args:
        pdf_path: path ไปยังไฟล์ PDF
        output_path: path สำหรับ output JSON (ถ้าไม่ระบุจะสร้างอัตโนมัติ)
        password: password สำหรับ PDF ที่มีการป้องกัน
    """
    # เปิดไฟล์ PDF
    doc = fitz.open(pdf_path)
    
    # ถ้ามี password ให้ลองใช้
    if doc.is_encrypted:
        if password:
            if not doc.authenticate(password):
                doc.close()
                raise ValueError(f"รหัสผ่านไม่ถูกต้อง")
            print(f"✓ ปลดล็อก PDF ด้วยรหัสผ่านสำเร็จ")
        else:
            doc.close()
            raise ValueError(f"PDF มีการป้องกันด้วยรหัสผ่าน กรุณาระบุรหัสผ่านด้วย --password")
    
    # สร้าง JSON structure
    data = {
        "source_file": str(Path(pdf_path).name),
        "extracted_at": datetime.now().isoformat(),
        "total_pages": len(doc),
        "pages": []
    }
    
    # อ่าน text จากทุกหน้า
    print(f"กำลังอ่าน PDF: {pdf_path}")
    print(f"จำนวนหน้าทั้งหมด: {len(doc)}")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        page_data = {
            "page_number": page_num + 1,  # เริ่มนับจาก 1 เพื่อให้อ่านง่าย
            "text_length": len(text),
            "text": text
        }
        
        data["pages"].append(page_data)
        print(f"  หน้า {page_num + 1}: ดึง text ได้ {len(text)} ตัวอักษร")
    
    doc.close()
    
    # สร้างชื่อไฟล์ output ถ้าไม่ได้ระบุ
    if output_path is None:
        input_path = Path(pdf_path)
        output_path = f"data/json/{input_path.stem}_extracted.json"
    
    # สร้าง directory ถ้ายังไม่มี
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # เขียนไฟล์ JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ บันทึกไฟล์สำเร็จ: {output_file}")
    print(f"  ขนาดไฟล์: {output_file.stat().st_size / 1024:.2f} KB")
    
    return data


def main():
    """Main function สำหรับรัน command line"""
    if len(sys.argv) < 2:
        print("การใช้งาน: python simple_pdf_to_json.py <pdf_file> [output_json] [--password PASSWORD]")
        print("\nตัวอย่าง:")
        print("  python simple_pdf_to_json.py 'Test/ไทยพาณิชย์/3...pdf'")
        print("  python simple_pdf_to_json.py 'Test/ttb/1.pdf' output.json")
        print("  python simple_pdf_to_json.py 'Test/AcctSt_Feb25.pdf' --password 28101983")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = None
    password = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--password' and i + 1 < len(sys.argv):
            password = sys.argv[i + 1]
            i += 2
        else:
            output_path = sys.argv[i]
            i += 1
    
    # ตรวจสอบว่าไฟล์มีจริง
    if not Path(pdf_path).exists():
        print(f"❌ ไม่พบไฟล์: {pdf_path}")
        sys.exit(1)
    
    try:
        pdf_to_json(pdf_path, output_path, password)
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
