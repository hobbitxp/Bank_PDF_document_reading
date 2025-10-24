#!/usr/bin/env python3
"""
Detect salary transactions from bank statement JSON.
Supports Thai payroll with progressive tax calculation.
"""

import json
import re
from collections import defaultdict, Counter
from statistics import mean, pstdev
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import pandas as pd

KEYWORD_PATTERNS = [
    r"เงินเดือน/อื่นๆ", r"\(BSD02\)", r"Payroll", r"เงินเดือน"
]
EXCLUDE_PATTERNS = [
    r"\(MOR(?:ISW|WSW)\)", r"\(NMIDSW\)", r"ATSWCR", r"SDCH", r"เช็ค", r"e ?wallet", r"EWALLETID"
]
CREDIT_HINTS = ["เงินโอนเข้า", "เงินเดือน/อื่นๆ", "(BSD02)", "BSD02"]

@dataclass
class Tx:
    page: int
    line_index: int
    time: Optional[str]
    amount: float
    desc_raw: str
    is_credit: bool
    channel: Optional[str]
    payer: Optional[str]
    score: float = 0.0
    cluster_id: Optional[int] = None

def _find_amount(s: str) -> Optional[float]:
    """Extract amount from text (handles Thai number formatting)."""
    m = re.search(r"(\d{1,3}(?:,\d{3})*\.\d{2})", s)
    if not m: 
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except:
        return None

def extract_transactions(statement_json: Dict[str, Any], 
                        employer_aliases: Optional[List[str]] = None) -> List[Tx]:
    """Extract all transactions from statement JSON."""
    txs: List[Tx] = []
    for page_obj in statement_json.get("pages", []):
        page_no = page_obj.get("page_number", 0)
        text = page_obj.get("text", "") or ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            amt = _find_amount(line)
            if amt is None:
                continue
            
            # window of context around line to catch description, channel, time
            start = max(0, i-2)
            end = min(len(lines), i+3)
            window_lines = lines[start:end]
            window = " ".join(window_lines)

            # direction heuristic
            is_credit = any(h in window for h in CREDIT_HINTS)
            if not is_credit:
                if "รายการฝาก" in "\n".join(lines[:max(40, i+1)]) or "เงินโอนเข้า" in window:
                    is_credit = True

            # time
            m_time = re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", window)
            time_str = m_time.group(0) if m_time else None

            # channel code (e.g., BSD02, IORSDT, MORISW, etc.)
            m_channel = re.search(r"\(([A-Z0-9]{4,6})\)", window)
            channel = m_channel.group(1) if m_channel else None

            # payer detection (simple alias match)
            payer = None
            if employer_aliases:
                up = window.upper()
                for alias in employer_aliases:
                    if alias.upper() in up:
                        payer = alias
                        break

            txs.append(Tx(
                page=page_no,
                line_index=i,
                time=time_str,
                amount=amt,
                desc_raw=window,
                is_credit=is_credit,
                channel=channel,
                payer=payer
            ))
    return txs

def is_excluded(tx: Tx) -> bool:
    """Check if transaction should be excluded."""
    return re.search("|".join(EXCLUDE_PATTERNS), tx.desc_raw, flags=re.I) is not None

def has_keyword(tx: Tx) -> bool:
    """Check if transaction has salary keywords."""
    return re.search("|".join(KEYWORD_PATTERNS), tx.desc_raw) is not None

def time_score(tx: Tx) -> int:
    """Score based on time (early morning = likely payroll)."""
    if not tx.time:
        return 0
    try:
        hh = int(tx.time.split(":")[0])
    except:
        return 0
    # payroll window (early morning)
    return 1 if 1 <= hh <= 6 else 0

def cluster_amounts(candidates: List[Tx], pct: float = 0.03) -> List[List[Tx]]:
    """Group similar amounts into clusters."""
    clusters: List[List[Tx]] = []
    for tx in sorted(candidates, key=lambda x: x.amount):
        placed = False
        for c in clusters:
            center = mean([t.amount for t in c])
            if abs(tx.amount - center) <= pct * center:
                c.append(tx)
                placed = True
                break
        if not placed:
            clusters.append([tx])
    return clusters

