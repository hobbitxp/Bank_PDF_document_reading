#!/usr/bin/env python3
"""
Bank Statement Processing Pipeline
Automates: PDF extraction → Data masking → Salary analysis

Usage:
    python process_statement.py "path/to/statement.pdf" [--password "1234"] [--employer "SG CAPITAL"] [--gross 84150]
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Execute a command and handle errors."""
    print(f"\n{'='*70}")
    print(f"▶ {description}")
    print(f"{'='*70}")
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    if result.returncode != 0:
        print(f"\n❌ Error: {description} failed with exit code {result.returncode}")
        return False
    
    print(f"✓ {description} completed successfully")
    return True


def extract_output_filename(pdf_filename):
    """Find the extracted JSON filename from PDF name."""
    pdf_name = Path(pdf_filename).stem  # Get filename without extension
    
    # Check for _extracted.json variant (what simple_pdf_to_json.py creates)
    json_dir = Path("data/json")
    
    # Try direct match first
    expected_names = [
        f"data/json/{pdf_name}_extracted.json",
        f"data/json/{pdf_name}.json"
    ]
    
    for expected_path in expected_names:
        if Path(expected_path).exists():
            return expected_path
    
    # Fallback: Find the most recent _extracted.json file in data/json/
    if json_dir.exists():
        extracted_files = sorted(
            json_dir.glob("*_extracted.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if extracted_files:
            return str(extracted_files[0])
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Process bank statement PDF through full analysis pipeline"
    )
    parser.add_argument(
        "input_file",
        help="Path to bank statement PDF file or extracted JSON file"
    )
    parser.add_argument("--password", default="", help="PDF password (if protected)")
    parser.add_argument("--employer", default="SG CAPITAL", help="Expected employer name for salary detection")
    parser.add_argument("--gross", type=float, help="Known gross salary amount for validation")
    parser.add_argument("--net", type=float, help="Known net salary amount")
    parser.add_argument("--pvd", type=float, help="PVD contribution amount")
    parser.add_argument("--eff_tax", type=float, help="Effective tax rate")
    parser.add_argument("--out-prefix", help="Output file prefix (default: auto-generated from PDF name)")
    
    args = parser.parse_args()
    
    # Verify input file exists
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    input_is_json = args.input_file.endswith(".json")
    pdf_file = args.input_file if not input_is_json else None
    
    print(f"\n{'='*70}")
    print(f"🚀 Bank Statement Processing Pipeline")
    print(f"{'='*70}")
    print(f"Input: {args.input_file}")
    print(f"Employer: {args.employer}")
    if args.gross:
        print(f"Gross salary (expected): {args.gross}")
    print()
    
    # Step 1: Extract PDF to JSON (skip if input is already JSON)
    if input_is_json:
        json_filename = args.input_file
        print(f"✓ Step 1/3: PDF Extraction - SKIPPED (input is already JSON)")
        print(f"   Using JSON: {json_filename}\n")
    else:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        
        extract_cmd = [
            sys.executable,
            str(script_dir / "simple_pdf_to_json.py"),
            args.input_file
        ]
        if args.password:
            extract_cmd.extend(["--password", args.password])
        
        if not run_command(extract_cmd, "Step 1/3: PDF Extraction"):
            sys.exit(1)
        
        # Find the extracted JSON file
        json_filename = extract_output_filename(args.input_file)
        if not json_filename:
            print("❌ Error: Could not find extracted JSON file")
            sys.exit(1)
        
        print(f"   Extracted JSON: {json_filename}")
    
    # Step 2: Mask sensitive data
    script_dir = Path(__file__).parent
    mask_cmd = [
        sys.executable,
        str(script_dir / "mask_data.py"),
        json_filename
    ]
    
    if not run_command(mask_cmd, "Step 2/3: Data Masking (PDPA Compliance)"):
        sys.exit(1)
    
    # Construct masked filename
    if "_extracted.json" in json_filename:
        # If input was _extracted.json, mask_data.py will create _masked.json by replacing _extracted
        masked_filename = json_filename.replace("_extracted.json", "_masked.json")
    elif json_filename.endswith(".json"):
        # If input is just .json, mask_data.py will append _masked
        masked_filename = json_filename.replace(".json", "_masked.json")
    else:
        masked_filename = f"{json_filename}_masked.json"
    
    print(f"   Masked JSON: {masked_filename}")
    
    # Step 3: Analyze salary
    script_dir = Path(__file__).parent
    analyze_cmd = [
        sys.executable,
        str(script_dir / "analyze_salary.py"),
        masked_filename,
        "--employer", args.employer
    ]
    
    if args.gross:
        analyze_cmd.extend(["--gross", str(args.gross)])
    if args.net:
        analyze_cmd.extend(["--net", str(args.net)])
    if args.pvd:
        analyze_cmd.extend(["--pvd", str(args.pvd)])
    if args.eff_tax:
        analyze_cmd.extend(["--eff_tax", str(args.eff_tax)])
    if args.out_prefix:
        analyze_cmd.extend(["--out-prefix", args.out_prefix])
    
    if not run_command(analyze_cmd, "Step 3/3: Salary Analysis & Detection"):
        sys.exit(1)
    
    # Extract base filename for summary
    base_name = Path(masked_filename).stem.replace("_masked", "")
    
    print(f"\n{'='*70}")
    print(f"✓ Processing Complete!")
    print(f"{'='*70}")
    print(f"Output files:")
    print(f"  • Extracted JSON:     {json_filename}")
    print(f"  • Masked JSON:        {masked_filename}")
    print(f"  • Mapping file:       {masked_filename.replace('.json', '_mapping.json')}")
    print(f"  • Salary analysis:    {base_name}_salary_detection.xlsx")
    print(f"  • Scored transactions: {base_name}_scored.csv")
    print(f"  • Summary JSON:       {base_name}_summary.json")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
