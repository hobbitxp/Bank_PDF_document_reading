"""
KTB (Krungthai Bank) PDF Statement Extractor

รูปแบบที่เจอจริง (จากตัวอย่างที่ให้มา):

บล็อคธุรกรรม 1 รายการ = 7 บรรทัดหลัก

    0: DD/MM/YY
    1: ประเภทรายการ (เช่น "เงินเดือน/อื่นๆ (BSD02)" หรือ "จ่ายค่าสินค้า/บริการ (NBSWP)")
    2: รายละเอียด (description / reference / หมายเลข / counterparty)
    3: จำนวนเงินของรายการ (เดบิตหรือเครดิตก็อยู่บรรทัดนี้เลย)
    4: ยอดคงเหลือหลังรายการ
    5: รหัสสาขา/ช่องทาง (เช่น 1400, 108682, 1309)
    6: เวลา (HH:MM)

ตัวอย่าง (เครดิตเข้าบัญชี):
    30/09/68
    เงินเดือน/อื่นๆ (BSD02)
    SG CAPITAL/เอสจี แคปปิตอล/200000 
    84,150.00
    84,715.87
    108682
    04:04

ตัวอย่าง (เดบิตออก):
    01/10/68
    จ่ายค่าสินค้า/บริการ (NBSWP)
    24184-20251001002152780649~ Future Amount:
    10,690.37
    29,361.01
    1400
    02:15
    10690.37 ~ Tran: NBSWP      <-- บรรทัด extra หลังจากนั้น (metadata) ให้ข้ามได้

หมายเหตุสำคัญ:
- หลังบรรทัดเวลาอาจมีบรรทัดเสริม ("~ Tran:", "Future Amount:", etc.) ก่อนจะเริ่มรายการถัดไป
  เราจะไม่พึ่งจำนวนบรรทัดตายตัวแบบ i += 10 อีกต่อไป แต่จะกระโดดไปที่ start_idx + 7 แล้วปล่อยลูปเดินต่อ
- ในหน้า PDF มี header ที่มีวันที่เหมือนกัน (เช่น "วันที่ส่งคำขอ\n24/10/68") ซึ่งจะหลอก regex วัน
  ดังนั้นก่อน parse ธุรกรรม เราจะตรวจเพิ่มว่า บรรทัดถัดจากวันที่ต้องมีวงเล็บโค้ดธุรกรรม เช่น "(MORISW)", "(BSD02)" ฯลฯ
"""

import re
from typing import List, Optional
from datetime import datetime

import fitz  # PyMuPDF

from domain.entities.statement import Statement, Transaction
from application.ports.pdf_extractor import IPDFExtractor


import re
from typing import List, Optional
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    pass  # Will be available in Docker container

from domain.entities.statement import Statement, Transaction
from application.ports.pdf_extractor import IPDFExtractor


