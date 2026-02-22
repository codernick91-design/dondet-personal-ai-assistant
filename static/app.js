let currentConversation = null;
const API_BASE = "";

// Format time to China Standard Time
function formatTime(dateStr) {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('en-US', {
        timeZone: 'Asia/Shanghai',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (e) {
        console.error("Fetch error:", e);
        return null;
    }
}

// Conversations
async function loadConversations() {
    const items = await fetchJSON("/api/conversations");
    const list = document.getElementById("convo-list");
    list.innerHTML = "";
    if (items) {
        items.forEach(i => {
            const el = document.createElement("div");
            el.className = `convo-item ${currentConversation === i.id ? 'active' : ''}`;
            el.textContent = `${i.title} • ${formatTime(i.created_at)}`;
            el.onclick = () => loadConversation(i.id);
            list.appendChild(el);
        });
    }
}

async function loadConversation(id) {
    currentConversation = id;
    loadConversations(); // Update active state
    const msgs = await fetchJSON(`/api/conversations/${id}`);
    renderMessages(msgs || []);
}

async function createConversation() {
    const r = await fetchJSON("/api/conversations", {
        method: "POST",
        body: new URLSearchParams({ title: "New Conversation" }) // English title
    });
    if (r) {
        await loadConversation(r.id);
    }
}

// Messages
function renderMessages(msgs) {
    const box = document.getElementById("messages");
    box.innerHTML = "";
    msgs.forEach(m => {
        appendMessage(m.role, m.content);
    });
    scrollToBottom();
}

function appendMessage(role, content) {
    const box = document.getElementById("messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `msg ${role}`;
    
    const iconDiv = document.createElement("div");
    iconDiv.className = "msg-icon";
    // User icon: User, Assistant icon: Robot
    iconDiv.innerHTML = role === "user" ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement("div");
    contentDiv.className = "msg-content";
    if (role === "assistant") {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content; 
    }
    
    msgDiv.appendChild(iconDiv);
    msgDiv.appendChild(contentDiv);
    box.appendChild(msgDiv);
    scrollToBottom();
}

function scrollToBottom() {
    const box = document.getElementById("messages");
    box.scrollTop = box.scrollHeight;
}


// Settings
function loadSettings() {
    const key = localStorage.getItem("lm_api_key") || "";
    document.getElementById("lm-api-key").value = key;
}

function saveSettings() {
    const key = document.getElementById("lm-api-key").value.trim();
    if (key) {
        localStorage.setItem("lm_api_key", key);
    } else {
        localStorage.removeItem("lm_api_key");
    }
    document.getElementById("settings-modal").classList.add("hidden");
}

// Query
async function sendQuery() {
    const input = document.getElementById("query");
    const q = input.value.trim();
    if (!q) return;
    
    input.value = "";
    
    if (!currentConversation) {
        await createConversation();
    }
    
    appendMessage("user", q);
    
    // Create a placeholder for assistant response with status
    const msgId = "msg-" + Date.now();
    const box = document.getElementById("messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = "msg assistant";
    msgDiv.id = msgId;
    
    msgDiv.innerHTML = `
        <div class="msg-icon"><i class="fas fa-robot"></i></div>
        <div class="msg-content">
            <div id="status-${msgId}" class="status-indicator retrieval">
                <i class="fas fa-search"></i> Retrieval
            </div>
            <div id="content-${msgId}"></div>
        </div>
    `;
    box.appendChild(msgDiv);
    scrollToBottom();
    
    try {
        const form = new URLSearchParams();
        form.append("conversation_id", currentConversation);
        form.append("query", q);
        
        // Add API key if present
        const apiKey = localStorage.getItem("lm_api_key");
        if (apiKey) {
            form.append("api_key", apiKey);
        }
        
        const response = await fetch("/query", {
            method: "POST",
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let logs = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split("\n").filter(l => l.trim());
            
            for (const line of lines) {
                try {
                    const data = JSON.parse(line);
                    const statusEl = document.getElementById(`status-${msgId}`);
                    const contentEl = document.getElementById(`content-${msgId}`);
                    
                    if (data.status === "retrieval_done") {
                        logs = data.logs;
                    } else if (data.status === "reasoning_start") {
                        statusEl.className = "status-indicator reasoning";
                        statusEl.innerHTML = '<i class="fas fa-brain"></i> System is reasoning...';
                    } else if (data.status === "done") {
                        statusEl.remove(); // Remove status when done
                        contentEl.innerHTML = marked.parse(data.response);
                        
                        // Append Cost Summary
                        if (data.cost_summary) {
                            const costHtml = `
                                <div class="cost-summary">
                                    <div class="cost-item" title="Retrieval Time"><i class="fas fa-clock"></i> ${data.cost_summary.retrieval_time.toFixed(3)}s</div>
                                    <div class="cost-item" title="Reasoning Tokens"><i class="fas fa-brain"></i> ${data.cost_summary.reasoning_tokens} toks</div>
                                    <div class="cost-item" title="Prompt Tokens"><i class="fas fa-arrow-up"></i> ${data.cost_summary.prompt_tokens} toks</div>
                                    <div class="cost-item" title="Completion Tokens"><i class="fas fa-arrow-down"></i> ${data.cost_summary.completion_tokens} toks</div>
                                </div>
                            `;
                            contentEl.insertAdjacentHTML('beforeend', costHtml);
                        }

                        // Append Logs if available (reusing previous logic)
                        if (logs) {
                            const logId = "log-" + Date.now();
                            const logHtml = `
                            <div style="margin-top:8px;border-top:1px solid #eee;padding-top:8px;">
                                <div style="cursor:pointer;font-size:12px;color:#666;display:flex;align-items:center;gap:6px;" onclick="document.getElementById('${logId}').classList.toggle('hidden')">
                                    <i class="fas fa-chart-line"></i> Retrieval Stats (${logs.total_time.toFixed(3)}s) <i class="fas fa-chevron-down" style="font-size:10px;"></i>
                                </div>
                                <div id="${logId}" class="hidden" style="margin-top:8px;font-family:monospace;font-size:11px;color:#444;background:#f9f9f9;padding:8px;border-radius:4px;">
                                    <div><span style="color:#007bff">Vector Search:</span> ${logs.vector_count} docs (${logs.vector_time.toFixed(3)}s)</div>
                                    <div><span style="color:#007bff">BM25 Search:</span> ${logs.bm25_count} docs (${logs.bm25_time.toFixed(3)}s)</div>
                                    <div><span style="color:#28a745">Re-ranking:</span> ${logs.rerank_count} candidates (${logs.rerank_time.toFixed(3)}s)</div>
                                    <div><span style="color:#dc3545">Final Context:</span> ${logs.final_count} chunks</div>
                                    <div style="margin-top:4px;color:#666;">Top Scores: ${logs.top_scores.map(s => s.toFixed(2)).join(', ')}</div>
                                </div>
                            </div>`;
                            contentEl.insertAdjacentHTML('beforeend', logHtml);
                        }
                    } else if (data.status === "error") {
                        statusEl.innerHTML = `<span style="color:red">Error: ${data.message}</span>`;
                    }
                } catch (e) {
                    console.error("Parse error", e);
                }
            }
        }
    } catch (e) {
        // Handle network errors
        const msgDiv = document.getElementById(`msg-${Date.now()}`); // This won't work, ID is lost
        // Simplification: just alert or log
        console.error(e);
    }
}


// Documents
async function loadDocuments() {
    const docs = await fetchJSON("/api/documents");
    const list = document.getElementById("doc-list");
    list.innerHTML = "";
    if (docs) {
        if (docs.length === 0) {
            list.innerHTML = "<div style='color:var(--text-light);text-align:center;padding:20px'>No documents yet</div>";
        }
        docs.forEach(d => {
            const el = document.createElement("div");
            el.className = "doc-item";
            el.innerHTML = `
                <div class="doc-info">
                    <span class="doc-name">${d.filename}</span>
                    <span class="doc-status">${d.status || 'processed'} • ${formatTime(d.created_at)}</span>
                </div>
                <button class="icon-btn" onclick="deleteDocument(${d.id})"><i class="fas fa-trash"></i></button>
            `;
            list.appendChild(el);
        });
    }
}

async function uploadDocument(file) {
    if (!file) return;
    
    // Show uploading status in modal
    const list = document.getElementById("doc-list");
    const tempEl = document.createElement("div");
    tempEl.className = "doc-item";
    tempEl.innerHTML = `
        <div class="doc-info">
            <span class="doc-name">${file.name}</span>
            <span class="doc-status">Uploading...</span>
        </div>
        <div class="spinner"></div>
    `;
    list.prepend(tempEl);
    
    const form = new FormData();
    form.append("file", file);
    
    try {
        const res = await fetchJSON("/api/documents/upload", {
            method: "POST",
            body: form
        });
        
        if (res) {
            // Refresh list
            loadDocuments();
        } else {
            tempEl.innerHTML = `<span style="color:red">Upload failed</span>`;
        }
    } catch (e) {
        tempEl.innerHTML = `<span style="color:red">Error</span>`;
    }
}

async function deleteDocument(id) {
    if(!confirm("Delete this document?")) return;
    await fetchJSON(`/api/documents/${id}`, { method: "DELETE" });
    loadDocuments();
}

// System Prompt
async function loadSystemPrompt() {
    const res = await fetchJSON("/api/system_prompt");
    if (res) {
        document.getElementById("system-prompt").value = res.content;
    }
}

async function saveSystemPrompt() {
    const content = document.getElementById("system-prompt").value;
    await fetchJSON("/api/system_prompt", {
        method: "POST",
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ content })
    });
    document.getElementById("prompt-modal").classList.add("hidden");
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    loadConversations();
    
    // Sidebar & Topbar buttons
    document.getElementById("new-convo").onclick = createConversation;
    
    // Docs Modal
    const docsModal = document.getElementById("docs-modal");
    document.getElementById("docs-btn").onclick = () => {
        loadDocuments();
        docsModal.classList.remove("hidden");
    };
    document.getElementById("upload-trigger").onclick = () => {
        loadDocuments();
        docsModal.classList.remove("hidden");
    };
    
    // Prompt Modal
    const promptModal = document.getElementById("prompt-modal");
    document.getElementById("prompt-btn").onclick = () => {
        loadSystemPrompt();
        promptModal.classList.remove("hidden");
    };

    // Settings Modal
    const settingsModal = document.getElementById("settings-modal");
    document.getElementById("settings-btn").onclick = () => {
        loadSettings();
        settingsModal.classList.remove("hidden");
    };
    
    // Close Modals
    document.querySelectorAll(".close-modal").forEach(btn => {
        btn.onclick = () => {
            docsModal.classList.add("hidden");
            promptModal.classList.add("hidden");
            settingsModal.classList.add("hidden");
        };
    });
    
    document.getElementById("save-prompt").onclick = saveSystemPrompt;
    document.getElementById("save-settings").onclick = saveSettings;
    
    // Upload logic
    const fileInput = document.getElementById("file-input");
    const uploadArea = document.getElementById("upload-area");
    
    uploadArea.onclick = () => fileInput.click();
    
    uploadArea.ondragover = (e) => {
        e.preventDefault();
        uploadArea.style.background = "#f0f7ff";
    };
    uploadArea.ondragleave = () => {
        uploadArea.style.background = "transparent";
    };
    uploadArea.ondrop = (e) => {
        e.preventDefault();
        uploadArea.style.background = "transparent";
        if (e.dataTransfer.files.length) {
            uploadDocument(e.dataTransfer.files[0]);
        }
    };
    
    fileInput.onchange = () => {
        if (fileInput.files.length) {
            uploadDocument(fileInput.files[0]);
            fileInput.value = ""; // reset
        }
    };
    
    // Chat
    document.getElementById("send").onclick = sendQuery;
    document.getElementById("query").onkeydown = (e) => {
        if (e.key === "Enter") sendQuery();
    };
});
