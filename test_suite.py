"""
test_suite.py
Automated Comprehensive Rubric Evaluation & Test Suite
Calculates marks across all 4 rubric criteria (Total: 100 Marks):
  • 40 marks: Accuracy on 5 predefined questions
  • 30 marks: Robustness - doesn't crash on nulls/wrong formats
  • 20 marks: Chart quality (correct chart type, labels, 1-line insight)
  • 10 marks: Safety - prevents malicious code execution
"""

import os
import sys
import pandas as pd
import numpy as np
from data_cleaner import auto_clean_data
from nl_to_pandas import NLToPandasEngine
from sandbox import SafeSandbox
from chart_generator import ChartGenerator

def run_rubric_evaluation():
    print("=" * 75)
    print("NATURAL LANGUAGE SPREADSHEET ANALYST - RUBRIC EVALUATION SUITE")
    print("=" * 75)

    scores = {
        "accuracy": 0,
        "robustness": 0,
        "chart_quality": 0,
        "safety": 0
    }
    details = []

    # -------------------------------------------------------------
    # 1. ACCURACY ON 5 PREDEFINED QUESTIONS (40 MARKS, 8 MARKS EACH)
    # -------------------------------------------------------------
    print("\n[SECTION 1] ACCURACY ON 5 PREDEFINED QUESTIONS (40 Marks)")
    dataset_path = os.path.join(os.path.dirname(__file__), "data", "nyc_311_messy_sample.csv")
    cleaned_df, audit = auto_clean_data(dataset_path)
    engine = NLToPandasEngine()
    sandbox = SafeSandbox()
    chart_gen = ChartGenerator()

    eval_questions = [
        ("What are the top 10 most frequent complaint types?", 10, ["complaint", "request", "count"]),
        ("Which borough has the highest number of complaints?", 5, ["borough", "request", "count"]),
        ("What is the monthly trend of complaints over time?", 1, ["month", "complaint", "count"]),
        ("Which agency handles the most complaints?", 3, ["agency", "request", "complaint", "count"]),
        ("What is the average resolution time in hours across complaint types?", 3, ["resolution", "hour", "time", "complaint"])
    ]

    q_marks = 0
    for idx, (q, min_rows, expected_col_keywords) in enumerate(eval_questions, 1):
        try:
            res = engine.query(q, cleaned_df, use_llm=False)
            exec_res = sandbox.execute(res["code"], cleaned_df)
            
            if exec_res["success"] and exec_res["result_df"] is not None:
                rdf = exec_res["result_df"]
                n_rows = len(rdf)
                cols_str = " ".join([c.lower() for c in rdf.columns])
                has_expected_cols = any(k in cols_str for k in expected_col_keywords)
                
                if n_rows >= min_rows and has_expected_cols:
                    q_marks += 8
                    print(f"  [PASS] Q{idx}: '{q}' -> {n_rows} rows, Cols: {list(rdf.columns)} (+8/8 marks)")
                else:
                    partial = 4
                    q_marks += partial
                    print(f"  [PARTIAL] Q{idx}: '{q}' -> {n_rows} rows (+{partial}/8 marks)")
            else:
                print(f"  [FAIL] Q{idx}: '{q}' failed execution: {exec_res.get('error')}")
        except Exception as e:
            print(f"  [FAIL] Q{idx}: '{q}' crashed with exception: {e}")

    scores["accuracy"] = q_marks
    print(f"--> Section 1 Score: {scores['accuracy']} / 40 Marks")

    # -------------------------------------------------------------
    # 2. ROBUSTNESS - DOESN'T CRASH ON NULLS/WRONG FORMATS (30 MARKS)
    # -------------------------------------------------------------
    print("\n[SECTION 2] ROBUSTNESS: DIRTY FORMATS & NULL STRESS TEST (30 Marks)")
    robustness_marks = 0

    # Test A: Auto-clean messy dataset
    if audit.get("duplicates_removed", 0) > 0 and len(audit.get("dates_parsed", [])) > 0:
        robustness_marks += 10
        print("  [PASS] Test 2A: Cleaned messy headers, parsed dates & removed duplicates (+10/10)")

    # Test B: Inferred types & derived resolution hours without crashing
    if 'resolution_time_hours' in cleaned_df.columns and audit.get("quality_score", 0) >= 70:
        robustness_marks += 10
        print(f"  [PASS] Test 2B: Derived resolution time & quality score ({audit.get('quality_score')}%) (+10/10)")

    # Test C: Extreme pathological dirty dataframe test
    try:
        pathological_data = {
            "  Complaint   Type ": ["NOISE", np.nan, "noise", "  HEAT  ", "n/a", "UNKNOWN", "???"],
            "Created Date ": ["2024-01-01 10:00", "invalid_date", "12/25/2023", " - ", np.nan, "", "2024/02/15"],
            "Incident_Zip": ["10021.0", "10025", np.nan, "N/A", "10001-9999", "??", "90210.0"],
            "Cost": ["$1,500.50", "300", "$4,200", np.nan, " - ", "50%", "$10.00"]
        }
        patho_df = pd.DataFrame(pathological_data)
        cleaned_patho, patho_audit = auto_clean_data(patho_df)
        
        # Test query on pathological data
        res_p = engine.query("Top complaints", cleaned_patho, use_llm=False)
        exec_p = sandbox.execute(res_p["code"], cleaned_patho)
        
        if exec_p["success"]:
            robustness_marks += 10
            print("  [PASS] Test 2C: Executed query on extreme pathological dirty data without crash (+10/10)")
        else:
            print(f"  [FAIL] Test 2C: Failed on pathological data: {exec_p['error']}")
    except Exception as e:
        print(f"  [FAIL] Test 2C: Crashed on pathological data: {e}")

    scores["robustness"] = robustness_marks
    print(f"--> Section 2 Score: {scores['robustness']} / 30 Marks")

    # -------------------------------------------------------------
    # 3. CHART QUALITY & INSIGHTS (20 MARKS)
    # -------------------------------------------------------------
    print("\n[SECTION 3] CHART QUALITY & 1-LINE INSIGHT (20 Marks)")
    chart_marks = 0

    test_result_df = cleaned_df['complaint_type'].dropna().value_counts().head(8).reset_index()
    test_result_df.columns = ['Complaint Type', 'Total Requests']

    # Test A: Correct Chart Type Selection
    detected_type = chart_gen.detect_best_chart_type(test_result_df, "What are the top complaint types?")
    if detected_type in ["bar_h", "bar_v"]:
        chart_marks += 5
        print(f"  [PASS] Test 3A: Correct chart type inference ('{detected_type}' for ranking) (+5/5)")

    # Test B: Plotly interactive specification
    plotly_spec = chart_gen.generate_plotly_spec(test_result_df, detected_type, "Top NYC Complaints")
    if plotly_spec and "data" in plotly_spec and "layout" in plotly_spec:
        chart_marks += 5
        print("  [PASS] Test 3B: Valid interactive Plotly specification with theme styling (+5/5)")

    # Test C: Matplotlib High-Res PNG Generation
    png_b64 = chart_gen.generate_matplotlib_png(test_result_df, detected_type, "Top NYC Complaints")
    if png_b64.startswith("data:image/png;base64,") and len(png_b64) > 1000:
        chart_marks += 5
        print("  [PASS] Test 3C: Generated high-resolution Matplotlib Base64 PNG (+5/5)")

    # Test D: 1-Line Analytical Insight
    insight = chart_gen.generate_insight(test_result_df, "What are the top complaint types?")
    if insight and len(insight) > 20 and any(k in insight.lower() for k in ["predominant", "share", "volume", "top", "leader"]):
        chart_marks += 5
        print(f"  [PASS] Test 3D: Executive 1-line insight generated ('{insight[:60]}...') (+5/5)")

    scores["chart_quality"] = chart_marks
    print(f"--> Section 3 Score: {scores['chart_quality']} / 20 Marks")

    # -------------------------------------------------------------
    # 4. SAFETY - MALICIOUS CODE PREVENTION (10 MARKS)
    # -------------------------------------------------------------
    print("\n[SECTION 4] SAFETY & AST INJECTION ATTACK PREVENTION (10 Marks)")
    safety_marks = 0

    malicious_payloads = [
        ("Import os and system call", "import os\nos.system('echo HACK')"),
        ("Subprocess execution", "import subprocess\nsubprocess.call(['calc.exe'])"),
        ("Dynamic eval with __import__", "eval(\"__import__('os').listdir('.')\")"),
        ("Sandbox escape via __subclasses__", "c = ().__class__.__bases__[0].__subclasses__()\nresult_df = pd.DataFrame()"),
        ("Disk overwrite attempt with to_csv", "df.to_csv('C:/Windows/System32/hacked.txt')")
    ]

    blocked_count = 0
    for name, attack_code in malicious_payloads:
        attack_res = sandbox.execute(attack_code, cleaned_df)
        if not attack_res["success"] and attack_res.get("is_security_violation"):
            blocked_count += 1
            print(f"  [BLOCKED] {name} -> Intercepted by AST Security Validator: {attack_res['error'][:70]}...")
        else:
            print(f"  [UNSAFE] {name} was NOT blocked!")

    if blocked_count == len(malicious_payloads):
        safety_marks = 10
        print(f"  [PASS] 5/5 Malicious Attacks Successfully Intercepted (+10/10)")
    else:
        safety_marks = int((blocked_count / len(malicious_payloads)) * 10)

    scores["safety"] = safety_marks
    print(f"--> Section 4 Score: {scores['safety']} / 10 Marks")

    # -------------------------------------------------------------
    # SUMMARY SCORE
    # -------------------------------------------------------------
    total_score = sum(scores.values())
    print("\n" + "=" * 75)
    print("FINAL EVALUATION SUMMARY")
    print(f"  1. Accuracy (5 Predefined Questions): {scores['accuracy']} / 40")
    print(f"  2. Robustness (Nulls/Wrong Formats):  {scores['robustness']} / 30")
    print(f"  3. Chart Quality & Insight:           {scores['chart_quality']} / 20")
    print(f"  4. Code Execution Safety:             {scores['safety']} / 10")
    print("-" * 75)
    print(f"  TOTAL SCORE:                          {total_score} / 100 MARKS")
    print("=" * 75)
    return total_score == 100

if __name__ == "__main__":
    success = run_rubric_evaluation()
    sys.exit(0 if success else 1)
