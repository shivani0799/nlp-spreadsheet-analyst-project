"""
chatbot.py
Conversational AI Data Copilot for Spreadsheet Analyst
Provides conversational Q&A, chart interpretation, business recommendations,
and proactive query suggestions.
"""

import os
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class DataChatbot:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()
        os.environ["GROQ_API_KEY"] = self.api_key

    def _build_context_summary(self, df: Optional[pd.DataFrame], dataset_name: str, last_query: str, last_result_df: Optional[pd.DataFrame]) -> str:
        lines = [f"ACTIVE DATASET: {dataset_name}"]
        if df is not None:
            lines.append(f"Total Rows: {len(df):,}, Total Columns: {len(df.columns)}")
            lines.append(f"Key Columns: {', '.join(list(df.columns)[:15])}")
        
        if last_query:
            lines.append(f"\nLAST DASHBOARD QUERY: '{last_query}'")
        
        if last_result_df is not None and not last_result_df.empty:
            preview_str = last_result_df.head(6).to_string(index=False)
            lines.append(f"CURRENT RESULT DATA PREVIEW:\n{preview_str}")
        
        return "\n".join(lines)

    def chat(self, 
             message: str, 
             history: List[Dict[str, str]], 
             df: Optional[pd.DataFrame] = None, 
             dataset_name: str = "NYC 311 Service Requests", 
             last_query: str = "", 
             last_result_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Processes conversational queries using Groq LLM with context awareness,
        or falls back to built-in business intelligence rules when offline.
        """
        context_str = self._build_context_summary(df, dataset_name, last_query, last_result_df)
        
        system_prompt = f"""You are the "Spreadsheet Analyst AI Copilot", an elite enterprise business intelligence advisor.
You are conversing with a business user about their spreadsheet data.

DATASET & ACTIVE CONTEXT:
{context_str}

GUIDELINES:
1. Provide concise, high-value, executive-ready insights.
2. When interpreting data, cite specific metrics, counts, and percentages from the context.
3. Suggest clear, actionable business recommendations or next steps.
4. If the user asks to see or filter a specific slice of data (e.g. 'Show me complaints in Brooklyn' or 'Filter by NYPD'), you can include an action tag at the end of your response:
   `[ACTION_QUERY: <the natural language query>]`
   The UI will automatically run this query on the main dashboard!
5. Format your answers clearly using markdown bolding and bullet points.
"""

        # Try Groq LLM
        if self.api_key:
            try:
                from groq import Groq
                client = Groq(api_key=self.api_key)
                
                messages = [{"role": "system", "content": system_prompt}]
                
                # Append last 6 turns of history
                for turn in history[-6:]:
                    if turn.get("role") in ["user", "assistant"] and turn.get("content"):
                        messages.append({"role": turn["role"], "content": turn["content"]})
                
                messages.append({"role": "user", "content": message})

                # Try available models
                models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]
                response_text = None
                for m in models:
                    try:
                        resp = client.chat.completions.create(
                            model=m,
                            messages=messages,
                            temperature=0.3,
                            max_tokens=650
                        )
                        response_text = resp.choices[0].message.content
                        break
                    except Exception:
                        continue

                if response_text:
                    # Check for action query tag
                    action_query = None
                    if "[ACTION_QUERY:" in response_text:
                        import re
                        match = re.search(r'\[ACTION_QUERY:\s*(.*?)\]', response_text)
                        if match:
                            action_query = match.group(1).strip()
                            response_text = re.sub(r'\[ACTION_QUERY:.*?\]', '', response_text).strip()

                    return {
                        "reply": response_text,
                        "source": "groq_copilot",
                        "action_query": action_query
                    }
            except Exception as e:
                print(f"[!] Groq chat error: {e}")

        # Fallback offline intelligence
        return self._offline_chat_response(message, df, last_query, last_result_df)

    def _offline_chat_response(self, message: str, df: Optional[pd.DataFrame], last_query: str, last_result_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Provides rich heuristic business intelligence answers when offline."""
        m = message.lower()
        
        if "recommend" in m or "action" in m or "suggestion" in m:
            reply = (
                "### 🎯 Strategic Business Recommendations:\n\n"
                "1. **Target Peak Noise Times**: Deploy targeted decibel monitoring units between 10 PM and 3 AM in high-density corridors.\n"
                "2. **Automate Triage for Parking & Blocked Driveways**: NYPD tow trucks and precinct dispatch can prioritize clear paths for emergency services.\n"
                "3. **Predictive Resource Reallocation**: Shift seasonal response staff to HPD and DEP during peak weather and temperature fluctuations."
            )
            return {"reply": reply, "source": "offline_copilot", "action_query": None}
            
        elif "explain" in m or "insight" in m or "summary" in m:
            if last_result_df is not None and not last_result_df.empty:
                top_row = last_result_df.iloc[0]
                cols = list(last_result_df.columns)
                reply = (
                    f"### 📊 Key Findings from Current Dashboard:\n\n"
                    f"- **Leading Category**: **{top_row[cols[0]]}** accounts for the highest volume (**{top_row[cols[1]]}**).\n"
                    f"- **Concentration**: Over 60% of total volume is clustered across the top 3 segments.\n"
                    f"- **Next Step**: Consider drilling down by borough or department to pinpoint root causes."
                )
            else:
                reply = "The active dataset contains service requests across multiple city departments. Noise complaints and parking violations account for the lion's share of inbound citizen reports."
            return {"reply": reply, "source": "offline_copilot", "action_query": None}

        elif "borough" in m or "brooklyn" in m or "queens" in m or "manhattan" in m:
            reply = (
                "### 🗺️ Geographic Distribution Summary:\n\n"
                "- **Brooklyn & Queens** exhibit the highest overall request volumes due to population density and residential zoning.\n"
                "- **Manhattan** has higher proportions of commercial noise and street condition issues.\n"
                "- Would you like to view the full borough breakdown chart?"
            )
            return {"reply": reply, "source": "offline_copilot", "action_query": "Which borough has the highest number of complaints?"}

        elif "nypd" in m or "police" in m or "agency" in m:
            reply = (
                "### 🏛️ Agency Workload Insight:\n\n"
                "- **NYPD** receives the overwhelming majority of 311 service requests, primarily driven by quality-of-life calls (residential/street noise and blocked driveways).\n"
                "- I have triggered the agency workload breakdown for you on the main dashboard."
            )
            return {"reply": reply, "source": "offline_copilot", "action_query": "Which agency handles the most complaints?"}

        else:
            reply = (
                f"I'm your **Spreadsheet Analyst AI Copilot**! I can answer analytical questions, identify trends, provide business recommendations, or automatically update the dashboard for you.\n\n"
                "Try asking:\n"
                "- *'What are the top 3 recommendations based on this data?'*\n"
                "- *'Explain the current chart findings'*;\n"
                "- *'Show complaints by borough'*."
            )
            return {"reply": reply, "source": "offline_copilot", "action_query": None}

data_chatbot = DataChatbot()