def thai_monthly_net_from_gross(
    gross: float,
    pvd_rate: Optional[float] = None,
    extra_deductions_yearly: float = 0.0
) -> Tuple[float, float, float]:
    """
    Thai PAYE model with progressive tax brackets.
    Returns (net_monthly, tax_monthly, sso_monthly).
    
    - SSO: 5% capped 750/month
    - Employment expense: 50% of annual income, capped 100,000
    - Personal allowance: 60,000/year
    - Progressive brackets (annual):
      0-150k: 0%, 150-300k: 5%, 300-500k: 10%, 500-750k: 15%,
      750k-1M: 20%, 1M-2M: 25%, 2M-5M: 30%, >5M: 35%
    """
    sso_month = min(gross * 0.05, 750.0)
    pvd_month = gross * (pvd_rate if pvd_rate else 0.0)

    annual_income = gross * 12.0
    annual_sso = min(9000.0, sso_month * 12.0)
    annual_pvd = pvd_month * 12.0

    employment_expense = min(annual_income * 0.5, 100000.0)
    personal_allowance = 60000.0

    taxable = annual_income - employment_expense - personal_allowance - annual_sso - annual_pvd - extra_deductions_yearly
    if taxable < 0:
        taxable = 0.0

    brackets = [
        (150000, 0.00),
        (300000, 0.05),
        (500000, 0.10),
        (750000, 0.15),
        (1000000, 0.20),
        (2000000, 0.25),
        (5000000, 0.30),
        (float("inf"), 0.35),
    ]
    last = 0.0
    tax_year = 0.0
    for limit, rate in brackets:
        if taxable > last:
            portion = min(taxable, limit) - last
            if portion > 0:
                tax_year += portion * rate
            last = limit
        else:
            break

    tax_month = tax_year / 12.0
    net_month = gross - sso_month - pvd_month - tax_month
    return net_month, tax_month, sso_month

def compute_net_range_from_gross(gross: float, pvd_rate: Optional[float] = None, 
                                 eff_tax_rate: Optional[float] = None) -> Tuple[float, float]:
    """Compute net salary range using Thai PAYE model (±5%)."""
    net, _, _ = thai_monthly_net_from_gross(gross, pvd_rate=pvd_rate)
    return net * 0.95, net * 1.05

def score_candidates(candidates: List[Tx],
                     employer_aliases: Optional[List[str]] = None,
                     gross: Optional[float] = None,
                     net: Optional[float] = None,
                     pvd_rate: Optional[float] = None,
                     eff_tax_rate: Optional[float] = None) -> Tuple[List[Tx], List[List[Tx]]]:
    """Score each candidate transaction."""
    amounts = [c.amount for c in candidates] or [0.0]
    avg = mean(amounts) if amounts else 0.0
    sd = pstdev(amounts) if len(amounts) > 1 else 0.0

    # amount clusters
    clusters = cluster_amounts(candidates)

    # precompute target range if user provided gross/net
    net_low = net_high = None
    if gross is not None:
        net_low, net_high = compute_net_range_from_gross(gross, pvd_rate, eff_tax_rate)
    elif net is not None:
        net_low, net_high = net*0.95, net*1.05

    def in_target_range(a: float) -> bool:
        if net_low is None or net_high is None:
            return False
        return net_low <= a <= net_high

    # weights
    w_keyword = 5
    w_payer = 3
    w_time = 2
    w_amount_cluster = 3
    w_monthly_periodicity = 3
    w_close_to_user_gross_net = 2
    w_not_wallet_or_cash = 2
    w_not_bonus = 2

    # compute cluster ids
    id_map = {}
    for idx, cl in enumerate(clusters):
        for tx in cl:
            id_map[id(tx)] = idx

    for tx in candidates:
        score = 0.0
        if has_keyword(tx):
            score += w_keyword
        if employer_aliases and tx.payer:
            score += w_payer
        score += w_time * time_score(tx)
        if not is_excluded(tx):
            score += w_not_wallet_or_cash

        # amount cluster + periodicity proxy
        cid = id_map.get(id(tx))
        if cid is not None:
            cl_size = len(clusters[cid])
            if cl_size >= 2:
                score += w_amount_cluster
            if cl_size >= 3:
                score += w_monthly_periodicity

        if in_target_range(tx.amount):
            score += w_close_to_user_gross_net

        if sd and abs(tx.amount - avg) > 2.5 * sd:
            score -= w_not_bonus

        tx.score = score
        tx.cluster_id = cid

    return candidates, clusters

