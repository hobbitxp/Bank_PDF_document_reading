"""
SCB (Siam Commercial Bank) PDF Statement Extractor

รูปแบบข้อความหลัง extract ด้วย PyMuPDF (fitz) จากสมุดบัญชี SCB ที่คุณให้:

Header (เจอทุกหน้า):
    ธนาคารไทยพาณิชย์ จำกัด (มหาชน)
    ...
    เลขที่บัญชี 111-476524-7
    01/02/2025 - 28/02/2025
    ...

ตารางธุรกรรม:
    ยอดเงินคงเหลือยกมา (BALANCE BROUGHT FORWARD)
    38.89

    01/02/25
    15:31
    X1
    ENET
    35,000.00
    35,038.89 กสิกรไทย (KBANK) /X685027

    02/02/25
    16:35
    X2
    SIPI
    4,000.00
    31,038.89 SIPS TRUE MONEY CO.,LTD.

    ...

โครงของแต่ละรายการ 1 รายการ = 6 บรรทัดติดกัน:
    [0] วันที่ (DD/MM/YY)
    [1] เวลา (HH:MM)
    [2] Code (เช่น X1, X2)
    [3] ช่องทาง/ประเภท (เช่น ENET, SIPI, CDM)
    [4] จำนวนเงิน (ไม่มีเครื่องหมายบวก/ลบ)
    [5] "<ยอดคงเหลือหลังรายการ> <ช่องว่าง> <รายละเอียดเต็ม>"

หมายเหตุ:
    - เครดิต (เงินเข้า) / เดบิต (เงินออก) แยกจากการเปลี่ยนยอดคงเหลือ:
        ถ้ายอดคงเหลือหลัง > ยอดคงเหลือก่อนหน้า => is_credit = True
        ไม่งั้น => is_credit = False
    - หน้าใหม่จะขึ้น "ยอดเงินคงเหลือยกมา (BALANCE BROUGHT FORWARD)" อีกรอบ
      บางหน้าจะตามด้วยยอดคงเหลือเดิม (เช่น "38.89") บางหน้าไม่มีก็ได้
    - ปีในสเตทเมนต์ SCB เป็นคริสต์ศักราชย่อ 2 หลัก (25 = 2025),
      ต่างจาก KTB ที่เป็น พ.ศ. 68 = 2568

Dependencies ภายนอก:
    - PyMuPDF (fitz)
    - domain.entities.statement.Statement, Transaction
    - application.ports.pdf_extractor.IPDFExtractor
"""

import re
from typing import List, Optional, Tuple
from datetime import datetime

from domain.entities.statement import Statement, Transaction
from application.ports.pdf_extractor import IPDFExtractor


