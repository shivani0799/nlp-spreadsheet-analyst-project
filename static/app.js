/**
 * app.js - Frontend Controller for Natural Language Spreadsheet Analyst
 * Implements Plotly rendering, interactive data tables, preset query chips,
 * live AST attack simulations, and benchmark evaluation suite.
 */

// Application State
const appState = {
  currentQuestion: "What are the top 10 most frequent complaint types?",
  currentChartType: "",
  activeView: "plotly", // "plotly" or "static"
  rawTableData: [],
  tableColumns: [],
  useLLM: true,
  apiKey: "",
  provider: "groq",
  user: null,
  chatHistory: []
};

// DOM Elements
const elements = {
  queryForm: document.getElementById("query-form"),
  queryInput: document.getElementById("query-input"),
  chartTypeSelector: document.getElementById("chart-type-selector"),
  submitBtn: document.getElementById("btn-submit-query"),
  presetChips: document.querySelectorAll(".preset-chip"),
  btnResetNyc: document.getElementById("btn-reset-nyc"),

  // User & Auth
  btnOpenAuth: document.getElementById("btn-open-auth"),
  userDisplayName: document.getElementById("user-display-name"),
  userAvatarInitials: document.getElementById("user-avatar-initials"),
  userDropdown: document.getElementById("user-dropdown"),
  dropdownUserName: document.getElementById("dropdown-user-name"),
  dropdownUserRole: document.getElementById("dropdown-user-role"),
  btnSignout: document.getElementById("btn-signout"),
  authModal: document.getElementById("auth-modal"),
  btnCloseAuth: document.getElementById("btn-close-auth"),
  tabBtnSignin: document.getElementById("tab-btn-signin"),
  tabBtnSignup: document.getElementById("tab-btn-signup"),
  authPaneSignin: document.getElementById("auth-pane-signin"),
  authPaneSignup: document.getElementById("auth-pane-signup"),
  signinForm: document.getElementById("signin-form"),
  signupForm: document.getElementById("signup-form"),
  btnDemoSignin: document.getElementById("btn-demo-signin"),
  signinError: document.getElementById("signin-error"),
  signupError: document.getElementById("signup-error"),

  // Chatbot
  btnToggleChat: document.getElementById("btn-toggle-chat"),
  chatPanel: document.getElementById("chat-panel"),
  btnCloseChat: document.getElementById("btn-close-chat"),
  btnClearChat: document.getElementById("btn-clear-chat"),
  chatMessagesScroll: document.getElementById("chat-messages-scroll"),
  chatInputForm: document.getElementById("chat-input-form"),
  chatUserInput: document.getElementById("chat-user-input"),
  suggestionChips: document.querySelectorAll(".suggestion-chip"),

  // Insight & Stats
  insightText: document.getElementById("insight-text-display"),
  statQueryTime: document.getElementById("stat-query-time"),
  statSandboxSafe: document.getElementById("stat-sandbox-safe"),

  // Charts
  plotlyDiv: document.getElementById("plotly-chart-div"),
  matplotlibDiv: document.getElementById("matplotlib-chart-div"),
  matplotlibImg: document.getElementById("matplotlib-img"),
  btnViewPlotly: document.getElementById("btn-view-plotly"),
  btnViewStatic: document.getElementById("btn-view-static"),
  badgeChartType: document.getElementById("badge-chart-type"),
  chartDisplayTitle: document.getElementById("chart-display-title"),

  // Table
  tableHead: document.getElementById("table-head"),
  tableBody: document.getElementById("table-body"),
  tableRowCountBadge: document.getElementById("table-row-count-badge"),
  tableFilterInput: document.getElementById("table-filter-input"),
  btnExportCsv: document.getElementById("btn-export-csv"),

  // Audit Banner
  auditHeader: document.getElementById("audit-toggle-header"),
  auditDrawer: document.getElementById("audit-details-drawer"),
  statQualityScore: document.getElementById("stat-quality-score"),
  statRowsCount: document.getElementById("stat-rows-count"),
  statDupsRemoved: document.getElementById("stat-dups-removed"),
  statDatesParsed: document.getElementById("stat-dates-parsed"),
  auditDatesList: document.getElementById("audit-dates-list"),
  auditNumericList: document.getElementById("audit-numeric-list"),
  auditDerivedList: document.getElementById("audit-derived-list"),

  // Inspector
  inspectorHeader: document.getElementById("inspector-toggle-header"),
  inspectorBody: document.getElementById("inspector-body"),
  codeSnippet: document.getElementById("code-snippet-display"),
  securityChecksList: document.getElementById("security-checks-list"),
  badgeEngineType: document.getElementById("badge-engine-type"),
  inspectorTabs: document.querySelectorAll(".tab-btn"),

  // Modals
  benchmarkModal: document.getElementById("benchmark-modal"),
  securityModal: document.getElementById("security-modal"),
  settingsModal: document.getElementById("settings-modal"),
  btnOpenBenchmark: document.getElementById("btn-open-benchmark"),
  btnOpenSecurity: document.getElementById("btn-open-security"),
  btnOpenSettings: document.getElementById("btn-open-settings"),
  btnCloseBenchmark: document.getElementById("btn-close-benchmark"),
  btnCloseSecurity: document.getElementById("btn-close-security"),
  btnCloseSettings: document.getElementById("btn-close-settings"),
  btnDoneBenchmark: document.getElementById("btn-done-benchmark"),
  btnRerunBenchmark: document.getElementById("btn-rerun-benchmark"),

  // Attack Lab
  attackBtns: document.querySelectorAll(".attack-btn"),
  attackResultDisplay: document.getElementById("attack-result-display"),

  // Upload
  fileInput: document.getElementById("csv-file-input"),
  datasetPillLabel: document.getElementById("dataset-pill-label"),

  // Settings Form
  settingsForm: document.getElementById("settings-form"),
  apiKeyInput: document.getElementById("api-key-input"),
  providerSelect: document.getElementById("provider-select"),
  useLlmToggle: document.getElementById("use-llm-toggle")
};

