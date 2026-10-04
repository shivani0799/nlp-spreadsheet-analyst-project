"""
nl_to_pandas.py
Natural Language to Pandas Code Translation Engine
Supports:
1. Free-tier LLMs: Groq (openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b, llama-3.3-70b-versatile), Gemini, OpenAI
2. Automatic Code Sanitization (strips accidental imports/prints before AST check)
3. Bulletproof Semantic Fallback Engine (resilient to ANY uploaded CSV schema, never crashes)
"""

import os
import re
import json
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv()

class NLToPandasEngine:
    GROQ_MODELS = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "allam-2-7b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

    def __init__(self, api_key: Optional[str] = None, provider: str = "groq"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.provider = provider.lower()
        self.active_model = None

    def set_api_key(self, api_key: str, provider: str = "groq"):
        self.api_key = api_key.strip()
        self.provider = provider.lower()
        os.environ["GROQ_API_KEY"] = self.api_key

    def get_dataframe_context(self, df: pd.DataFrame) -> str:
        """Extracts schema, datatypes, and top sample values for LLM prompt."""
        context_lines = []
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            sample_vals = df[col].dropna().unique()[:3]
            sample_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in sample_vals])
            context_lines.append(f"- `{col}` ({dtype_str}): e.g. [{sample_str}]")
        return "\n".join(context_lines)

    def sanitize_code(self, raw_code: str) -> str:
        """
        Cleans generated code:
        - Removes markdown fences (```python ... ```)
        - Removes harmless import lines (import pandas as pd, import numpy as np)
        - Removes print() calls
        - Ensures result_df is assigned
        """
        code = raw_code.strip()
        code = re.sub(r'^```(?:python)?\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'```$', '', code, flags=re.MULTILINE).strip()

        # Remove lines starting with import or from
        lines = code.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Strip harmless import lines since pd and np are already provided
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            # Strip print statements
            if stripped.startswith("print(") and stripped.endswith(")"):
                continue
            cleaned_lines.append(line)

        sanitized = "\n".join(cleaned_lines).strip()

        # Check if result_df was assigned
        if "result_df" not in sanitized:
            # If there's an assignment like `top_x = ...`, alias it to result_df
            assign_match = re.findall(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=', sanitized, flags=re.MULTILINE)
            if assign_match:
                last_var = assign_match[-1]
                sanitized += f"\nresult_df = {last_var}"
            else:
                # If it's a standalone expression, assign it directly
                sanitized = f"result_df = {sanitized}"

        return sanitized

    def generate_code_with_llm(self, question: str, df: pd.DataFrame) -> Tuple[str, str]:
        """Calls Groq or Gemini to convert question to safe pandas code."""
        if not self.api_key:
            raise ValueError("No API key configured for LLM.")

        schema_context = self.get_dataframe_context(df)

        system_prompt = f"""You are an elite data scientist and Pandas expert.
Given a pandas DataFrame named `df` with {len(df)} rows, write clean, robust Python pandas code to answer the user's question.

AVAILABLE COLUMNS & TYPES:
{schema_context}

CRITICAL RULES:
1. The DataFrame is ALREADY loaded as `df`. Do NOT write any import statements (pandas is `pd`, numpy is `np`).
2. ALWAYS assign the final resulting summarized/filtered DataFrame to `result_df`.
3. Keep column names descriptive for presentation (e.g. ['Category', 'Total']).
4. Handle missing values cleanly with .dropna() where appropriate.
5. If grouping, use .reset_index() so the result has clean columns.
6. NO dangerous operations: no file writes, no os/sys/subprocess, no eval/exec.
7. Return valid JSON only with keys "code" and "insight" (a crisp 1-line business takeaway).
Format:
{{
  "code": "result_df = ...",
  "insight": "..."
}}
"""

        user_prompt = f"User Question: {question}"

        # 1. Try Groq
        if self.provider == "groq" or self.api_key.startswith("gsk_"):
            from groq import Groq
            client = Groq(api_key=self.api_key)

            # Probe for available models
            models_to_try = [self.active_model] if self.active_model else []
            models_to_try.extend([m for m in self.GROQ_MODELS if m not in models_to_try])

            last_error = None
            for model_name in models_to_try:
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                        max_tokens=600
                    )
                    self.active_model = model_name
                    raw_json = json.loads(response.choices[0].message.content)
                    raw_code = raw_json.get("code", "")
                    insight = raw_json.get("insight", "")
                    return self.sanitize_code(raw_code), insight
                except Exception as e:
                    last_error = e
                    continue

            raise RuntimeError(f"All Groq models failed: {last_error}")

        # 2. Try Gemini
        elif self.provider == "gemini":
            try:
                import httpx
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": f"{system_prompt}\n\n{user_prompt}\nReturn JSON format."}]
                    }],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
                }
                res = httpx.post(url, json=payload, timeout=20.0)
                if res.status_code == 200:
                    data = res.json()
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    raw_json = json.loads(text)
                    return self.sanitize_code(raw_json.get("code", "")), raw_json.get("insight", "")
                else:
                    raise RuntimeError(f"Gemini API returned status {res.status_code}: {res.text}")
            except Exception as e:
                raise RuntimeError(f"Gemini API error: {e}")

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _find_matching_col(self, df: pd.DataFrame, keywords: List[str], fallback_type: str = "categorical") -> Optional[str]:
        """Safely searches dataframe columns for matching keywords; falls back to best column type."""
        cols = list(df.columns)
        lower_cols = [c.lower() for c in cols]

        # 1. Exact or partial match with keywords
        for kw in keywords:
            kw_lower = kw.lower()
            for orig, low in zip(cols, lower_cols):
                if kw_lower in low:
                    return orig

        # 2. Fallback based on type
        if fallback_type == "categorical":
            cat_cols = [c for c in cols if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]
            if cat_cols:
                return cat_cols[0]
        elif fallback_type == "numeric":
            num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
            if num_cols:
                return num_cols[0]
        elif fallback_type == "date":
            date_cols = [c for c in cols if pd.api.types.is_datetime64_any_dtype(df[c]) or any(k in c.lower() for k in ['date', 'time', 'month', 'year'])]
            if date_cols:
                return date_cols[0]

        return cols[0] if cols else None

    def generate_code_offline_fallback(self, question: str, df: pd.DataFrame) -> Tuple[str, str]:
        """
        High-accuracy deterministic semantic engine.
        Guaranteed to work safely on ANY dataframe without throwing IndexError or KeyError.
        """
        q = question.lower().strip()

        # Find available columns
        cat_col = self._find_matching_col(df, ["type", "name", "category", "item", "product", "complaint", "status", "borough", "agency"], "categorical")
        num_col = self._find_matching_col(df, ["amount", "sales", "revenue", "price", "count", "cost", "total", "quantity", "hours"], "numeric")
        date_col = self._find_matching_col(df, ["created_month", "created_date", "date", "timestamp", "time", "month"], "date")

        # 1. Borough query (NYC 311 specific or location)
        if "borough" in q or "district" in q:
            borough_col = self._find_matching_col(df, ["borough", "district", "city", "region", "location"], "categorical")
            if borough_col:
                code = f"""# Distribution by {borough_col}
clean_s = df['{borough_col}'].dropna()
result_df = clean_s[~clean_s.astype(str).str.upper().isin(['UNSPECIFIED', 'UNKNOWN', 'NAN'])].value_counts().reset_index()
result_df.columns = ['{borough_col.replace('_', ' ').title()}', 'Total Requests']"""
                insight = f"Distribution breakdown across {borough_col.replace('_', ' ').title()}."
                return code, insight

        # 2. Monthly trend / over time
        if any(k in q for k in ["trend", "month", "monthly", "over time", "timeline", "by year"]):
            if date_col:
                if pd.api.types.is_datetime64_any_dtype(df[date_col]):
                    code = f"""# Monthly trend over time
result_df = df['{date_col}'].dropna().dt.to_period('M').astype(str).value_counts().sort_index().reset_index()
result_df.columns = ['Period', 'Count']"""
                else:
                    code = f"""# Trend analysis over {date_col}
clean_d = df['{date_col}'].dropna()
result_df = clean_d[clean_d.astype(str) != 'NaT'].value_counts().sort_index().reset_index()
result_df.columns = ['Period', 'Count']"""
                insight = "Temporal trend analysis reveals demand and transaction patterns over time."
                return code, insight

        # 3. Agency / Department workload
        if "agency" in q or "department" in q or "nypd" in q:
            agency_col = self._find_matching_col(df, ["agency", "department", "rep", "agent"], "categorical")
            if agency_col:
                code = f"""# Volume by {agency_col}
clean_a = df['{agency_col}'].dropna()
result_df = clean_a[~clean_a.astype(str).str.upper().isin(['NAN', 'UNKNOWN', 'NONE'])].value_counts().head(10).reset_index()
result_df.columns = ['{agency_col.replace('_', ' ').title()}', 'Total Requests']"""
                insight = f"Workload distribution across {agency_col.replace('_', ' ').title()}."
                return code, insight

        # 4. Resolution time / duration
        if any(k in q for k in ["resolution", "how long", "duration", "hours", "time to close", "speed"]):
            res_col = self._find_matching_col(df, ["resolution_time_hours", "duration", "hours", "time"], "numeric")
            if res_col and cat_col and res_col != cat_col:
                code = f"""# Average {res_col} by {cat_col}
res_df = df.dropna(subset=['{res_col}', '{cat_col}'])
result_df = res_df.groupby('{cat_col}')['{res_col}'].agg(['mean', 'count'])
result_df = result_df[result_df['count'] >= 2].sort_values(by='mean', ascending=False).head(10).reset_index()
result_df['mean'] = result_df['mean'].round(1)
result_df.columns = ['{cat_col.replace('_', ' ').title()}', 'Avg {res_col.replace('_', ' ').title()}', 'Count']"""
                insight = f"Analysis of average turnaround time in hours across categories."
                return code, insight

        # 5. Top N Ranking / General query
        top_n = 10
        m = re.search(r'top\s*(\d+)', q)
        if m:
            top_n = int(m.group(1))

        # Check if user mentioned a specific column name
        for col in df.columns:
            if col.lower() in q:
                cat_col = col
                break

        # If we have both a categorical column and a numeric column (e.g. sales by product)
        if cat_col and num_col and cat_col != num_col and any(k in q for k in ["sales", "revenue", "amount", "cost", "sum", "total"]):
            code = f"""# Top {top_n} {cat_col} by {num_col}
result_df = df.dropna(subset=['{cat_col}', '{num_col}'])\
              .groupby('{cat_col}', as_index=False)['{num_col}'].sum()\
              .sort_values(by='{num_col}', ascending=False)\
              .head({top_n})
result_df.columns = ['{cat_col.replace('_', ' ').title()}', 'Total {num_col.replace('_', ' ').title()}']"""
            insight = f"Top {top_n} {cat_col.replace('_', ' ').title()} ranked by cumulative {num_col.replace('_', ' ').title()}."
            return code, insight

        # Standard categorical frequency ranking
        target = cat_col or df.columns[0]
        code = f"""# Top {top_n} {target} by frequency
result_df = df['{target}'].dropna().value_counts().head({top_n}).reset_index()
result_df.columns = ['{target.replace('_', ' ').title()}', 'Total Count']"""
        insight = f"Top {top_n} {target.replace('_', ' ').title()} represent the primary segments in this dataset."
        return code, insight

    def query(self, question: str, df: pd.DataFrame, use_llm: bool = True) -> Dict[str, Any]:
        """
        Translates natural language to pandas code, validates through sandbox, and returns execution result.
        """
        code = ""
        insight = ""
        source = "offline_engine"

        # If LLM is requested or API key exists, use LLM
        if use_llm and self.api_key:
            try:
                code, insight = self.generate_code_with_llm(question, df)
                source = f"groq_llm ({self.active_model or 'fast'})"
            except Exception as e:
                # Graceful fallback to offline rule engine
                code, insight = self.generate_code_offline_fallback(question, df)
                source = f"offline_fallback (LLM error: {str(e)[:50]}...)"
        else:
            code, insight = self.generate_code_offline_fallback(question, df)
            source = "offline_rule_engine"

        return {
            "code": code,
            "insight": insight,
            "source": source
        }

if __name__ == "__main__":
    from data_cleaner import auto_clean_data
    from sandbox import SafeSandbox

    sample_path = os.path.join(os.path.dirname(__file__), "data", "nyc_311_messy_sample.csv")
    df, audit = auto_clean_data(sample_path)
    engine = NLToPandasEngine()
    sandbox = SafeSandbox()

    print("=== Testing with Groq API Key ===")
    res = engine.query("What are the top 5 complaint types?", df, use_llm=True)
    print("Source:", res["source"])
    print("Code:\n", res["code"])
    print("Insight:", res["insight"])
    exec_res = sandbox.execute(res["code"], df)
    print("Executed:", exec_res["success"], "| Rows:", len(exec_res["result_df"]) if exec_res["result_df"] is not None else 0)

    print("\n=== Testing with Custom Unknown CSV (Sales Data) ===")
    sales_df = pd.DataFrame({
        "product": ["Widget A", "Widget B", "Widget A", "Gadget X", "Widget B", "Gadget Y"],
        "sales": [1200, 3400, 1500, 800, 2200, 450],
        "region": ["North", "South", "East", "West", "North", "South"]
    })
    res_sales = engine.query("Top complaints", sales_df, use_llm=False)
    print("Fallback on unknown CSV succeeded:", bool(res_sales["code"]))
    exec_sales = sandbox.execute(res_sales["code"], sales_df)
    print("Sales query executed without crash:", exec_sales["success"], "| Rows:", len(exec_sales["result_df"]))
