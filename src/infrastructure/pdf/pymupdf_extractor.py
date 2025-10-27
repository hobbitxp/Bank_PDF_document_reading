"""
Infrastructure Adapter: PyMuPDF Extractor
Implements IPDFExtractor using PyMuPDF (fitz) library

เวอร์ชันนี้ออกแบบมาเพื่อรองรับ statement รูปแบบ KBank Mobile/K PLUS
โดยใช้ state machine ดึงแต่ละธุรกรรมแบบ block:

[วันที่] -> [เวลา] -> [ช่องทาง (อาจหลายบรรทัด)] -> [ยอดคงเหลือหลังรายการ]
-> [รายละเอียดหลายบรรทัด] -> [ประเภทธุรกรรม] -> [จำนวนเงินของรายการ]

พร้อมระบุเดบิต / เครดิต ชัดเจน
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import logging

from application.ports.pdf_extractor import IPDFExtractor
from domain.entities.statement import Statement
from domain.entities.transaction import Transaction

logger = logging.getLogger(__name__)


class PyMuPDFExtractor(IPDFExtractor):
    """
    PDF extraction using PyMuPDF (fitz) + KBank statement state machine parser
    """

    # =========================
    # -------- PUBLIC ---------
    # =========================

    def extract(self, pdf_path: str, password: Optional[str] = None) -> Statement:
        """
        Extract text and transactions from a PDF statement.
        Returns a Statement entity containing pages + all parsed Transaction objects.
        """

        # --- เปิดไฟล์ PDF ---
        doc = fitz.open(pdf_path)

        # --- จัดการกรณีไฟล์ล็อก ---
        if doc.is_encrypted:
            if password:
                if not doc.authenticate(password):
                    doc.close()
                    raise ValueError("รหัสผ่าน PDF ไม่ถูกต้อง")
            else:
                doc.close()
                raise ValueError("PDF มีการป้องกันด้วยรหัสผ่าน กรุณาระบุรหัสผ่าน")

        # --- เตรียม Statement domain entity ---
        statement = Statement(
            source_file=Path(pdf_path).name,
            total_pages=len(doc),
            extracted_at=datetime.now(),
            pages=[]
        )

        # --- วนทุกหน้า ---
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page.get_text()
            lines = [ln for ln in text.split("\n") if ln.strip()]

            # เก็บ raw text เข้า statement.pages เพื่อ debug / เก็บหลักฐาน
            statement.pages.append({
                "page_number": page_index + 1,
                "text": text,
                "lines": lines,
            })

            # สกัดธุรกรรมจากหน้านี้
            page_transactions = self._extract_transactions_from_text(
                lines=lines,
                page_num=page_index + 1,
            )

            # ใส่เข้า statement
            for tx in page_transactions:
                statement.add_transaction(tx)

        doc.close()
        return statement

    # =========================
    # ------- INTERNAL --------
    # =========================

    # ---------- REGEX / CONSTANTS ----------
    DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}$")             # เช่น "01-04-25"
    TIME_RE = re.compile(r"^\d{2}:\d{2}$")                    # เช่น "05:27"
    MONEY_RE = re.compile(r"^\d{1,3}(?:,\d{3})*\.\d{2}$")     # เช่น "12,278.00" หรือ "875.50"

    # ธนาคารใช้คำเหล่านี้เป็น "ประเภทธุรกรรม" (tx_type)
    TX_TYPE_KEYWORDS_DEBIT = {
        "ชำระเงิน",        # จ่ายบิล / จ่ายร้าน
        "โอนเงิน",        # โอนไป ...
        "ถอนเงินสด",       # กดเงิน
    }
    TX_TYPE_KEYWORDS_CREDIT = {
        "รับโอนเงิน",          # รับโอนเงิน
        "รับโอนเงินอัตโนมัติ",  # เงินเดือน/Payroll
        "รับโอนเงินผ่าน QR",   # รับผ่าน QR
    }
    TX_TYPE_KEYWORDS_ALL = TX_TYPE_KEYWORDS_DEBIT | TX_TYPE_KEYWORDS_CREDIT

    # ---------- PUBLIC HELPER ----------
    def _extract_transactions_from_text(
        self,
        lines: List[str],
        page_num: int
    ) -> List[Transaction]:
        """
        Core entry for per-page parsing.
        ตอนนี้เราทำ parser แบบ state machine สำหรับรูปแบบสเตทเมนต์ของ KBank Mobile/K PLUS
        """

        logger.debug(f"[extract_page] page={page_num} lines={len(lines)}")

        txs = self._parse_kbank_page(lines, page_num)
        logger.debug(f"[extract_page] page={page_num} parsed_tx={len(txs)}")

        return txs

    # ---------- LOW LEVEL HELPERS ----------

    def _parse_money(self, money_str: str) -> float:
        """
        '12,278.00' -> 12278.00 (float)
        """
        return float(money_str.replace(",", ""))

    def _extract_payer_from_desc(self, desc_lines: List[str]) -> Optional[str]:
        """
        พยายามดึงผู้โอน / ผู้จ่ายฝั่งเครดิต จากบรรทัดที่ขึ้นต้นด้วย "จาก ..."

        ตัวอย่าง:
          "จาก SCB X5247 นาย กฤษฎา รักเพื่++"           → "SCB"
          "จาก SMART SCBT X1690 *BOOTS RETAIL (T) ++"  → "SMART SCBT"
          "จาก X5027 MR. JAYARAJ  NIRMA++"              → fallback
        """

        # รวม desc_lines ทั้งหมดเป็น block เดียว
        full_desc = " ".join(desc_lines)
        
        # ลองหา "จาก XXX" ก่อน
        if "จาก" not in full_desc:
            return None
        
        # Extract ส่วนหลัง "จาก"
        parts = full_desc.split("จาก", 1)
        if len(parts) < 2:
            return None
        
        after_jak = parts[1].strip()
        
        # ตัด ++ และอักขระพิเศษออก
        after_jak = re.sub(r"\+\+.*$", "", after_jak).strip()
        
        # ตัดที่ " X####" (account number)
        if " X" in after_jak:
            before_x = after_jak.split(" X")[0].strip()
            # ถ้ามีชื่อยาวพอ (>= 3 ตัวอักษร) ให้ใช้
            if len(before_x) >= 3:
                print(f"[PAYER_EXTRACT] full_desc='{full_desc[:60]}...' → payer='{before_x}'")
                return before_x
        
        # Fallback: ใช้คำแรกหลัง "จาก" (เช่น "SCB", "BBL", "KTB")
        first_word = after_jak.split()[0] if after_jak.split() else None
        if first_word:
            print(f"[PAYER_EXTRACT_FALLBACK] full_desc='{full_desc[:60]}...' → payer='{first_word}'")
        return first_word

    def _is_carry_forward_block(
        self,
        lines: List[str],
        i: int
    ) -> bool:
        """
        ตรวจ pattern 'ยอดยกมา' / 'ยอดยกไป' ที่ขึ้นต้นหน้าใหม่
        รูปแบบ:
            [DD-MM-YY]
            [BALANCE_AFTER]
            ยอดยกมา
        """

        if i + 2 >= len(lines):
            return False

        date_line = lines[i].strip()
        bal_line = lines[i + 1].strip()
        next_line = lines[i + 2].strip()

        if not self.DATE_RE.match(date_line):
            return False
        if not self.MONEY_RE.match(bal_line):
            return False
        if "ยอดยกมา" in next_line or "ยอดยกไป" in next_line:
            return True

        return False

    def _parse_kbank_page(
        self,
        lines: List[str],
        page_num: int
    ) -> List[Transaction]:
        """
        State machine สำหรับหน้าเดียวของ statement KBank
        """

        txs: List[Transaction] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i].strip()

            # หาบรรทัดที่เป็นวันที่ (เช่น "01-04-25")
            if not self.DATE_RE.match(line):
                i += 1
                continue

            start_idx = i  # เก็บ index บรรทัดแรกของ block (ใช้เป็น line_index ใน Transaction)
            date_str = line
            i += 1
            if i >= n:
                break

            # ----- เช็ค carry forward "ยอดยกมา" / "ยอดยกไป" -----
            # รูปแบบที่ขึ้นต้นหน้าใหม่:
            #   05-04-25
            #   5,575.20
            #   ยอดยกมา
            #   06-04-25
            if self._is_carry_forward_block(lines, start_idx):
                # skip block 'ยอดยกมา'
                i = start_idx + 3
                continue

            # ----- TIME -----
            time_str = None
            if i < n and self.TIME_RE.match(lines[i].strip()):
                time_str = lines[i].strip()
                i += 1

            if i >= n:
                break

            # ----- CHANNEL -----
            # channel อาจกินหลายบรรทัด (ATM ... / อีกบรรทัด / ฯลฯ)
            # เราจะสะสมไปเรื่อยจนกว่าจะเจอเลขจำนวนเงิน (ซึ่งคือ balance_after)
            channel_parts: List[str] = []
            while i < n and not self.MONEY_RE.match(lines[i].strip()):
                # ถ้าเจอวันที่ใหม่แบบสมบูรณ์ (ป้องกันฟอร์แมตพัง)
                if self.DATE_RE.match(lines[i].strip()):
                    # ฟอร์แมตไม่ครบ / ขาด balance -> เราจะถือว่า block นี้ invalid แล้ว break
                    logger.debug(
                        f"[page {page_num}] Encountered new date before balance; "
                        f"aborting current block at line {i}"
                    )
                    break

                channel_parts.append(lines[i].strip())
                i += 1

            if i >= n:
                break

            channel_str = " ".join(part for part in channel_parts if part)

            # ----- BALANCE AFTER -----
            balance_after = None
            if i < n and self.MONEY_RE.match(lines[i].strip()):
                balance_after = self._parse_money(lines[i].strip())
                i += 1
            else:
                # ถ้าดันไม่เจอ balance หลัง channel ก็ถือว่าบล็อกนี้แตกกลางทาง -> ข้าม
                logger.debug(
                    f"[page {page_num}] Missing balance_after after channel at line {i}; skip block"
                )
                continue

            # ----- DESCRIPTION LINES -----
            # เก็บบรรทัดรายละเอียดจนกว่าจะเจอ tx_type (เช่น 'ชำระเงิน', 'โอนเงิน', 'ถอนเงินสด', 'รับโอนเงิน')
            desc_lines: List[str] = []
            tx_type: Optional[str] = None

            while i < n:
                candidate = lines[i].strip()

                # ถ้าบรรทัดนี้เป็นประเภทธุรกรรม => จบ description
                if candidate in self.TX_TYPE_KEYWORDS_ALL:
                    tx_type = candidate
                    i += 1  # ขยับให้ไปชี้บรรทัดจำนวนเงิน
                    break

                # ถ้าเจอวันที่ใหม่ก่อนเจอ tx_type แปลว่า block นี้อาจไม่สมบูรณ์
                # --> เราจะหยุด block ตรงนี้เลย (tx_type = None)
                if self.DATE_RE.match(candidate):
                    logger.debug(
                        f"[page {page_num}] Hit next date before tx_type at line {i}; "
                        f"current block might be incomplete"
                    )
                    break

                desc_lines.append(candidate)
                i += 1

            description = " ".join(seg for seg in desc_lines if seg)

            # ----- AMOUNT (จำนวนเงินของรายการ) -----
            amount_val: Optional[float] = None
            if i < n and self.MONEY_RE.match(lines[i].strip()):
                amount_val = self._parse_money(lines[i].strip())
                i += 1
            else:
                # ถ้าไม่เจอจำนวนเงินบรรทัดสุดท้าย ก็ยังเก็บธุรกรรมได้
                # แต่ amount จะเป็น None
                pass

            # ----- DETERMINE CREDIT / DEBIT -----
            if tx_type in self.TX_TYPE_KEYWORDS_CREDIT:
                is_credit = True
            elif tx_type in self.TX_TYPE_KEYWORDS_DEBIT:
                is_credit = False
            else:
                # fallback heuristic ถ้า tx_type ไม่เจอ (ไม่ควรเกิดใน statement ปกติ)
                blob = f"{tx_type or ''} {description}"
                if "รับโอนเงิน" in blob:
                    is_credit = True
                else:
                    is_credit = False  # สมมติเป็นเดบิต

            # ----- PAYER -----
            payer = self._extract_payer_from_desc(desc_lines)

            # ----- สร้าง Transaction object -----
            tx_obj = Transaction(
                page=page_num,
                line_index=start_idx,
                date=date_str,
                time=time_str,
                channel=channel_str or None,
                description=description or None,
                amount=amount_val,
                is_credit=is_credit,
                payer=payer,
            )

            txs.append(tx_obj)

            # ลูปต่อไปหา date ถัดไป

        return txs
