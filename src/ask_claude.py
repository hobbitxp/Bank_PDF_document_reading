#!/usr/bin/env python3
"""
ส่ง masked JSON ไปวิเคราะห์ด้วย Claude AI
รองรับ PDPA compliance - ข้อมูลที่ส่งออกไปถูก mask แล้ว
"""

import json
import sys
import os
from pathlib import Path
import anthropic

def load_masked_json(json_file):
    """โหลด masked JSON file"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def ask_claude(masked_json, question, api_key=None):
    """
    ส่งคำถามไปยัง Claude AI พร้อม masked data
    
    Args:
        masked_json: dict - masked JSON data
        question: str - คำถามที่ต้องการถาม
        api_key: str - Claude API key (optional, จะใช้จาก environment ถ้าไม่ระบุ)
    """
    # ใช้ API key จาก parameter หรือ environment
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found!")
        print("\nวิธีตั้งค่า API key:")
        print("1. ตั้งค่าใน environment:")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\n2. หรือส่งผ่าน parameter:")
        print("   ask_claude(data, question, api_key='your-key')")
        print("\n3. หรือสร้างไฟล์ .env:")
        print("   echo 'ANTHROPIC_API_KEY=your-key' > .env")
        return None
    
    # สร้าง Claude client
    client = anthropic.Anthropic(api_key=api_key)
    
    # แปลง JSON เป็น text สำหรับส่งให้ Claude
    json_text = json.dumps(masked_json, ensure_ascii=False, indent=2)
    
    # สร้าง prompt
    prompt = f"""คุณเป็น AI ผู้เชี่ยวชาญด้านการวิเคราะห์งบการเงินและธนาคาร

ข้อมูลที่ได้รับเป็นข้อมูล Bank Statement ที่ถูก mask เพื่อความปลอดภัยตาม PDPA แล้ว:
- ชื่อ-นามสกุล → NAME_XXX
- เลขบัตรประชาชน → THAIID_XXX
- เบอร์โทรศัพท์ → PHONE_XXX
- ที่อยู่ → ADDRESS_XXX
- อีเมล → EMAIL_XXX
- เลขบัญชี → ACCOUNT_XXX

ข้อมูล Bank Statement (masked):
{json_text}

คำถาม: {question}

โปรดวิเคราะห์และตอบคำถามโดยใช้ข้อมูลจาก statement ที่ให้มา ตอบเป็นภาษาไทยที่เข้าใจง่าย"""

    print(f"\n🤖 กำลังส่งคำถามไปยัง Claude AI...")
    print(f"📊 ขนาดข้อมูล: {len(json_text):,} characters")
    print(f"❓ คำถาม: {question}\n")
    
    try:
        # เรียกใช้ Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # ใช้ model ล่าสุด
            max_tokens=4096,
            temperature=0.3,  # ลดความ creative เพื่อความแม่นยำ
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # ดึงคำตอบ
        answer = message.content[0].text
        
        # แสดงข้อมูล usage
        usage = message.usage
        print(f"📈 Token Usage:")
        print(f"   Input: {usage.input_tokens:,} tokens")
        print(f"   Output: {usage.output_tokens:,} tokens")
        print(f"   Total: {usage.input_tokens + usage.output_tokens:,} tokens")
        print(f"\n{'='*60}\n")
        
        return answer
        
    except anthropic.APIError as e:
        print(f"❌ Claude API Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python ask_claude.py <masked_json_file> [question]")
        print("\nExample:")
        print('  python ask_claude.py data.json "แต่ละเดือนได้รับเงินเดือนเท่าไหร่"')
        print('  python ask_claude.py data.json "วิเคราะห์พฤติกรรมการใช้จ่าย"')
        sys.exit(1)
    
    json_file = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else "สรุปข้อมูลในงบแสดงรายการบัญชีนี้"
    
    # ตรวจสอบไฟล์
    if not Path(json_file).exists():
        print(f"❌ Error: File not found: {json_file}")
        sys.exit(1)
    
    # แสดง warning ถ้าไฟล์ไม่มี _masked
    if '_masked' not in json_file:
        print("⚠️  Warning: ไฟล์นี้อาจไม่ได้ผ่านการ masking!")
        print("   ควรใช้ไฟล์ที่มี '_masked.json' เพื่อความปลอดภัย\n")
    
    # โหลดข้อมูล
    print(f"📂 Loading: {json_file}")
    masked_data = load_masked_json(json_file)
    
    # ส่งไปยัง Claude
    answer = ask_claude(masked_data, question)
    
    if answer:
        print("💬 Claude AI ตอบ:\n")
        print(answer)
        print(f"\n{'='*60}\n")
        
        # บันทึกคำตอบ
        output_file = json_file.replace('.json', '_claude_answer.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"คำถาม: {question}\n\n")
            f.write(f"{'='*60}\n\n")
            f.write(answer)
        
        print(f"✅ บันทึกคำตอบไว้ที่: {output_file}")
    else:
        print("❌ ไม่สามารถรับคำตอบจาก Claude ได้")
        sys.exit(1)

if __name__ == '__main__':
    main()
