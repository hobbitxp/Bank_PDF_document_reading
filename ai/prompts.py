"""
AI prompt templates for bank statement analysis
"""

# System prompts
SYSTEM_PROMPT_FINANCIAL_ADVISOR = """คุณเป็นที่ปรึกษาทางการเงินที่มีความเชี่ยวชาญ
ให้คำแนะนำที่เป็นประโยชน์ แม่นยำ และปฏิบัติได้จริง
วิเคราะห์ข้อมูลการเงินและให้ข้อเสนอแนะสำหรับการจัดการเงินที่ดีขึ้น
ตอบเป็นภาษาไทยที่เข้าใจง่าย ใช้ตัวเลขและตัวอย่างประกอบ"""

SYSTEM_PROMPT_ANALYZER = """คุณเป็นผู้ช่วยวิเคราะห์ข้อมูลทางการเงิน
ให้คำตอบที่แม่นยำ กระชับ และตรงประเด็น
วิเคราะห์รูปแบบการใช้จ่าย หาความผิดปกติ และสรุปข้อมูลสำคัญ
ตอบเป็นภาษาไทยเสมอ"""

SYSTEM_PROMPT_BUDGET_PLANNER = """คุณเป็นผู้เชี่ยวชาญด้านการวางแผนงบประมาณ
ช่วยผู้ใช้วางแผนการใช้จ่ายและออม
ให้คำแนะนำที่สมเหตุสมผลตามสถานการณ์จริง
ตอบเป็นภาษาไทยด้วยน้ำเสียงเป็นมิตร"""

# Query templates
QUERY_TEMPLATES = {
    "summary": """จากข้อมูลStatement นี้ ช่วยสรุปสถานการณ์การเงินให้หน่อย รวมถึง:
1. รายรับ-รายจ่ายรวม
2. หมวดที่จ่ายเยอะสุด 3 อันดับแรก
3. แนวโน้มการใช้จ่าย
4. ข้อสังเกตที่น่าสนใจ""",

    "spending_analysis": """วิเคราะห์รูปแบบการใช้จ่ายในเดือนนี้:
1. จ่ายหมวดไหนบ่อยสุด
2. จ่ายหมวดไหนเยอะสุด
3. ร้านไหนที่ไปบ่อย
4. ช่วงเวลาไหนที่จ่ายเยอะ""",

    "savings_advice": """จากรูปแบบการใช้จ่ายนี้ แนะนำวิธีประหยัดเงินและเพิ่มการออมหน่อย
โดยเฉพาะหมวดที่สามารถลดได้""",

    "anomaly_detection": """ช่วยตรวจสอบรายการที่ผิดปกติ เช่น:
1. รายจ่ายที่สูงผิดปกติ
2. รายการซ้ำๆ ที่น่าสงสัย
3. รายการที่ไม่คุ้นเคย""",

    "budget_recommendation": """ช่วยแนะนำการตั้งงบประมาณสำหรับเดือนหน้า
โดยพิจารณาจากรูปแบบการใช้จ่ายเดือนนี้""",

    "category_breakdown": """แสดงรายละเอียดรายจ่ายแยกตามหมวด พร้อมเปอร์เซ็นต์
และแนะนำว่าหมวดไหนควรลดลง""",

    "merchant_analysis": """วิเคราะห์ร้านค้า/ผู้ขายที่ทำรายการ:
1. ร้านที่ไปบ่อยสุด 5 อันดับ
2. ร้านที่จ่ายเยอะสุด 5 อันดับ
3. ร้านที่ควรลด/หลีกเลี่ยง""",

    "financial_health": """ประเมินสุขภาพการเงินจากStatement นี้:
1. สัดส่วนรายรับ-รายจ่าย
2. การออม
3. ความเสี่ยง
4. คำแนะนำปรับปรุง
ให้คะแนนด้วย (0-100)""",
}

