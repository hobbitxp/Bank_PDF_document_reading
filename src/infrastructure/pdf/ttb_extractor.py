"""
TTB (TTB Bank / ธนาคารทหารไทยธนชาต) PDF Statement Extractor

โครงสร้างที่เจอในสเตทเมนต์ออมทรัพย์แบบย่อของ TTB คือคอลัมน์:
    วันที่ | เวลา | รายการ | ช่องทาง | จำนวนเงิน (+/-) | ยอดเงินคงเหลือ

แต่จาก PDF/ข้อความที่ OCR ออกมา กลายเป็นเรียงทีละคอลัมน์แนวตั้งเป็นกลุ่ม ๆ แบบนี้:
    HH:MM
    DD <THAI_MONTH_ABBR>. YY
    <รายละเอียดรายการ อาจยาวหลายบรรทัด>
    <ช่องทาง เช่น KTB / BBL ... (อาจไม่มีในบางรายการ)>
    <จำนวนเงิน เช่น +25,000.00 หรือ -24,600.00>
    <ยอดเงินคงเหลือ เช่น 100,421.94>

ตัวอย่างธุรกรรม (เงินเข้า):
    05:44
    30 ก.ย. 68
    รับเงินโอน
    KTB
    +25,000.00
    100,421.94

ตัวอย่างธุรกรรม (หักชำระสินเชื่ออัตโนมัติ):
    03:20
    25 ก.ย. 68
    หักบัญชีชำระ สินเชื่อ
    อ
    อัตโนมัติ
    -24,600.00
    75,421.94

หมายเหตุ:
- บรรทัดคำอธิบาย ("รายการ") อาจแตกหลายบรรทัด (เช่น "หักบัญชีชำระ สินเชื่อ", "อ", "อัตโนมัติ")
- ช่องทางอาจเป็นตัวย่อธนาคาร เช่น "KTB", "BBL" หรือไม่มีเลย
- จำนวนเงินมีเครื่องหมาย + (เงินเข้า) หรือ - (เงินออก)
- ปีในวันที่เป็น พ.ศ. 2 หลัก (เช่น "68" = 2568 พ.ศ.) ต้องแปลงเป็น พ.ศ.เต็ม หรือ ค.ศ.ถ้าต้องการ datetime
"""

import re
from typing import List, Optional
from datetime import datetime
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    pass  # Will be available in Docker container

from domain.entities.statement import Statement, Transaction
from application.ports.pdf_extractor import IPDFExtractor