// Initialization
document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  setupAuth();
  setupChatbot();
  await loadStatus();
});

// Load backend status and audit summary
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.status === "ready" && data.audit) {
      updateAuditUI(data.audit, data.dataset_name);
    }
  } catch (err) {
    console.warn("Could not fetch status:", err);
  }
}

function updateAuditUI(audit, datasetName) {
  if (elements.statQualityScore) elements.statQualityScore.textContent = `${audit.quality_score}%`;
  if (elements.statRowsCount) elements.statRowsCount.textContent = audit.final_rows.toLocaleString();
  if (elements.statDupsRemoved) elements.statDupsRemoved.textContent = audit.duplicates_removed;
  if (elements.statDatesParsed) elements.statDatesParsed.textContent = audit.dates_parsed.length;
  if (elements.datasetPillLabel) {
    elements.datasetPillLabel.textContent = `${datasetName} • ${audit.final_rows.toLocaleString()} Rows Cleaned`;
  }

  // Populate lists
  if (elements.auditDatesList) {
    elements.auditDatesList.innerHTML = audit.dates_parsed.map(c => `<li>${c}</li>`).join("") || "<li>None</li>";
  }
  if (elements.auditNumericList) {
    elements.auditNumericList.innerHTML = audit.numeric_inferred.map(c => `<li>${c}</li>`).join("") || "<li>None</li>";
  }
  if (elements.auditDerivedList) {
    elements.auditDerivedList.innerHTML = audit.derived_columns.map(c => `<li>${c}</li>`).join("") || "<li>None</li>";
  }
}

// Core Query Execution Function
async function runQuery(question, chartTypeOverride = "") {
  if (!question.trim()) return;

  setLoadingState(true);
  appState.currentQuestion = question;
  elements.queryInput.value = question;

  try {
    const payload = {
      question: question,
      chart_type_override: chartTypeOverride || elements.chartTypeSelector.value || null,
      use_llm: appState.useLLM,
      api_key: appState.apiKey || null,
      provider: appState.provider || "groq"
    };

    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    let data;
    try {
      data = await res.json();
    } catch (e) {
      const text = await res.text();
      handleQueryError({ error: `Server error (${res.status}): ${text.slice(0, 100)}` });
      return;
    }

    if (!data.success) {
      handleQueryError(data);
      return;
    }

    renderQueryResult(data);
  } catch (err) {
    handleQueryError({ error: `Network error or server unavailable: ${err.message}` });
  } finally {
    setLoadingState(false);
  }
}

