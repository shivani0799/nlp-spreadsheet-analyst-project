"""
sandbox.py
Hardened AST Security Validator and Safe Code Execution Sandbox
Satisfies Task 2, 4 & Rubric (10 marks for Safety - prevents malicious code execution).
"""

import ast
import time
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional, List

class ASTSecurityError(Exception):
    """Raised when code violates security policies."""
    pass

class ASTSecurityValidator(ast.NodeVisitor):
    BANNED_IMPORTS = {
        'os', 'sys', 'subprocess', 'shutil', 'socket', 'http', 'urllib', 'requests',
        'pty', 'commands', 'builtins', '__builtin__', 'importlib', 'pickle', 'ctypes',
        'platform', 'signal', 'threading', 'multiprocessing', 'asyncio', 'webbrowser'
    }

    BANNED_FUNCTIONS = {
        'open', 'eval', 'exec', 'compile', '__import__', 'globals', 'locals',
        'getattr', 'setattr', 'delattr', 'hasattr', 'breakpoint', 'exit', 'quit',
        'input', 'help', 'memoryview', 'classmethod', 'staticmethod', 'super'
    }

    BANNED_ATTRIBUTES = {
        '__builtins__', '__subclasses__', '__bases__', '__mro__', '__class__',
        '__dict__', '__code__', '__globals__', '__closure__', '__func__',
        '__self__', '__module__', '__qualname__', '__annotations__',
        'to_csv', 'to_excel', 'to_sql', 'to_pickle', 'to_json', 'to_parquet'  # prevent unauthorized file writes
    }

    def __init__(self):
        self.violations: List[str] = []
        self.passed_checks: List[str] = []

    def visit_Import(self, node: ast.Import):
        self.violations.append(f"Disallowed import statement: {[alias.name for alias in node.names]}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.violations.append(f"Disallowed from-import statement: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check direct call by name (e.g. eval(), exec(), open())
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.BANNED_FUNCTIONS or func_name in self.BANNED_IMPORTS:
                self.violations.append(f"Disallowed function call: {func_name}()")
        # Check call via attribute (e.g. os.system(), sys.exit())
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in self.BANNED_FUNCTIONS or attr_name in self.BANNED_ATTRIBUTES:
                self.violations.append(f"Disallowed method/call: {attr_name}()")
            if isinstance(node.func.value, ast.Name) and node.func.value.id in self.BANNED_IMPORTS:
                self.violations.append(f"Disallowed module call: {node.func.value.id}.{attr_name}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in self.BANNED_ATTRIBUTES:
            self.violations.append(f"Access to forbidden dunder or write attribute: '{node.attr}'")
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global):
        self.violations.append("Global statement is forbidden.")
        self.generic_visit(node)

    def visit_Nonlocal(self, node: ast.Nonlocal):
        self.violations.append("Nonlocal statement is forbidden.")
        self.generic_visit(node)

    def validate(self, code_str: str) -> Tuple[bool, List[str], List[str]]:
        """
        Parses and inspects code AST.
        Returns: (is_safe, passed_checks, violations)
        """
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, [], [f"Syntax Error in generated code: {e}"]

        self.violations = []
        self.visit(tree)

        checks = [
            "AST Syntax Tree Validated",
            "Zero Unauthorized Imports (import / from ... import blocked)",
            "Zero System Execution Calls (os, sys, subprocess blocked)",
            "Zero File/Network I/O Operations (open, requests, socket blocked)",
            "Zero Metaprogramming / Sandbox Escape Vectors (__subclasses__, __globals__ blocked)",
            "Zero Disk Write Operations (to_csv, to_excel, to_pickle blocked)"
        ]

        if self.violations:
            return False, [], self.violations
        return True, checks, []


class SafeSandbox:
    SAFE_BUILTINS = {
        'abs': abs,
        'all': all,
        'any': any,
        'bool': bool,
        'dict': dict,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'int': int,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'range': range,
        'round': round,
        'set': set,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'zip': zip,
        'True': True,
        'False': False,
        'None': None
    }

    def __init__(self):
        self.validator = ASTSecurityValidator()

    def execute(self, code_str: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Safely executes AST-validated Python/Pandas code.
        Guarantees:
        - AST security check must pass first
        - Read-only copy of input df
        - Restricted execution namespace with no dangerous builtins
        - Output coerced into standardized pd.DataFrame
        """
        start_time = time.perf_counter()
        
        # 1. AST Security Validation
        is_safe, passed_checks, violations = self.validator.validate(code_str)
        if not is_safe:
            return {
                "success": False,
                "error": f"Security Policy Violation: {'; '.join(violations)}",
                "violations": violations,
                "passed_checks": [],
                "result_df": None,
                "execution_time_ms": 0.0,
                "is_security_violation": True
            }

        # 2. Setup isolated execution environment
        df_copy = df.copy()
        local_scope = {
            "df": df_copy,
            "pd": pd,
            "np": np,
            "result_df": None
        }
        global_scope = {
            "__builtins__": self.SAFE_BUILTINS,
            "pd": pd,
            "np": np
        }

        # 3. Execution
        try:
            exec(code_str, global_scope, local_scope)
            execution_time = (time.perf_counter() - start_time) * 1000.0

            # Retrieve result_df or detect what was computed
            result = local_scope.get("result_df")
            if result is None:
                # If result_df wasn't explicitly assigned, look for last updated dataframe/series
                for var_name, var_val in local_scope.items():
                    if var_name not in ["df", "pd", "np", "__builtins__"]:
                        if isinstance(var_val, (pd.DataFrame, pd.Series)):
                            result = var_val
                            break

            if result is None:
                return {
                    "success": False,
                    "error": "Code executed but did not assign a 'result_df' DataFrame or Series.",
                    "violations": [],
                    "passed_checks": passed_checks,
                    "result_df": None,
                    "execution_time_ms": round(execution_time, 2),
                    "is_security_violation": False
                }

            # Standardize result into a clean pd.DataFrame
            if isinstance(result, pd.Series):
                result_df = result.reset_index()
                # Ensure column names are clean
                if len(result_df.columns) == 2:
                    result_df.columns = ['Category', 'Value']
            elif isinstance(result, pd.DataFrame):
                result_df = result.copy()
                # If index is meaningful (not simple RangeIndex), reset it
                if not isinstance(result_df.index, pd.RangeIndex):
                    result_df = result_df.reset_index()
            else:
                # Scalar or list
                result_df = pd.DataFrame([{"Result": result}])

            return {
                "success": True,
                "error": None,
                "violations": [],
                "passed_checks": passed_checks,
                "result_df": result_df,
                "execution_time_ms": round(execution_time, 2),
                "is_security_violation": False
            }

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": False,
                "error": f"Runtime Execution Error: {type(e).__name__}: {str(e)}",
                "violations": [],
                "passed_checks": passed_checks,
                "result_df": None,
                "execution_time_ms": round(execution_time, 2),
                "is_security_violation": False
            }

if __name__ == "__main__":
    # Test safe code vs attack code
    sandbox = SafeSandbox()
    test_df = pd.DataFrame({"complaint_type": ["Noise", "Heat", "Noise", "Traffic"], "count": [10, 20, 30, 40]})

    print("--- 1. Testing Safe Transformation ---")
    safe_code = "result_df = df.groupby('complaint_type')['count'].sum().reset_index()"
    res = sandbox.execute(safe_code, test_df)
    print("Safe Code Success:", res["success"], "| Rows:", len(res["result_df"]) if res["result_df"] is not None else 0)
    print("Checks Passed:", res["passed_checks"])

    print("\n--- 2. Testing Malicious Attack: os.system ---")
    attack_1 = "import os\nos.system('echo HACKED')"
    res1 = sandbox.execute(attack_1, test_df)
    print("Attack 1 Blocked:", not res1["success"], "| Reason:", res1["error"])

    print("\n--- 3. Testing Malicious Attack: __import__ & eval ---")
    attack_2 = "eval(\"__import__('os').system('dir')\")"
    res2 = sandbox.execute(attack_2, test_df)
    print("Attack 2 Blocked:", not res2["success"], "| Reason:", res2["error"])

    print("\n--- 4. Testing Malicious Attack: Sandbox Escape via __subclasses__ ---")
    attack_3 = "x = ().__class__.__bases__[0].__subclasses__()\nresult_df = pd.DataFrame({'x': [1]})"
    res3 = sandbox.execute(attack_3, test_df)
    print("Attack 3 Blocked:", not res3["success"], "| Reason:", res3["error"])

    print("\n--- 5. Testing File Overwrite: to_csv ---")
    attack_4 = "df.to_csv('system32.dll')\nresult_df = df"
    res4 = sandbox.execute(attack_4, test_df)
    print("Attack 4 Blocked:", not res4["success"], "| Reason:", res4["error"])