class SCBPDFExtractor(IPDFExtractor):
    """Extract transactions from SCB (ธนาคารไทยพาณิชย์) PDF statements"""

    # ------------------
    # Regex patterns
    # ------------------
    DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")  # เช่น "01/02/25"
    TIME_RE = re.compile(r"^(\d{2}):(\d{2})$")          # เช่น "15:31"
    CODE_RE = re.compile(r"^[A-Z]\d$")                 # เช่น "X1", "X2"
    CHANNEL_RE = re.compile(r"^[A-Z]+$")               # เช่น "ENET", "SIPI", "CDM"
    MONEY_RE = re.compile(r"^\d{1,3}(?:,\d{3})*\.\d{2}$")
    BALANCE_DESC_RE = re.compile(
        r"^(\d{1,3}(?:,\d{3})*\.\d{2})\s+(.+)$"
    )
    ACCOUNT_NO_RE = re.compile(r"\b(\d{3}-\d{6}-\d)\b")
    DATE_RANGE_RE = re.compile(
        r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})"
    )

    # ------------------
    # Public API
    # ------------------
    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        อ่านไฟล์ PDF แล้วคืน Statement ที่ประกอบด้วยรายการธุรกรรมทั้งหมด
        """
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)

        # handle password-protected PDF
        if doc.is_encrypted:
            if not password:
                raise ValueError(
                    "PDF มีการป้องกันด้วยรหัสผ่าน กรุณาระบุรหัสผ่าน"
                )
            if not doc.authenticate(password):
                raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")

        # เก็บทุกบรรทัดจากทุกหน้า โดยจำหน้ากับ line index ไว้ด้วย
        lines_info = []  # List[(page_no, line_index, text)]
        full_text_pages: List[str] = []

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            full_text_pages.append(text)

            for line_idx, raw_line in enumerate(text.splitlines()):
                lines_info.append(
                    (page_num + 1, line_idx, raw_line.strip())
                )

        page_count = doc.page_count
        doc.close()

        # ดึง account number และ statement_date (ใช้วันสุดท้ายของงวด)
        account_no, stmt_date = self._parse_header_metadata(
            "\n".join(full_text_pages)
        )

        # แปลงบรรทัดดิบทั้งหมด -> Transaction[]
        transactions = self._extract_transactions_from_lines(lines_info)

        print(f"[SCB] Extracted {len(transactions)} transactions from {page_count} pages")

        return Statement(
            source_file=pdf_path,
            total_pages=page_count,
            extracted_at=datetime.now(),
            transactions=transactions,
        )

    # ------------------
    # Internal helpers
    # ------------------
    def _parse_header_metadata(
        self,
        full_text: str,
    ) -> Tuple[Optional[str], Optional[datetime]]:
        """
        ดึงข้อมูลหัวสเตทเมนต์:
        - เลขที่บัญชี เช่น "111-476524-7"
        - ระยะเวลา statement เช่น "01/02/2025 - 28/02/2025"
          -> คืนค่าวันสุดท้ายเป็น statement_date
        """
        account_no = None
        acc_match = self.ACCOUNT_NO_RE.search(full_text)
        if acc_match:
            account_no = acc_match.group(1)

        stmt_date = None
        range_match = self.DATE_RANGE_RE.search(full_text)
        if range_match:
            _, end_date = range_match.groups()
            try:
                stmt_date = datetime.strptime(end_date, "%d/%m/%Y")
            except ValueError:
                # ถ้า parse ไม่ได้ ก็ปล่อยไว้เป็น None
                stmt_date = None

        return account_no, stmt_date

    def _extract_transactions_from_lines(
        self,
        lines_info: List[tuple],
    ) -> List[Transaction]:
        """
        core parser:
        - เดินไล่ทีละบรรทัด
        - เจอคำว่า "ยอดเงินคงเหลือยกมา" -> เก็บยอดคงเหลือเริ่มต้น
        - เจอ pattern วันที่ DD/MM/YY -> อ่าน block 6 บรรทัด
        """
        transactions: List[Transaction] = []
        prev_balance: Optional[float] = None  # จะใช้เทียบว่าเงินเข้า/ออก

        i = 0
        n = len(lines_info)

        while i < n:
            cur_line = lines_info[i][2]

            # 1) ถ้าเป็น "ยอดเงินคงเหลือยกมา (BALANCE BROUGHT FORWARD)"
            #    ให้พยายามอ่านยอดคงเหลือเริ่มต้นจากบรรทัดถัดไป (เช่น "38.89")
            if (
                "ยอดเงินคงเหลือยกมา" in cur_line
                or "BALANCE BROUGHT FORWARD" in cur_line.upper()
            ):
                j = i + 1
                # ข้ามบรรทัดว่าง
                while j < n and lines_info[j][2] == "":
                    j += 1

                if j < n:
                    candidate = lines_info[j][2]
                    if self.MONEY_RE.match(candidate):
                        prev_balance = self._parse_money(candidate)
                        i = j + 1
                        continue

                i += 1
                continue

            # 2) เช็คว่าเป็นต้นบล็อกธุรกรรมหรือไม่ (ขึ้นต้นด้วยวันที่ DD/MM/YY)
            date_match = self.DATE_RE.match(cur_line)
            if date_match and i + 5 < n:
                date_line = lines_info[i][2]
                time_line = lines_info[i + 1][2]
                code_line = lines_info[i + 2][2]
                channel_line = lines_info[i + 3][2]
                amount_line = lines_info[i + 4][2]
                bal_desc_line = lines_info[i + 5][2]

                # validate โครง 6 บรรทัด
                is_valid_block = (
                    self.TIME_RE.match(time_line)
                    and self.CODE_RE.match(code_line)
                    and self.CHANNEL_RE.match(channel_line)
                    and self.MONEY_RE.match(amount_line)
                )

                if is_valid_block:
                    bal_desc_match = self.BALANCE_DESC_RE.match(bal_desc_line)
                    if bal_desc_match:
                        balance_after_raw, desc_raw = bal_desc_match.groups()

                        amount = self._parse_money(amount_line)
                        balance_after = self._parse_money(balance_after_raw)
                        description = desc_raw.strip()

                        # ตัดสินว่าเป็นเครดิตหรือเดบิต
                        # ถ้ายอดหลัง > ยอดก่อน => เงินเข้า
                        if prev_balance is None:
                            is_credit = True
                        else:
                            is_credit = balance_after > prev_balance

                        # ฝั่งคู่รายการ (เช่น ชื่อธนาคารต้นทาง)
                        payer = self._extract_counterparty(
                            description,
                            is_credit=is_credit,
                        )

                        transactions.append(
                            Transaction(
                                page=lines_info[i][0],
                                line_index=lines_info[i][1],
                                date=self._normalize_date(date_line),
                                time=time_line,
                                channel=f"{code_line} {channel_line}",
                                description=description,
                                amount=amount,
                                is_credit=is_credit,
                                payer=payer,
                            )
                        )

                        # อัปเดตยอดคงเหลือล่าสุดสำหรับรายการถัดไป
                        prev_balance = balance_after

                        # กระโดดข้ามทั้ง block 6 บรรทัด
                        i += 6
                        continue

            # ถ้าไม่ตรง pattern ก็ไปบรรทัดถัดไป
            i += 1

        return transactions

    def _normalize_date(self, d: str) -> str:
        """
        ปรับรูปแบบวันที่จาก 'DD/MM/YY' ให้เป็น 'DD/MM/YYYY'

        กติกา:
        - SCB ใช้ ค.ศ. 2 หลัก เช่น 25 -> 2025
        - ถ้า YY >= 60 ให้เดาว่าเป็นปี พ.ศ. 25YY (เช่น '68' -> '2568')
          เพื่อให้ใช้ parser ตัวเดียวกับ statement แบบอื่นได้ในอนาคต
        """
        m = self.DATE_RE.match(d)
        if not m:
            return d

        day, month, yy = m.groups()
        yy_int = int(yy)

        if yy_int >= 60:
            # สมมติเป็นพ.ศ. เช่น '68' -> '2568'
            year_full = f"25{yy}"
        else:
            # สมมติเป็นค.ศ. เช่น '25' -> '2025'
            year_full = f"20{yy.zfill(2)}"

        return f"{day}/{month}/{year_full}"

    def _parse_money(self, money_str: str) -> float:
        """แปลงสตริงจำนวนเงินแบบ '35,000.00' -> float 35000.0"""
        return float(money_str.replace(",", ""))

    def _extract_counterparty(
        self,
        description: str,
        is_credit: bool,
    ) -> Optional[str]:
        """
        ดึงชื่อคู่รายการ/ผู้โอน (payer) ถ้าเป็นเงินเข้า
        ตัวอย่าง:
            "กสิกรไทย (KBANK) /X685027"
            -> "กสิกรไทย (KBANK)"

        ถ้าไม่ใช่เงินเข้า ให้คืน None
        """
        if not is_credit or not description:
            return None

        if "/" in description:
            left = description.split("/", 1)[0].strip()
            if left:
                return left

        return None