function renderQueryResult(data) {
  // 1. Update Executive Insight
  elements.insightText.textContent = data.insight;
  elements.statQueryTime.textContent = `⚡ ${data.execution_time_ms} ms`;
  elements.statSandboxSafe.textContent = "🛡️ AST Sandbox Safe";
  elements.statSandboxSafe.className = "stat-pill-success";

  // 2. Render Plotly Chart
  if (data.plotly_spec && data.plotly_spec.data) {
    Plotly.react(elements.plotlyDiv, data.plotly_spec.data, data.plotly_spec.layout, {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ['lasso2d', 'select2d']
    });
  }

  // 3. Render Matplotlib PNG
  if (data.matplotlib_png) {
    elements.matplotlibImg.src = data.matplotlib_png;
  }

  elements.badgeChartType.textContent = (data.chart_type || "Bar").replace("_", " ").toUpperCase();
  elements.chartDisplayTitle.textContent = data.question;

  // 4. Render Data Table
  appState.rawTableData = data.table.rows || [];
  appState.tableColumns = data.table.columns || [];
  renderTable(appState.rawTableData);
  elements.tableRowCountBadge.textContent = `${data.table.total_rows} Rows`;

  // 5. Update Inspector
  elements.codeSnippet.textContent = data.code;
  elements.badgeEngineType.textContent = data.source;

  if (data.security && data.security.passed_checks) {
    elements.securityChecksList.innerHTML = data.security.passed_checks
      .map(chk => `<li>${chk}</li>`)
      .join("");
  }
}

function renderTable(rows) {
  if (!elements.tableHead || !elements.tableBody) return;

  if (rows.length === 0) {
    elements.tableHead.innerHTML = "";
    elements.tableBody.innerHTML = `<tr><td style="text-align:center; padding: 20px; color:#64748b;">No rows found.</td></tr>`;
    return;
  }

  const cols = appState.tableColumns;
  // Header
  elements.tableHead.innerHTML = `<tr>${cols.map(c => `<th>${c.label}</th>`).join("")}</tr>`;

  // Body
  elements.tableBody.innerHTML = rows.map(row => {
    return `<tr>${cols.map(c => {
      const val = row[c.key];
      const displayVal = (val === null || val === undefined) ? `<span style="color:#64748b;">null</span>` : val;
      return `<td>${displayVal}</td>`;
    }).join("")}</tr>`;
  }).join("");
}

function handleQueryError(data) {
  elements.insightText.textContent = `❌ ${data.error || 'Execution failed.'}`;
  elements.statSandboxSafe.textContent = data.is_security_violation ? "🚨 VIOLATION BLOCKED" : "⚠️ Runtime Error";
  elements.statSandboxSafe.className = "stat-pill";
  elements.statSandboxSafe.style.background = "rgba(244, 63, 94, 0.2)";
  elements.statSandboxSafe.style.color = "#fda4af";

  if (data.code) {
    elements.codeSnippet.textContent = `# FAILED CODE:\n${data.code}`;
  }
}

function setLoadingState(isLoading) {
  if (isLoading) {
    elements.submitBtn.disabled = true;
    elements.submitBtn.style.opacity = "0.7";
    elements.insightText.textContent = "Analyzing spreadsheet and executing AST-validated logic...";
  } else {
    elements.submitBtn.disabled = false;
    elements.submitBtn.style.opacity = "1";
  }
}