def pick_salary(scored: List[Tx]) -> Dict[str, Any]:
    """Pick best salary candidate group."""
    if not scored:
        return {"salary_candidates": [], "best_guess_group": [], "best_guess_amount": None}

    by_cluster: Dict[int, List[Tx]] = defaultdict(list)
    for tx in scored:
        cid = tx.cluster_id if tx.cluster_id is not None else -1
        by_cluster[cid].append(tx)

    # choose cluster by highest (avg score + 0.2*size)
    best_cid, best_metric = None, float("-inf")
    for cid, items in by_cluster.items():
        metric = (sum(t.score for t in items)/len(items)) + 0.2*len(items)
        if metric > best_metric:
            best_metric = metric
            best_cid = cid

    best_group = sorted(by_cluster[best_cid], key=lambda x: -x.score) if best_cid is not None else []
    best_amount = round(sum(t.amount for t in best_group)/len(best_group), 2) if best_group else None

    top10 = sorted(scored, key=lambda x: -x.score)[:10]
    return {
        "salary_candidates": [asdict_tx(t) for t in top10],
        "best_guess_group": [asdict_tx(t) for t in best_group],
        "best_guess_amount": best_amount
    }

def asdict_tx(t: Tx) -> Dict[str, Any]:
    """Convert transaction to dict."""
    return {
        "page": t.page,
        "time": t.time,
        "amount": t.amount,
        "is_credit": t.is_credit,
        "channel": t.channel,
        "payer": t.payer,
        "score": t.score,
        "cluster_id": t.cluster_id,
        "desc_raw": t.desc_raw[:500]
    }

def run(statement_path: str,
        employer_aliases: Optional[List[str]] = None,
        gross: Optional[float] = None,
        net: Optional[float] = None,
        pvd_rate: Optional[float] = None,
        eff_tax_rate: Optional[float] = None,
        export_prefix: Optional[str] = None) -> Dict[str, Any]:
    """
    Run salary detection on statement JSON.
    
    Args:
        statement_path: Path to extracted statement JSON
        employer_aliases: List of employer names to match
        gross: Known gross salary (for validation)
        net: Known net salary (for validation)
        pvd_rate: PVD contribution rate (default 0)
        eff_tax_rate: Override effective tax rate
        export_prefix: Output file prefix (default = statement_path without extension)
    
    Returns:
        Dict with summary, result, and export file paths
    """
    with open(statement_path, "r", encoding="utf-8") as f:
        statement_json = json.load(f)

    txs = extract_transactions(statement_json, employer_aliases=employer_aliases)

    # Keep only credits and non-excluded
    credit_candidates = [t for t in txs if t.is_credit and not is_excluded(t)]
    scored, clusters = score_candidates(
        credit_candidates,
        employer_aliases=employer_aliases,
        gross=gross, net=net,
        pvd_rate=pvd_rate,
        eff_tax_rate=eff_tax_rate
    )
    result = pick_salary(scored)

    # Exports
    prefix = export_prefix or str(Path(statement_path).with_suffix(""))
    df_all = pd.DataFrame([asdict_tx(t) for t in scored]).sort_values("score", ascending=False)
    df_best = pd.DataFrame(result["best_guess_group"]) if result["best_guess_group"] else pd.DataFrame()
    df_top10 = pd.DataFrame(result["salary_candidates"]) if result["salary_candidates"] else pd.DataFrame()

    df_all.to_csv(prefix + "_scored.csv", index=False)
    with pd.ExcelWriter(prefix + "_salary_detection.xlsx") as writer:
        df_all.to_excel(writer, sheet_name="all_scored", index=False)
        if not df_best.empty:
            df_best.to_excel(writer, sheet_name="best_group", index=False)
        if not df_top10.empty:
            df_top10.to_excel(writer, sheet_name="top10", index=False)

    summary = {
        "best_guess_amount": result["best_guess_amount"],
        "scored_count": len(scored),
        "clusters": [len(c) for c in clusters]
    }
    with open(prefix + "_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        "summary": summary,
        "result": result,
        "exports": {
            "csv": prefix + "_scored.csv",
            "xlsx": prefix + "_salary_detection.xlsx",
            "json": prefix + "_summary.json"
        }
    }

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Detect salary transactions from statement JSON.")
    ap.add_argument("statement", help="Path to statement JSON file")
    ap.add_argument("--employer", nargs="*", default=[], help="Employer aliases")
    ap.add_argument("--gross", type=float, default=None, help="Known gross salary")
    ap.add_argument("--net", type=float, default=None, help="Known net salary")
    ap.add_argument("--pvd", type=float, default=None, help="PVD contribution rate (e.g., 0.05)")
    ap.add_argument("--eff_tax", type=float, default=None, help="Override effective tax rate")
    ap.add_argument("--out_prefix", type=str, default=None, help="Export file prefix")
    args = ap.parse_args()

    out = run(
        args.statement,
        employer_aliases=args.employer or None,
        gross=args.gross,
        net=args.net,
        pvd_rate=args.pvd,
        eff_tax_rate=args.eff_tax,
        export_prefix=args.out_prefix
    )
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2))