class TTBPDFExtractor(IPDFExtractor):
    """Extract transactions from TTB (ทีทีบี/ธนาคารทหารไทยธนชาต) PDF statements"""

    # -----------------------
    # Regex patterns
    # -----------------------
    TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")  # e.g. "05:44"
    MONEY_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})*\.\d{2}$")  # +25,000.00 / -24,600.00 / 100,421.94
    ACCOUNT_RE = re.compile(r"\d{3}-\d-\d{5}-\d")  # e.g. 138-7-06896-6
    DATE_RANGE_RE = re.compile(
        r"(\d{1,2}\s+[ก-ฮ]\S+\s+\d{2})\s*-\s*(\d{1,2}\s+[ก-ฮ]\S+\s+\d{2})"
    )
    THAI_DATE_RE = re.compile(
        r"^(\d{1,2})\s+([ก-ฮ]\S+)\s+(\d{2})$"  # "30 ก.ย. 68"
    )

    # Mapping ย่อเดือนภาษาไทย -> เดือนตัวเลข
    THAI_MONTHS = {
        "ม.ค.": "01",
        "ก.พ.": "02",
        "มี.ค.": "03",
        "เม.ย.": "04",
        "พ.ค.": "05",
        "มิ.ย.": "06",
        "ก.ค.": "07",
        "ส.ค.": "08",
        "ก.ย.": "09",
        "ต.ค.": "10",
        "พ.ย.": "11",
        "ธ.ค.": "12",
    }

    # Heuristic ตรวจว่า line น่าจะเป็นช่องทาง (เช่น "KTB", "BBL")
    CHANNEL_RE = re.compile(r"^[A-Z]{2,6}$")

    # -----------------------
    # Public API
    # -----------------------
    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        เปิด PDF, แตกข้อความทุกหน้า, parse header + transaction list,
        สร้าง Statement object พร้อม Transaction ทั้งหมด
        """
        import fitz
        
        doc = fitz.open(pdf_path)

        # Handle password-protected PDF
        if doc.is_encrypted:
            if not password:
                doc.close()
                raise ValueError("PDF ถูกล็อกด้วยรหัสผ่าน กรุณาระบุ password")
            if not doc.authenticate(password):
                doc.close()
                raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")

        all_transactions: List[Transaction] = []
        page_count = doc.page_count  # Save before closing

        header_info = {
            "account_number": None,
            "statement_date": None,
        }

        for page_index in range(page_count):
            page = doc[page_index]
            page_text = page.get_text()  # raw text
            lines = self._clean_lines(page_text)

            # Header (เอาเฉพาะหน้าแรก)
            if page_index == 0:
                parsed_header = self._parse_header(lines)
                header_info.update(
                    {
                        k: v
                        for k, v in parsed_header.items()
                        if v is not None and header_info.get(k) is None
                    }
                )

            # Transactions (ทุกหน้า)
            page_transactions = self._parse_transactions_from_lines(
                lines, page_num=page_index + 1
            )
            all_transactions.extend(page_transactions)

        doc.close()

        print(f"[TTB] Extracted {len(all_transactions)} transactions from {page_count} pages")

        return Statement(
            source_file=Path(pdf_path).name,
            total_pages=page_count,
            extracted_at=datetime.now(),
            transactions=all_transactions
        )

    # -----------------------
    # Header parsing
    # -----------------------
    def _parse_header(self, lines: List[str]) -> dict:
        """
        ดึงเลขบัญชี และวันสิ้นสุดรอบบัญชีจากส่วนหัวหน้าแรก

        ตัวอย่าง header ที่เจอ:
            "138-7-06896-6"
            "1 เม.ย. 68 - 24 ต.ค. 68"

        คืนค่า:
            {
                "account_number": str|None,
                "statement_date": datetime|None,
            }
        """
        account_number = None
        statement_date: Optional[datetime] = None

        for line in lines:
            if account_number is None:
                m_acc = self.ACCOUNT_RE.search(line)
                if m_acc:
                    account_number = m_acc.group(0)

            if statement_date is None:
                m_range = self.DATE_RANGE_RE.search(line)
                if m_range:
                    # เอาวันที่สิ้นสุดช่วง
                    end_thai_date = m_range.group(2)
                    statement_date = self._thai_date_to_datetime(end_thai_date)

        return {
            "account_number": account_number,
            "statement_date": statement_date,
        }

    # -----------------------
    # Transaction parsing
    # -----------------------
    def _parse_transactions_from_lines(
        self, lines: List[str], page_num: int
    ) -> List[Transaction]:
        """
        เราจะหาธุรกรรมแบบ block ตาม pattern:

            <TIME HH:MM>
            <THAI DATE "30 ก.ย. 68">
            <DESCRIPTION line 1>
            <DESCRIPTION line 2> ... (อาจมีหลายบรรทัด, รวมถึงคำว่า "อัตโนมัติ" ที่โดนตัดบรรทัด)
            [<POSSIBLE CHANNEL like 'KTB'/'BBL'>]
            <AMOUNT +25,000.00 / -24,600.00>
            <BALANCE 100,421.94>

        implementation:
            - เจอ TIME_RE -> เริ่มธุรกรรมใหม่
            - บรรทัดถัดไปต้องเป็นวันที่แบบไทย
            - เก็บ description_lines จนกระทั่งเจอ MONEY_RE (amount)
            - ก่อน amount ถ้าบรรทัดสุดท้ายดูเหมือน channel (อังกฤษตัวใหญ่สั้นๆ)
              เราจะแยกเป็น channel
            - บรรทัดถัดจาก amount คือ balance
        """
        txs: List[Transaction] = []

        i = 0
        n = len(lines)

        while i < n:
            time_line = lines[i]

            # 1) match เวลา
            if not self.TIME_RE.match(time_line):
                i += 1
                continue

            # 2) ต้องมีบรรทัดวันที่ถัดไป
            if i + 1 >= n or not self.THAI_DATE_RE.match(lines[i + 1]):
                # รูปแบบไม่ครบ ข้าม
                i += 1
                continue

            date_line = lines[i + 1]

            # 3) เก็บรายละเอียดตั้งแต่ i+2 เป็นต้นไป จนกว่าจะเจอ amount
            desc_start = i + 2
            j = desc_start
            desc_chunks: List[str] = []

            amount_line_idx = None
            while j < n:
                if self.MONEY_RE.match(lines[j]):
                    amount_line_idx = j
                    break
                desc_chunks.append(lines[j])
                j += 1

            # ถ้าไม่เจอจำนวนเงิน แสดงว่า block ไม่ครบ ให้เลื่อนไปต่อ
            if amount_line_idx is None:
                i += 1
                continue

            # 4) amount และ balance
            amount_line = lines[amount_line_idx]
            balance_line = (
                lines[amount_line_idx + 1] if amount_line_idx + 1 < n else ""
            )

            # 5) แยก channel ออกจาก desc ถ้าเข้าเงื่อนไข
            channel = ""
            if desc_chunks:
                last_chunk = desc_chunks[-1]
                if self.CHANNEL_RE.match(last_chunk):
                    channel = last_chunk
                    desc_chunks = desc_chunks[:-1]

            description = " ".join(desc_chunks)
            description = re.sub(r"\s+", " ", description).strip()

            # 6) parse date/time/amount/is_credit
            date_str = self._thai_date_to_date_string(date_line)
            time_str = time_line

            signed_amount = self._parse_signed_money(amount_line)
            is_credit = signed_amount > 0
            amount_abs = abs(signed_amount)

            # 7) สร้าง Transaction
            tx = Transaction(
                page=page_num,
                line_index=i,
                date=date_str,          # รูปแบบ "DD/MM/2568"
                time=time_str,          # "05:44"
                channel=channel,        # เช่น "KTB", "BBL", หรือ "" ถ้าไม่มี
                description=description,  # "รับเงินโอน", "หักบัญชีชำระ สินเชื่อ อัตโนมัติ", ...
                amount=amount_abs,      # 24600.00 (จำนวนเต็ม ไม่ติด +/-)
                is_credit=is_credit,    # True = เงินเข้า (+), False = เงินออก (-)
                payer=self._infer_payer(description, channel, is_credit),
            )
            txs.append(tx)

            # 8) ขยับ i ไปหลัง balance line
            i = amount_line_idx + 2
            continue

        return txs

    # -----------------------
    # Utilities
    # -----------------------
    def _clean_lines(self, text: str) -> List[str]:
        """ตัด splitlines(), strip(), แล้วทิ้งบรรทัดว่าง"""
        raw_lines = text.splitlines()
        cleaned = [ln.strip() for ln in raw_lines if ln.strip()]
        return cleaned

    def _thai_date_to_date_string(self, thai_date: str) -> str:
        """
        แปลง '30 ก.ย. 68' -> '30/09/2568'

        (หมายเหตุ: ปี พ.ศ. 2568 = 2025 ค.ศ., แต่ Transaction.date ในโปรเจกต์ก่อนหน้า
         เก็บสตริง พ.ศ.เต็ม เราจะตาม format นั้น)
        """
        m = self.THAI_DATE_RE.match(thai_date)
        if not m:
            return thai_date  # fallback raw

        day_str, th_month, yy_be2 = m.groups()
        day = int(day_str)
        month_num = self.THAI_MONTHS.get(th_month, "01")

        # yy_be2 เช่น "68" -> 2568 พ.ศ.
        be_year_full = int("25" + yy_be2)

        return f"{day:02d}/{month_num}/{be_year_full}"

    def _thai_date_to_datetime(self, thai_date: str) -> Optional[datetime]:
        """
        แปลง '24 ต.ค. 68' -> datetime(2025, 10, 24)
        ใช้สำหรับ statement_date (เอาปี ค.ศ.จริง)
        """
        m = self.THAI_DATE_RE.match(thai_date)
        if not m:
            return None

        day_str, th_month, yy_be2 = m.groups()
        day = int(day_str)
        month_num = int(self.THAI_MONTHS.get(th_month, "01"))

        # ปี พ.ศ.เต็ม
        be_year_full = int("25" + yy_be2)  # 2568
        ce_year = be_year_full - 543       # 2025

        return datetime(ce_year, month_num, day)

    def _parse_signed_money(self, s: str) -> float:
        """
        '+25,000.00' -> 25000.0
        '-24,600.00' -> -24600.0
        '100,421.94' -> 100421.94  (ถือว่าเป็นบวกถ้าไม่มีเครื่องหมาย)
        """
        s_clean = s.replace(",", "")
        try:
            return float(s_clean)
        except ValueError:
            # fallback แบบ manual
            sign = -1.0 if s_clean.startswith("-") else 1.0
            num = s_clean.lstrip("+-")
            return sign * float(num)

    def _infer_payer(
        self, description: str, channel: str, is_credit: bool
    ) -> Optional[str]:
        """
        heuristic เติม payer เฉพาะกรณีเงินเข้า (is_credit=True)
        - ถ้า channel เป็นตัวย่อธนาคาร (KTB, BBL) ใช้ channel
        - ถ้า description เริ่มด้วยคำไทย 'รับเงินโอน' แล้วมี channel => channel
        - ถ้าไม่มี อาจคืน None
        """
        if not is_credit:
            return None

        # ถ้ามี channel แบบ KTB / BBL ก็น่าจะเป็นผู้โอนต้นทาง
        if channel:
            return channel

        # ตัดคำแรกดูเผื่อมีชื่อธนาคารตามหลัง
        # (กันเคสอนาคต ถ้ามี pattern อย่าง 'รับเงินโอน KTB')
        tokens = description.split()
        if len(tokens) > 1 and tokens[0].startswith("รับเงินโอน"):
            # หา token ถัดไปที่เป็นตัวอักษรอังกฤษใหญ่ล้วน
            for tk in tokens[1:]:
                if self.CHANNEL_RE.match(tk):
                    return tk

        return None