// Event Listeners setup
function setupEventListeners() {
  // Query Form
  elements.queryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = elements.queryInput.value;
    runQuery(q);
  });

  // Chart type dropdown change
  elements.chartTypeSelector.addEventListener("change", () => {
    runQuery(elements.queryInput.value, elements.chartTypeSelector.value);
  });

  // Preset chips
  elements.presetChips.forEach(chip => {
    chip.addEventListener("click", () => {
      elements.presetChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      const question = chip.getAttribute("data-q");
      runQuery(question);
    });
  });

  // Chart view toggle (Interactive vs Static Matplotlib)
  elements.btnViewPlotly.addEventListener("click", () => {
    elements.btnViewPlotly.classList.add("active");
    elements.btnViewStatic.classList.remove("active");
    elements.plotlyDiv.classList.remove("hidden");
    elements.matplotlibDiv.classList.add("hidden");
  });

  elements.btnViewStatic.addEventListener("click", () => {
    elements.btnViewStatic.classList.add("active");
    elements.btnViewPlotly.classList.remove("active");
    elements.plotlyDiv.classList.add("hidden");
    elements.matplotlibDiv.classList.remove("hidden");
  });

  // Table filter search
  elements.tableFilterInput.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase().trim();
    if (!term) {
      renderTable(appState.rawTableData);
      return;
    }
    const filtered = appState.rawTableData.filter(row => {
      return Object.values(row).some(v => String(v).toLowerCase().includes(term));
    });
    renderTable(filtered);
  });

  // CSV Export
  elements.btnExportCsv.addEventListener("click", () => {
    window.location.href = "/api/export-csv";
  });

  // Collapsible Audit Banner
  elements.auditHeader.addEventListener("click", () => {
    elements.auditDrawer.classList.toggle("hidden");
  });

  // Collapsible Inspector
  elements.inspectorHeader.addEventListener("click", () => {
    elements.inspectorBody.classList.toggle("hidden");
  });

  // Inspector Tabs
  elements.inspectorTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      elements.inspectorTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      document.getElementById("tab-code").classList.add("hidden");
      document.getElementById("tab-security").classList.add("hidden");
      document.getElementById(targetId).classList.remove("hidden");
    });
  });

  // Reload NYC 311 Dataset
  if (elements.btnResetNyc) {
    elements.btnResetNyc.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/reset-nyc-dataset", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          updateAuditUI(data.audit, data.dataset_name);
          runQuery("What are the top 10 most frequent complaint types?");
        }
      } catch (err) {
        alert("Failed to reload NYC 311 dataset: " + err.message);
      }
    });
  }

  // Modals open/close
  elements.btnOpenBenchmark.addEventListener("click", openBenchmarkModal);
  elements.btnCloseBenchmark.addEventListener("click", () => elements.benchmarkModal.classList.add("hidden"));
  elements.btnDoneBenchmark.addEventListener("click", () => elements.benchmarkModal.classList.add("hidden"));
  elements.btnRerunBenchmark.addEventListener("click", runBenchmarkSuite);

  elements.btnOpenSecurity.addEventListener("click", () => elements.securityModal.classList.remove("hidden"));
  elements.btnCloseSecurity.addEventListener("click", () => elements.securityModal.classList.add("hidden"));

  elements.btnOpenSettings.addEventListener("click", () => elements.settingsModal.classList.remove("hidden"));
  elements.btnCloseSettings.addEventListener("click", () => elements.settingsModal.classList.add("hidden"));

  // Security Attack Buttons
  elements.attackBtns.forEach(btn => {
    btn.addEventListener("click", async () => {
      const attackType = btn.getAttribute("data-attack");
      await executeSimulatedAttack(attackType);
    });
  });

  // Settings Form
  elements.settingsForm.addEventListener("submit", (e) => {
    e.preventDefault();
    appState.apiKey = elements.apiKeyInput.value.trim();
    appState.provider = elements.providerSelect.value;
    appState.useLLM = elements.useLlmToggle.checked;
    elements.settingsModal.classList.add("hidden");
    alert(`Settings saved! LLM Mode: ${appState.useLLM ? 'Enabled' : 'Offline Engine'}`);
  });

  // File Upload
  elements.fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    elements.datasetPillLabel.textContent = `Uploading & Cleaning ${file.name}...`;

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        updateAuditUI(data.audit, data.filename);
        runQuery("Top complaints");
      } else {
        alert(`Upload error: ${data.detail || 'Could not process file'}`);
      }
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    }
  });
}