class KTBPDFExtractor(IPDFExtractor):
    """Extract transactions from KTB (Krungthai Bank) PDF statements"""

    # -----------------------
    # Regex patterns
    # -----------------------
    DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")          # e.g. 30/09/68
    TIME_RE = re.compile(r"^(\d{2}):(\d{2})$")                  # e.g. 04:04
    MONEY_RE = re.compile(r"^[\d,]+\.\d{2}$")                   # e.g. 84,150.00

    BRANCH_RE = re.compile(r"^\d{3,9}$")                        # e.g. 1400, 108682, 1309

    # -----------------------
    # Keywords สำหรับจัดหมวดเครดิต/เดบิต
    # -----------------------
    CREDIT_KEYWORDS = {
        "เงินเดือน",
        "เงินเดือน/อื่นๆ",
        "เงินโอนเข้า",
        "ฝากเงิน",
        "BSD02",
        "IORSDT",
        "SDCH",
    }

    DEBIT_KEYWORDS = {
        "โอนเงินออก",
        "ถอนเงิน",
        "ถอนเงินไม่ใช้บัตร",
        "จ่ายค่าสินค้า",
        "จ่ายค่าบริการ",
        "IORSWT",
        "NBSWT",
        "MORWSW",
        "MORISW",
        "NMIDSW",
        "MORPSW",
        "NBSWP",
        "CGSWP",
        "ATSWCR",
    }

    # -----------------------
    # Public API
    # -----------------------
    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        เปิด PDF → วิ่งทุกหน้า → ดึงธุรกรรม → รวมเป็น Statement
        """
        import fitz

        doc = fitz.open(pdf_path)

        # handle password-protected PDFs
        if doc.is_encrypted:
            if not password:
                raise ValueError("PDF มีการป้องกันด้วยรหัสผ่าน กรุณาระบุรหัสผ่าน")

            # authenticate() คืนค่า >0 ถ้า success
            if not doc.authenticate(password):
                raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")

        all_transactions: List[Transaction] = []
        page_count = doc.page_count  # Save before closing

        for page_index in range(page_count):
            page = doc[page_index]
            text = page.get_text("text")
            page_transactions = self._extract_transactions_from_text(
                text,
                page_num=page_index + 1,
            )
            all_transactions.extend(page_transactions)

        doc.close()

        print(f"[KTB] Extracted {len(all_transactions)} transactions from {page_count} pages")

        return Statement(
            source_file=pdf_path,
            total_pages=page_count,
            extracted_at=datetime.now(),
            transactions=all_transactions
        )

    # -----------------------
    # Page-level extraction
    # -----------------------
    def _extract_transactions_from_text(self, text: str, page_num: int) -> List[Transaction]:
        """
        เดินบรรทัดในหน้านั้น แล้วจับ block ธุรกรรมทีละก้อน
        """
        raw_lines = text.split("\n")

        transactions: List[Transaction] = []
        i = 0
        n = len(raw_lines)

        while i < n:
            line = raw_lines[i].strip()

            date_match = self.DATE_RE.match(line)
            if date_match:
                # เพื่อกัน false positive จาก header เช่น:
                #   วันที่ส่งคำขอ
                #   24/10/68
                #   ชื่อบัญชี
                # => ไม่ใช่ธุรกรรมจริง
                #
                # ธุรกรรมจริง บรรทัดถัดจากวันที่ต้องมีรูปแบบ "<ข้อความ> (<CODE>)"
                tx_type_candidate = raw_lines[i + 1].strip() if i + 1 < n else ""
                if "(" in tx_type_candidate and ")" in tx_type_candidate:
                    tx = self._parse_transaction_block(raw_lines, i, page_num)
                    if tx:
                        transactions.append(tx)
                        # กระโดดไปหลังบล็อคหลัก (7 บรรทัดแรกของรายการ)
                        i = i + 7
                        continue

            i += 1

        return transactions

    # -----------------------
    # Block parser (ธุรกรรมเดียว)
    # -----------------------
    def _parse_transaction_block(
        self,
        lines: List[str],
        start_idx: int,
        page_num: int,
    ) -> Optional[Transaction]:
        """
        โครงสร้างธุรกรรมจาก statement กรุงไทย:

        index (จาก start_idx):
            0: วันที่ dd/mm/yy
            1: ประเภทรายการ เช่น "เงินเดือน/อื่นๆ (BSD02)" หรือ "โอนเงินออก-พร้อมเพย์ (MORISW)"
            2: รายละเอียด/หมายเลขอ้างอิง
            3: จำนวนเงินของรายการ
            4: ยอดคงเหลือหลังรายการ
            5: รหัสสาขา/ช่องทาง (ตัวเลขล้วน เช่น 1400, 108682, 1309)
            6: เวลา HH:MM

        หลังบรรทัด index 6 อาจมีบรรทัดเสริม ("~ Tran: ...", "Future Amount: ...")
        เราไม่นับเป็นส่วนธุรกรรมหลัก
        """

        # ต้องมีอย่างน้อย 7 บรรทัดให้ครบ index 0..6
        if start_idx + 6 >= len(lines):
            return None

        # 0: วันที่
        date_line = lines[start_idx].strip()
        if not self.DATE_RE.match(date_line):
            return None

        # 1: ประเภทรายการ
        tx_type_line = lines[start_idx + 1].strip()
        # sanity check อีกชั้น: ต้องไม่น่าใช่ header
        # ส่วนใหญ่ธุรกรรมจะมีวงเล็บท้าย เช่น "(MORISW)"
        if "(" not in tx_type_line or ")" not in tx_type_line:
            return None

        # 2: รายละเอียด
        detail_line = lines[start_idx + 2].strip()

        # 3: จำนวนเงินของรายการ
        amount_line = lines[start_idx + 3].strip()
        if not self.MONEY_RE.match(amount_line):
            # ถ้าไม่ใช่รูปแบบเงิน ปกติคือ block นี้บิดเพี้ยน ก็ขอ reject
            return None
        amount_val = self._parse_money(amount_line)

        # 4: ยอดคงเหลือ (เรา parse เผื่อ debug/ตรวจ cross, ถึงแม้ Transaction domain ตอนนี้อาจยังไม่เก็บ)
        balance_line = lines[start_idx + 4].strip()
        balance_val = None
        if self.MONEY_RE.match(balance_line):
            balance_val = self._parse_money(balance_line)

        # 5: สาขา / channel code
        branch_line = lines[start_idx + 5].strip()
        channel_val = branch_line if self.BRANCH_RE.match(branch_line) else None

        # 6: เวลา
        time_line = lines[start_idx + 6].strip()
        time_match = self.TIME_RE.match(time_line)
        time_val = time_line if time_match else None

        # จัดหมวดเครดิต/เดบิตจากชื่อรายการ (tx_type_line)
        is_credit = self._is_credit_transaction(tx_type_line)

        # หา payer ถ้าเป็นเครดิต (เช่นเงินเดือน)
        payer_val = self._extract_payer(detail_line) if is_credit else None

        # เราไม่มี field tx_type แยกใน Transaction domain ที่คุณ import มา
        # งั้น description จะรวมทั้ง tx_type_line + detail_line เพื่อไม่เสียข้อมูล
        # เช่น:
        #   "เงินเดือน/อื่นๆ (BSD02) | SG CAPITAL/เอสจี แคปปิตอล/200000"
        full_description = f"{tx_type_line} | {detail_line}"

        # คืน Transaction domain object ของระบบหลักคุณ
        return Transaction(
            page=page_num,
            line_index=start_idx,
            date=date_line,             # เก็บแบบ dd/mm/yy ตามต้นฉบับ (ปี พ.ศ. ตัดเหลือสองหลัก)
            time=time_val,
            channel=channel_val,        # ใช้ช่องนี้เป็นรหัสสาขา / channel code (เช่น 1400, 108682)
            description=full_description,
            amount=amount_val,
            is_credit=is_credit,
            payer=payer_val,
        )

    # -----------------------
    # Helpers
    # -----------------------
    def _is_credit_transaction(self, tx_type_line: str) -> bool:
        """
        ตัดสินว่าเป็นเงินเข้าไหม (credit)
        heuristic:
        - ถ้ามี keyword ฝั่งเครดิต → True
        - ถ้ามี keyword ฝั่งเดบิต → False
        - fallback: คำบางคำในภาษาไทย
        """

        tx_upper = tx_type_line.upper()

        # ถ้ามีคำที่บ่งบอกว่า "เข้า"
        for kw in self.CREDIT_KEYWORDS:
            if kw.upper() in tx_upper:
                return True

        # ถ้ามีคำที่บ่งบอกว่า "ออก"
        for kw in self.DEBIT_KEYWORDS:
            if kw.upper() in tx_upper:
                return False

        # fallback heuristic ภาษาธรรมดา
        # "รับ", "ฝาก" -> เข้า
        if ("รับ" in tx_type_line) or ("ฝาก" in tx_type_line):
            return True

        # "จ่าย", "โอนออก", "ถอน" -> ออก
        if ("จ่าย" in tx_type_line) or ("โอน" in tx_type_line) or ("ถอน" in tx_type_line):
            return False

        # default → ถือว่าเป็นเดบิต (ระมัดระวัง)
        return False

    def _extract_payer(self, detail_line: str) -> Optional[str]:
        """
        ดึงชื่อผู้จ่าย / บริษัท / แหล่งที่มาของเครดิตเข้า
        ตัวอย่าง:
            "SG CAPITAL/เอสจี แคปปิตอล/200000" → "SG CAPITAL"
            "014-1114765247"                    → None
        """
        if not detail_line:
            return None

        # กรณีข้อความแบบ "SG CAPITAL/เอสจี แคปปิตอล/200000"
        if "/" in detail_line:
            first_part = detail_line.split("/")[0].strip()
            # กรองไม่ให้คืนค่าเป็นตัวเลขบัญชีล้วน ๆ
            if len(first_part) > 3 and not first_part.replace("-", "").isdigit():
                return first_part

        # กรณีคำแรกเป็นชื่อบริษัทตัวใหญ่
        parts = detail_line.split()
        if parts:
            first_word = parts[0].strip()
            if len(first_word) > 2 and first_word.isupper() and not first_word.replace("-", "").isdigit():
                return first_word

        return None

    def _parse_money(self, money_str: str) -> float:
        """
        "84,150.00" -> 84150.00 (float)
        "1,107.55"  -> 1107.55
        "1.00"      -> 1.0
        """
        return float(money_str.replace(",", ""))