# Example queries
EXAMPLE_QUERIES = [
    "รายจ่ายทั้งหมดเท่าไหร่",
    "รายได้ทั้งหมดเท่าไหร่",
    "ยอดคงเหลือสุดท้าย",
    "รายจ่ายหมวดอาหารเท่าไหร่",
    "จ่ายช้อปปิ้งไปเท่าไหร่",
    "ร้านไหนจ่ายบ่อยสุด",
    "ร้านไหนจ่ายเยอะสุด",
    "จ่าย 7-11 ไปเท่าไหร่",
    "จ่ายเงินช่วงไหนของเดือนบ่อยสุด",
    "วันไหนจ่ายเยอะสุด",
    "ใช้ช่องทางไหนบ่อยสุด",
    "แนะนำการลดค่าใช้จ่าย",
    "รายจ่ายผิดปกติมีไหม",
    "สุขภาพการเงินเป็นยังไง",
    "ควรตั้งงบไว้เท่าไหร่",
]


def format_statement_context(statement_data: dict) -> str:
    """
    Format statement data into context for AI.

    Args:
        statement_data: Parsed statement dictionary

    Returns:
        Formatted context string
    """
    metadata = statement_data.get('metadata', {})
    balance = statement_data.get('balance', {})
    summary = statement_data.get('summary', {})
    transactions = statement_data.get('transactions', [])

    # Basic info
    context = f"""
=== ข้อมูลบัญชี ===
ธนาคาร: {metadata.get('bank', 'N/A')}
เลขบัญชี: {metadata.get('account_number', 'N/A')}
ประเภท: {metadata.get('account_type', 'N/A')}
ระยะเวลา: {metadata.get('statement_period', {}).get('start_date', 'N/A')} - {metadata.get('statement_period', {}).get('end_date', 'N/A')}

=== ยอดเงิน ===
ยอดเริ่มต้น: {balance.get('opening', 0):,.2f} บาท
ยอดสิ้นสุด: {balance.get('closing', 0):,.2f} บาท
ยอดเฉลี่ย: {balance.get('average', 0):,.2f} บาท
เงินเปลี่ยนแปลง: {summary.get('net_change', 0):,.2f} บาท

=== สรุปรายการ ===
จำนวนรายการ: {summary.get('total_transactions', 0)}
รายจ่ายรวม: {summary.get('total_debit', 0):,.2f} บาท ({summary.get('by_type', {}).get('debit_count', 0)} รายการ)
รายรับรวม: {summary.get('total_credit', 0):,.2f} บาท ({summary.get('by_type', {}).get('credit_count', 0)} รายการ)

=== รายจ่ายตามหมวด ===
"""

    # Add categories
    categories = summary.get('by_category', {})
    for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / summary.get('total_debit', 1)) * 100
        context += f"{cat}: {amount:,.2f} บาท ({percentage:.1f}%)\n"

    # Add channels
    context += "\n=== ช่องทางทำรายการ ===\n"
    channels = summary.get('by_channel', {})
    for channel, count in sorted(channels.items(), key=lambda x: x[1], reverse=True):
        context += f"{channel}: {count} รายการ\n"

    # Sample transactions (top 5 by amount)
    if transactions:
        sorted_txns = sorted(transactions, key=lambda x: abs(x.get('amount', 0)), reverse=True)[:5]
        context += "\n=== รายการใหญ่สุด 5 อันดับ ===\n"
        for i, txn in enumerate(sorted_txns, 1):
            context += f"{i}. {txn.get('date')} - {txn.get('description', 'N/A')}: {txn.get('amount', 0):,.2f} บาท\n"

    return context


def create_prompt(query: str, statement_data: dict, template: str = None) -> str:
    """
    Create a complete prompt for AI.

    Args:
        query: User query
        statement_data: Statement data
        template: Optional template name from QUERY_TEMPLATES

    Returns:
        Complete prompt string
    """
    context = format_statement_context(statement_data)

    if template and template in QUERY_TEMPLATES:
        query = QUERY_TEMPLATES[template]

    return f"{context}\n\nคำถาม: {query}\n\nคำตอบ:"


def get_system_prompt(role: str = "analyzer") -> str:
    """
    Get system prompt for a specific role.

    Args:
        role: Role name ('advisor', 'analyzer', 'planner')

    Returns:
        System prompt string
    """
    prompts = {
        "advisor": SYSTEM_PROMPT_FINANCIAL_ADVISOR,
        "analyzer": SYSTEM_PROMPT_ANALYZER,
        "planner": SYSTEM_PROMPT_BUDGET_PLANNER,
    }

    return prompts.get(role, SYSTEM_PROMPT_ANALYZER)