// Benchmark Suite Runner
async function openBenchmarkModal() {
  elements.benchmarkModal.classList.remove("hidden");
  await runBenchmarkSuite();
}

async function runBenchmarkSuite() {
  const container = document.getElementById("benchmark-items-container");
  container.innerHTML = `<p style="color:#94a3b8; padding: 20px 0;">Executing 5 predefined benchmark questions through the analytical engine...</p>`;

  try {
    const res = await fetch("/api/run-benchmark", { method: "POST" });
    const data = await res.json();

    document.getElementById("benchmark-score-pill").textContent = `Score: ${data.total_score} / ${data.max_score} (${(data.total_score / data.max_score * 100).toFixed(0)}%)`;

    container.innerHTML = data.benchmark_results.map(item => `
      <div class="benchmark-item">
        <div class="benchmark-info">
          <h4>Q${item.id}: ${item.title}</h4>
          <p>${item.question} • <em>${item.time_ms} ms</em></p>
          <p style="color:#38bdf8; margin-top:4px;">${item.insight}</p>
        </div>
        <div class="benchmark-badge-pass">
          ${item.passed ? `✓ ${item.score}/${item.max_score} MARKS` : `FAILED`}
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<p style="color:#f43f5e;">Failed to run benchmark: ${err.message}</p>`;
  }
}

// Security Attack Simulator
async function executeSimulatedAttack(attackType) {
  elements.attackResultDisplay.innerHTML = `<p style="color:#94a3b8;">Injecting malicious payload into sandbox...</p>`;

  try {
    const res = await fetch("/api/test-attack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ attack_type: attackType })
    });
    const data = await res.json();

    if (data.blocked) {
      elements.attackResultDisplay.innerHTML = `
        <div class="attack-alert-blocked">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
          MALICIOUS CODE ATTACK INTERCEPTED & BLOCKED (+10/10 SAFETY)
        </div>
        <p><strong>Vector:</strong> ${data.attack_label}</p>
        <p style="color:#fda4af; margin-top:4px;"><strong>AST Violations:</strong> ${data.violations.join(" | ")}</p>
        <div class="attack-code-preview">${escapeHtml(data.attempted_code)}</div>
      `;
    } else {
      elements.attackResultDisplay.innerHTML = `<p style="color:#f43f5e;">⚠️ ATTACK WAS NOT BLOCKED!</p>`;
    }
  } catch (err) {
    elements.attackResultDisplay.innerHTML = `<p style="color:#f43f5e;">Error during test: ${err.message}</p>`;
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ==========================================
// FIRST PAGE AUTHENTICATION & SCREEN ROUTER
// ==========================================
function showAuthPortal() {
  const authPortal = document.getElementById("auth-portal-view");
  const dashboard = document.getElementById("main-dashboard-view");
  const chatRoot = document.getElementById("chat-widget-root");

  if (authPortal) authPortal.classList.remove("hidden");
  if (dashboard) dashboard.classList.add("hidden");
  if (chatRoot) chatRoot.classList.add("hidden");
}

function showDashboard(user) {
  const authPortal = document.getElementById("auth-portal-view");
  const dashboard = document.getElementById("main-dashboard-view");
  const chatRoot = document.getElementById("chat-widget-root");

  if (authPortal) authPortal.classList.add("hidden");
  if (dashboard) {
    dashboard.classList.remove("hidden");
    dashboard.classList.add("main-dashboard-page");
  }
  if (chatRoot) chatRoot.classList.remove("hidden");

  updateUserUI(user);

  // Trigger initial query if not loaded yet
  if (!appState.rawTableData || appState.rawTableData.length === 0) {
    runQuery("What are the top 10 most frequent complaint types?");
  }
}

async function setupAuth() {
  const token = localStorage.getItem("analyst_token");

  // Check existing session
  if (token) {
    try {
      const res = await fetch(`/api/auth/me?token=${token}`);
      const data = await res.json();
      if (data.authenticated && data.user) {
        showDashboard(data.user);
      } else {
        localStorage.removeItem("analyst_token");
        showAuthPortal();
      }
    } catch (e) {
      showAuthPortal();
    }
  } else {
    // Show first page: Sign In / Sign Up
    showAuthPortal();
  }

  // Auth Portal Tabs
  const tabBtnSignin = document.getElementById("tab-btn-signin");
  const tabBtnSignup = document.getElementById("tab-btn-signup");
  const authPaneSignin = document.getElementById("auth-pane-signin");
  const authPaneSignup = document.getElementById("auth-pane-signup");

  if (tabBtnSignin && tabBtnSignup) {
    tabBtnSignin.addEventListener("click", () => {
      tabBtnSignin.classList.add("active");
      tabBtnSignup.classList.remove("active");
      authPaneSignin.classList.remove("hidden");
      authPaneSignup.classList.add("hidden");
    });

    tabBtnSignup.addEventListener("click", () => {
      tabBtnSignup.classList.add("active");
      tabBtnSignin.classList.remove("active");
      authPaneSignup.classList.remove("hidden");
      authPaneSignin.classList.add("hidden");
    });
  }

  // Sign In Form (First Page)
  const portalSigninForm = document.getElementById("portal-signin-form");
  const portalSigninError = document.getElementById("portal-signin-error");
  if (portalSigninForm) {
    portalSigninForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("portal-signin-email").value.trim();
      const password = document.getElementById("portal-signin-password").value;
      if (portalSigninError) portalSigninError.classList.add("hidden");

      try {
        const res = await fetch("/api/auth/signin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.success) {
          localStorage.setItem("analyst_token", data.token);
          showDashboard(data.user);
        } else {
          if (portalSigninError) {
            portalSigninError.textContent = data.detail || "Invalid email or password.";
            portalSigninError.classList.remove("hidden");
          }
        }
      } catch (err) {
        if (portalSigninError) {
          portalSigninError.textContent = "Network error: " + err.message;
          portalSigninError.classList.remove("hidden");
        }
      }
    });
  }

  // Sign Up Form (First Page)
  const portalSignupForm = document.getElementById("portal-signup-form");
  const portalSignupError = document.getElementById("portal-signup-error");
  if (portalSignupForm) {
    portalSignupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("portal-signup-name").value.trim();
      const email = document.getElementById("portal-signup-email").value.trim();
      const role = document.getElementById("portal-signup-role").value;
      const password = document.getElementById("portal-signup-password").value;
      if (portalSignupError) portalSignupError.classList.add("hidden");

      try {
        const res = await fetch("/api/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password, role })
        });
        const data = await res.json();
        if (data.success) {
          localStorage.setItem("analyst_token", data.token);
          showDashboard(data.user);
        } else {
          if (portalSignupError) {
            portalSignupError.textContent = data.detail || "Could not create account.";
            portalSignupError.classList.remove("hidden");
          }
        }
      } catch (err) {
        if (portalSignupError) {
          portalSignupError.textContent = "Network error: " + err.message;
          portalSignupError.classList.remove("hidden");
        }
      }
    });
  }

  // 1-Click Instant Demo Login (First Page)
  const btnPortalDemo = document.getElementById("btn-portal-demo-signin");
  if (btnPortalDemo) {
    btnPortalDemo.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/auth/demo", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          localStorage.setItem("analyst_token", data.token);
          showDashboard(data.user);
        }
      } catch (err) {
        alert("Demo login error: " + err.message);
      }
    });
  }

  // Sign Out Button (Navbar)
  const btnSignout = document.getElementById("btn-signout");
  if (btnSignout) {
    btnSignout.addEventListener("click", () => {
      localStorage.removeItem("analyst_token");
      appState.user = null;
      showAuthPortal();
    });
  }
}

