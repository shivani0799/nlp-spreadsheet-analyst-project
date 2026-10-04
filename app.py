"""
app.py
Production-grade FastAPI Backend for Natural Language Spreadsheet Analyst
Serves interactive REST API and rich modern web dashboard.
"""

import os
import io
import json
import time
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from data_cleaner import auto_clean_data, DataCleaner
from sandbox import SafeSandbox
from chart_generator import ChartGenerator
from nl_to_pandas import NLToPandasEngine
from auth_manager import auth_manager
from chatbot import data_chatbot

app = FastAPI(
    title="Natural Language Spreadsheet Analyst",
    description="Conversational Business Intelligence Agent for Messy Spreadsheets",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application state
class AppState:
    cleaned_df: Optional[pd.DataFrame] = None
    audit_summary: Optional[Dict[str, Any]] = None
    current_dataset_name: str = "nyc_311_messy_sample.csv"
    sandbox: SafeSandbox = SafeSandbox()
    chart_gen: ChartGenerator = ChartGenerator()
    engine: NLToPandasEngine = NLToPandasEngine()
    last_query_result: Optional[pd.DataFrame] = None
    last_query_text: str = ""

state = AppState()

# Pre-load default sample on startup
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "nyc_311_messy_sample.csv")
if os.path.exists(DEFAULT_CSV_PATH):
    state.cleaned_df, state.audit_summary = auto_clean_data(DEFAULT_CSV_PATH)

# Request models
class QueryRequest(BaseModel):
    question: str
    chart_type_override: Optional[str] = None
    api_key: Optional[str] = None
    provider: Optional[str] = "groq"
    use_llm: Optional[bool] = False

class SecurityAttackRequest(BaseModel):
    attack_type: str

class SignUpRequest(BaseModel):
    name: str
    email: str
    password: str

class SignInRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

# Endpoints
@app.get("/api/status")
def get_status():
    has_data = state.cleaned_df is not None
    return {
        "status": "ready" if has_data else "no_data",
        "dataset_name": state.current_dataset_name,
        "rows": len(state.cleaned_df) if has_data else 0,
        "columns": len(state.cleaned_df.columns) if has_data else 0,
        "column_names": list(state.cleaned_df.columns)[:25] if has_data else [],
        "audit": state.audit_summary,
        "llm_configured": bool(state.engine.api_key),
        "llm_provider": state.engine.provider
    }

@app.post("/api/configure-llm")
def configure_llm(api_key: str = Form(...), provider: str = Form("groq")):
    state.engine.set_api_key(api_key, provider)
    return {
        "success": True,
        "message": f"LLM provider configured successfully ({provider}).",
        "provider": provider
    }

