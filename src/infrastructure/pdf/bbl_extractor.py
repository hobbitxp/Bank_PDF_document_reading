"""
Bangkok Bank PDF Statement Extractor

รูปแบบข้อความหลัง extract ด้วย PyMuPDF (fitz) จากสมุดบัญชี Bangkok Bank:

    01/08/25 B/F
    10,452.63

    01/08/25 TRF. PROMPTPAY
    25.00
    10,427.63 mPhone

    26/08/25 CHEQUE DEP NBK
    144,267.09
    144,420.02 BR1235 อาคารซันทาวเวอรส

    29/08/25 SALARY
    10,313.33
    153,813.35 Auto

ตารางจริงใน statement:
    Date | Particulars | Chq.No. | Withdrawal | Deposit | Balance | Via

แต่ตอนถูก extract เป็น text เส้นมันแตกเป็น 2 หรือ 3 บรรทัดต่อรายการ:
    บรรทัด A: <dd/mm/yy> <รายละเอียดรายการ>
    บรรทัด B: <จำนวนเงิน>     (withdrawal หรือ deposit ของบรรทัด A)
    บรรทัด C: <ยอดคงเหลือหลังรายการ> <ช่องทาง/สาขา/ATM/...>

Exception:
    บรรทัดเปิดงวด "B/F" จะเป็น:
        <dd/mm/yy> B/F
        <ยอดคงเหลือยกมา>
    ไม่มีจำนวนเงิน เพราะไม่ใช่รายการเคลื่อนไหว

แนวคิด parser:
  1. เดินทีละบรรทัด มองหารูปแบบวัน/เดือน/ปี 2 หลัก  -> เริ่ม block ใหม่
  2. ดูบรรทัดต่อๆ ไป:
        case 3 บรรทัด (ปกติ):
            amount_line = money
            bal_line    = "<money> <via...>"
        case 2 บรรทัด (B/F):
            balance_line_only = money
  3. ใช้ balance ก่อนหน้า เพื่อคำนวณว่า amount เป็น credit (+) หรือ debit (-):
        diff = balance_after - balance_before
        ถ้า |diff| == amount -> ทิศทางตาม diff
     ถ้าไม่มี balance_before (เจอครั้งแรก) ก็แค่ตั้งค่า opening balance แล้วข้าม (ไม่บันทึกเป็น Transaction)
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from domain.entities.statement import Statement, Transaction
from application.ports.pdf_extractor import IPDFExtractor


class BangkokBankPDFExtractor(IPDFExtractor):
    """Extract transactions from Bangkok Bank (ธนาคารกรุงเทพ) PDF statements"""

    # -------- regex patterns --------
    DATE_DESC_RE = re.compile(r"^(?P<date>\d{2}/\d{2}/\d{2})\s+(?P<desc>.+)$")
    MONEY_RE = re.compile(r"^[\d,]+\.\d{2}$")
    ACCOUNT_NO_RE = re.compile(r"\d{3}-\d-\d{5}-\d")  # eg. 123-4-63258-4
    PERIOD_RE = re.compile(
        r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})"
    )  # "01/08/2025 - 23/10/2025"

    # ถ้า fallback ต้องทายเครดิตจาก keyword
    CREDIT_HINT_KEYWORDS = {
        "SALARY",
        "CHEQUE DEP",
        "CHEQUE DEP NBK",
        "DEP",
        "DEPOSIT",
    }

    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        เปิด PDF, แตกทุกหน้าเป็นข้อความ, วิ่ง state machine เพื่อดึงรายการ
        คืนค่า Statement ที่มี transactions เรียงตามลำดับในสเตทเมนต์
        """
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)

        if doc.is_encrypted:
            if not password:
                raise ValueError(
                    "PDF นี้ล็อกด้วยรหัสผ่าน ต้องใส่ password เพื่ออ่าน (Bangkok Bank)"
                )
            if not doc.authenticate(password):
                raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")

        # เก็บ header จากหน้าแรก: account_number + statement period
        first_page_text = doc[0].get_text() if doc.page_count > 0 else ""
        account_number, statement_end_dt = self._parse_header(first_page_text)

        # เก็บธุรกรรมทั้งหมด (พร้อมวิธีคำนวณเดบิต/เครดิตด้วย running balance)
        all_transactions: List[Transaction] = []
        prev_balance: Optional[float] = None

        for page_index in range(doc.page_count):
            page_text = doc[page_index].get_text()
            page_transactions, prev_balance = self._parse_page_transactions(
                text=page_text,
                page_num=page_index + 1,
                starting_prev_balance=prev_balance,
            )
            all_transactions.extend(page_transactions)

        page_count = doc.page_count
        doc.close()

        print(f"[BBL] Extracted {len(all_transactions)} transactions from {page_count} pages")

        # สร้าง Statement domain object
        return Statement(
            source_file=pdf_path,
            total_pages=page_count,
            extracted_at=datetime.now(),
            transactions=all_transactions,
        )

    # ------------------------------------------------------------------
    # Core page parser
    # ------------------------------------------------------------------
    def _parse_page_transactions(
        self,
        text: str,
        page_num: int,
        starting_prev_balance: Optional[float],
    ) -> Tuple[List[Transaction], Optional[float]]:
        """
        แตก text ของหน้านั้นเป็นบรรทัด แล้วจับ block 2-3 บรรทัดตาม format BBL
        คืน (transactions ในหน้านี้, balance ล่าสุดหลัง parse หน้านี้)
        """
        lines = [
            ln.strip()
            for ln in text.splitlines()
            if ln.strip()
        ]

        txs: List[Transaction] = []
        idx = 0
        prev_balance = starting_prev_balance

        while idx < len(lines):
            line0 = lines[idx]
            m = self.DATE_DESC_RE.match(line0)
            if not m:
                idx += 1
                continue

            raw_date = m.group("date")  # "01/08/25"
            desc_txt = m.group("desc").strip()  # "TRF. PROMPTPAY", "SALARY", "B/F", ...

            # เตรียม lookahead
            l1 = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            l2 = lines[idx + 2].strip() if idx + 2 < len(lines) else ""

            # helper
            def is_money(val: str) -> bool:
                return bool(self.MONEY_RE.match(val))

            # ดูว่าเป็นบล็อก 3 บรรทัดธุรกรรม หรือบรรทัดยอดยกมา (B/F)
            if is_money(l1):
                # candidate for triple-line:
                #   l1 = amount
                #   l2 = "<balance_after> <via...>"
                # แต่ถ้าเป็น B/F มันจะไม่มี l2 เป็นเงิน
                l2_first = l2.split()[0] if l2 else ""

                # เคสยอดยกมา (B/F): ไม่มีบรรทัด balance+via แยกชัด
                # จะหน้าตาแบบ:
                #   01/08/25 B/F
                #   10,452.63
                # next line คือรายการถัดไปแล้ว (ไม่ใช่ยอด+ช่องทาง)
                if desc_txt.upper().startswith("B/F") or not is_money(l2_first):
                    # นี่คือ opening balance; อัปเดต prev_balance แล้วไม่สร้าง Transaction
                    prev_balance = self._parse_money(l1)
                    idx += 2
                    continue

                # ปกติธุรกรรม 3 บรรทัด
                amount_val = self._parse_money(l1)

                balance_after = self._parse_money(l2_first)
                via_detail = l2[len(l2_first) :].strip()  # "mPhone", "ATM ...", "Auto", ...

                # ตัดสินว่าเครดิต (เงินเข้า) หรือเดบิต (เงินออก)
                is_credit = self._decide_credit_flag(
                    desc_txt=desc_txt,
                    amount=amount_val,
                    new_balance=balance_after,
                    old_balance=prev_balance,
                )

                # เวลาของ BBL statement ไม่มีในแต่ละแถว → ใช้ "" (หรือ "00:00")
                txs.append(
                    Transaction(
                        page=page_num,
                        line_index=idx,
                        date=self._normalize_date(raw_date),
                        time="",  # ไม่มีเวลาในสเตทเมนต์ของ BBL
                        channel=desc_txt,  # ex. "TRF. PROMPTPAY", "SALARY", ...
                        description=via_detail,  # ex. "mPhone", "ATM เจริญพาศน์", "Auto"
                        amount=amount_val,
                        is_credit=is_credit,
                        payer=self._extract_payer(desc_txt, via_detail, is_credit),
                    )
                )

                # อัปเดต running balance
                prev_balance = balance_after

                # consume 3 lines
                idx += 3
                continue

            # ถ้า l1 ไม่ใช่ตัวเงิน เราถือว่า format แปลก/ข้าม
            idx += 1

        return txs, prev_balance

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_header(
        self,
        first_page_text: str,
    ) -> Tuple[Optional[str], Optional[datetime]]:
        """
        ดึงเลขที่บัญชี และวันปิดงวด statement
        จาก header ของหน้าแรก เช่น:
            เลขที่บัญชี/Account No.
            123-4-63258-4
            ...
            รอบรายการบัญชี / Statement Period
            01/08/2025 - 23/10/2025
        """
        account_number = None
        end_date = None

        for line in first_page_text.splitlines():
            line = line.strip()

            if account_number is None:
                acct_match = self.ACCOUNT_NO_RE.search(line)
                if acct_match:
                    account_number = acct_match.group(0)

            if end_date is None:
                period_match = self.PERIOD_RE.search(line)
                if period_match:
                    # second group is the period end date
                    _, end_str = period_match.groups()
                    try:
                        end_date = datetime.strptime(end_str, "%d/%m/%Y")
                    except ValueError:
                        end_date = None

        return account_number, end_date

    def _parse_money(self, money_str: str) -> float:
        """Convert '144,267.09' -> 144267.09 (float)"""
        return float(money_str.replace(",", ""))

    def _normalize_date(self, dmy_short: str) -> str:
        """
        รับ "01/08/25" -> "01/08/2025"
        Bangkok Bank ใช้ ค.ศ. 2 หลักท้ายในตาราง (25=2025)
        """
        day, month, yy = dmy_short.split("/")
        year_full = 2000 + int(yy)  # 25 -> 2025
        return f"{day}/{month}/{year_full}"

    def _decide_credit_flag(
        self,
        desc_txt: str,
        amount: float,
        new_balance: float,
        old_balance: Optional[float],
    ) -> bool:
        """
        พยายามระบุว่านี่คือเงินเข้า (credit=True) หรือเงินออก (credit=False)

        1. ถ้าเรามี old_balance:
            diff = new_balance - old_balance
            ถ้า abs(|diff| - amount) <= 0.01:
                diff > 0  -> credit
                diff < 0  -> debit
        2. fallback: keyword hint (เช่น "SALARY", "CHEQUE DEP NBK")
        3. default = False (สมมติว่าเงินออก)
        """
        if old_balance is not None:
            diff = round(new_balance - old_balance, 2)
            if abs(abs(diff) - amount) <= 0.01:
                if diff > 0:
                    return True
                if diff < 0:
                    return False

        # fallback keyword guess
        up = desc_txt.upper()
        for kw in self.CREDIT_HINT_KEYWORDS:
            if kw in up:
                return True

        # else assume it's a withdrawal
        return False

    def _extract_payer(
        self,
        desc_txt: str,
        via_detail: str,
        is_credit: bool,
    ) -> Optional[str]:
        """
        ใส่ข้อมูลผู้จ่าย/นายจ้างแบบหยาบ ๆ สำหรับเคสเงินเข้า
        เช่น:
           "SALARY" -> "SALARY"
           "CHEQUE DEP NBK" -> "CHEQUE DEP NBK"
        ที่เหลือไม่มีข้อมูลต้นทางชัดเจน (PromptPay ไม่ให้ชื่อในสเตทเมนต์นี้)
        """
        if not is_credit:
            return None

        up_desc = desc_txt.upper()

        if "SALARY" in up_desc:
            return "SALARY"

        if "CHEQUE DEP" in up_desc:
            return "CHEQUE DEP"

        # บางที channel "Auto" อาจบอก payroll system อื่น ๆ
        if via_detail and via_detail.upper().startswith("AUTO"):
            return via_detail.strip()

        return None