function updateUserUI(user) {
  if (!user) return;
  appState.user = user;
  const userDisplayName = document.getElementById("user-display-name");
  const userAvatarInitials = document.getElementById("user-avatar-initials");
  const userDisplayRole = document.getElementById("user-display-role");

  if (userDisplayName) userDisplayName.textContent = user.name.split(" ")[0];
  if (userAvatarInitials) userAvatarInitials.textContent = user.name.charAt(0).toUpperCase();
  if (userDisplayRole) userDisplayRole.textContent = user.role ? user.role.split(" ")[0] : "Analyst";
}

// ==========================================
// FLOATING AI CHATBOT COPILOT CONTROLLER
// ==========================================
function setupChatbot() {
  if (!elements.btnToggleChat) return;

  // Toggle chat panel
  elements.btnToggleChat.addEventListener("click", () => {
    elements.chatPanel.classList.toggle("hidden");
    if (!elements.chatPanel.classList.contains("hidden")) {
      elements.chatUserInput.focus();
    }
  });

  if (elements.btnCloseChat) {
    elements.btnCloseChat.addEventListener("click", () => {
      elements.chatPanel.classList.add("hidden");
    });
  }

  // Clear chat
  if (elements.btnClearChat) {
    elements.btnClearChat.addEventListener("click", () => {
      appState.chatHistory = [];
      elements.chatMessagesScroll.innerHTML = `
        <div class="chat-msg msg-assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-bubble">
            <p>👋 Conversation reset! How can I assist with your spreadsheet analysis?</p>
          </div>
        </div>
      `;
    });
  }

  // Suggestion chips
  if (elements.suggestionChips) {
    elements.suggestionChips.forEach(chip => {
      chip.addEventListener("click", () => {
        const prompt = chip.getAttribute("data-prompt");
        elements.chatUserInput.value = prompt;
        sendChatMessage(prompt);
      });
    });
  }

  // Chat submit
  if (elements.chatInputForm) {
    elements.chatInputForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const message = elements.chatUserInput.value.trim();
      if (!message) return;
      elements.chatUserInput.value = "";
      sendChatMessage(message);
    });
  }
}