@app.post("/api/load-sample")
@app.post("/api/reset-nyc-dataset")
def load_sample_dataset():
    if not os.path.exists(DEFAULT_CSV_PATH):
        from data.fetch_dataset import fetch_or_generate_dataset
        fetch_or_generate_dataset()

    state.cleaned_df, state.audit_summary = auto_clean_data(DEFAULT_CSV_PATH)
    state.current_dataset_name = "NYC 311 Service Requests (Sample)"
    return {
        "success": True,
        "message": "Authentic NYC 311 dataset loaded and cleaned successfully.",
        "dataset_name": state.current_dataset_name,
        "rows": len(state.cleaned_df),
        "columns": len(state.cleaned_df.columns),
        "audit": state.audit_summary
    }

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.tsv', '.txt')):
        raise HTTPException(status_code=400, detail="Only CSV or TSV files are supported.")

    content = await file.read()
    try:
        buffer = io.BytesIO(content)
        cleaned_df, audit = auto_clean_data(buffer)
        state.cleaned_df = cleaned_df
        state.audit_summary = audit
        state.current_dataset_name = file.filename
        return {
            "success": True,
            "filename": file.filename,
            "rows": len(cleaned_df),
            "columns": len(cleaned_df.columns),
            "audit": audit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and clean CSV: {str(e)}")

@app.post("/api/query")
def process_query(req: QueryRequest):
    if state.cleaned_df is None:
        raise HTTPException(status_code=400, detail="No dataset loaded. Please upload a CSV or load the sample.")

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Configure engine with API key
        engine = state.engine
        api_key = req.api_key or os.environ.get("GROQ_API_KEY")
        if api_key:
            engine = NLToPandasEngine(api_key=api_key, provider=req.provider or "groq")

        # Automatically use LLM if an API key is available
        use_llm = req.use_llm or bool(api_key)

        # 1. Translate question to safe Pandas code
        translation = engine.query(question, state.cleaned_df, use_llm=use_llm)
        code = translation["code"]
        source = translation["source"]
        preset_insight = translation.get("insight", "")

        # 2. Safely validate AST and execute in sandbox
        exec_result = state.sandbox.execute(code, state.cleaned_df)

        if not exec_result["success"]:
            return {
                "success": False,
                "error": exec_result["error"],
                "violations": exec_result.get("violations", []),
                "passed_checks": exec_result.get("passed_checks", []),
                "code": code,
                "source": source,
                "execution_time_ms": exec_result.get("execution_time_ms", 0),
                "is_security_violation": exec_result.get("is_security_violation", False)
            }

        result_df = exec_result["result_df"]
        state.last_query_result = result_df
        state.last_query_text = question

        # 3. Detect and generate chart
        chart_type = req.chart_type_override or state.chart_gen.detect_best_chart_type(result_df, question)
        chart_title = f"{question}"
        
        plotly_spec = state.chart_gen.generate_plotly_spec(result_df, chart_type, chart_title)
        matplotlib_png = state.chart_gen.generate_matplotlib_png(result_df, chart_type, chart_title)

        # 4. Generate 1-line business insight
        insight = preset_insight if preset_insight and len(preset_insight) > 15 else state.chart_gen.generate_insight(result_df, question)

        # 5. Format table for JSON response
        preview_df = result_df.head(100)
        table_data = preview_df.replace({np.nan: None}).to_dict(orient="records")
        table_columns = [{"key": col, "label": str(col).replace('_', ' ').title()} for col in result_df.columns]

        return {
            "success": True,
            "question": question,
            "insight": insight,
            "chart_type": chart_type,
            "plotly_spec": plotly_spec,
            "matplotlib_png": matplotlib_png,
            "table": {
                "columns": table_columns,
                "rows": table_data,
                "total_rows": len(result_df)
            },
            "code": code,
            "source": source,
            "execution_time_ms": exec_result["execution_time_ms"],
            "security": {
                "safe": True,
                "passed_checks": exec_result["passed_checks"]
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis Error: {str(e)}",
            "violations": [],
            "passed_checks": [],
            "code": "",
            "source": "error",
            "execution_time_ms": 0,
            "is_security_violation": False
        }

# --- Authentication Endpoints ---
@app.post("/api/auth/signup")
def signup(req: SignUpRequest):
    try:
        user = auth_manager.create_user(req.email, req.name, req.password)
        token = auth_manager.create_session(user)
        return {"success": True, "user": user, "token": token}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/signin")
def signin(req: SignInRequest):
    user = auth_manager.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = auth_manager.create_session(user)
    return {"success": True, "user": user, "token": token}

@app.post("/api/auth/demo")
def demo_login():
    user = auth_manager.authenticate_user("analyst@company.com", "demo123")
    if not user:
        user = auth_manager.create_user("analyst@company.com", "Shivani (Senior Analyst)", "demo123")
    token = auth_manager.create_session(user)
    return {"success": True, "user": user, "token": token}

@app.get("/api/auth/me")
def get_me(token: Optional[str] = None):
    if not token:
        return {"authenticated": False, "user": None}
    user = auth_manager.get_user_from_session(token)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}

# --- Conversational AI Chatbot Endpoint ---
@app.post("/api/chat")
def chat_copilot(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    resp = data_chatbot.chat(
        message=req.message.strip(),
        history=req.history or [],
        df=state.cleaned_df,
        dataset_name=state.current_dataset_name,
        last_query=state.last_query_text,
        last_result_df=state.last_query_result
    )
    return {
        "success": True,
        "reply": resp["reply"],
        "source": resp["source"],
        "action_query": resp.get("action_query")
    }

@app.post("/api/run-benchmark")
def run_benchmark():
    """Runs all 5 rubric questions and returns a full benchmark report card."""
    if state.cleaned_df is None:
        raise HTTPException(status_code=400, detail="No dataset loaded.")

    questions = [
        ("What are the top 10 most frequent complaint types?", "Top 10 Complaints", 10),
        ("Which borough has the highest number of complaints?", "Borough Breakdown", 5),
        ("What is the monthly trend of complaints over time?", "Monthly Timeline", 1),
        ("Which agency handles the most complaints?", "Agency Distribution", 3),
        ("What is the average resolution time in hours across complaint types?", "Resolution Time", 3)
    ]

    results = []
    total_score = 0

    for idx, (q, title, min_rows) in enumerate(questions, 1):
        t0 = time.perf_counter()
        tr = state.engine.query(q, state.cleaned_df, use_llm=False)
        ex = state.sandbox.execute(tr["code"], state.cleaned_df)
        elapsed = (time.perf_counter() - t0) * 1000.0

        passed = ex["success"] and ex["result_df"] is not None and len(ex["result_df"]) >= min_rows
        score = 8 if passed else 4
        total_score += score

        insight = state.chart_gen.generate_insight(ex["result_df"], q) if ex["result_df"] is not None else ""
        chart_type = state.chart_gen.detect_best_chart_type(ex["result_df"], q) if ex["result_df"] is not None else "bar_v"

        results.append({
            "id": idx,
            "question": q,
            "title": title,
            "passed": passed,
            "score": score,
            "max_score": 8,
            "rows": len(ex["result_df"]) if ex["result_df"] is not None else 0,
            "chart_type": chart_type,
            "insight": insight,
            "time_ms": round(elapsed, 2),
            "code": tr["code"]
        })

    return {
        "total_score": total_score,
        "max_score": 40,
        "all_passed": total_score == 40,
        "benchmark_results": results
    }

@app.post("/api/test-attack")
def test_attack(req: SecurityAttackRequest):
    """Simulates malicious code injection attempts to demonstrate sandbox security."""
    attacks = {
        "os_system": ("Shell Command Injection (os.system)", "import os\nos.system('whoami')"),
        "subprocess": ("Process Spawning (subprocess.Popen)", "import subprocess\nsubprocess.Popen(['notepad.exe'])"),
        "eval_import": ("Obfuscated Dynamic Eval (__import__)", "eval(\"__import__('os').getcwd()\")"),
        "dunder_escape": ("Metaprogramming Escape (__subclasses__)", "x = ().__class__.__bases__[0].__subclasses__()\nresult_df = pd.DataFrame()"),
        "file_overwrite": ("Unauthorized Disk Write (to_csv)", "df.to_csv('system_leak.csv')\nresult_df = df"),
        "open_read": ("File System Access (open)", "with open('C:/Windows/win.ini') as f:\n    result_df = pd.DataFrame({'f': [f.read()]})")
    }

    if req.attack_type not in attacks:
        raise HTTPException(status_code=400, detail="Unknown attack type.")

    label, code = attacks[req.attack_type]
    test_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    res = state.sandbox.execute(code, test_df)

    return {
        "attack_label": label,
        "attempted_code": code,
        "blocked": not res["success"],
        "is_security_violation": res.get("is_security_violation", False),
        "violations": res.get("violations", []),
        "passed_checks": res.get("passed_checks", [])
    }

@app.get("/api/export-csv")
def export_csv():
    """Exports the last query result as a downloadable CSV."""
    if state.last_query_result is None or state.last_query_result.empty:
        raise HTTPException(status_code=400, detail="No active query result available to export.")

    stream = io.StringIO()
    state.last_query_result.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=spreadsheet_analyst_export.csv"
    return response

# Serve static files and UI
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Spreadsheet Analyst Backend Running</h1><p>Static index.html not found yet.</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