async function sendChatMessage(message) {
  // Append user bubble
  appendMessageBubble("user", escapeHtml(message));
  appState.chatHistory.push({ role: "user", content: message });

  // Append typing bubble
  const typingId = "typing-" + Date.now();
  appendMessageBubble("assistant", "Thinking & inspecting data...", typingId);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        history: appState.chatHistory
      })
    });
    const data = await res.json();

    // Remove typing bubble
    const typingElem = document.getElementById(typingId);
    if (typingElem) typingElem.remove();

    if (data.success) {
      appendMessageBubble("assistant", formatMarkdown(data.reply), null, data.action_query);
      appState.chatHistory.push({ role: "assistant", content: data.reply });
    } else {
      appendMessageBubble("assistant", `⚠️ ${data.error || "Could not generate response."}`);
    }
  } catch (err) {
    const typingElem = document.getElementById(typingId);
    if (typingElem) typingElem.remove();
    appendMessageBubble("assistant", `⚠️ Network error: ${err.message}`);
  }
}

function appendMessageBubble(role, htmlContent, elementId = null, actionQuery = null) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg msg-${role}`;
  if (elementId) msgDiv.id = elementId;

  const avatar = role === "user" ? (appState.user ? appState.user.name.charAt(0) : "👤") : "🤖";

  let actionHtml = "";
  if (actionQuery) {
    actionHtml = `
      <div>
        <button class="chat-action-btn-bubble" onclick="runQueryFromChat('${escapeHtml(actionQuery)}')">
          ▶️ Run on Dashboard: "${escapeHtml(actionQuery)}"
        </button>
      </div>
    `;
  }

  msgDiv.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">
      <div>${htmlContent}</div>
      ${actionHtml}
    </div>
  `;

  elements.chatMessagesScroll.appendChild(msgDiv);
  elements.chatMessagesScroll.scrollTop = elements.chatMessagesScroll.scrollHeight;
}

window.runQueryFromChat = function (query) {
  elements.queryInput.value = query;
  runQuery(query);
};

function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Lists
  html = html.replace(/^[-\*]\s+(.*)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
  // Newlines to breaks
  html = html.replace(/\n\n/g, '<p></p>');
  html = html.replace(/\n/g, '<br/>');
  return html;
}

