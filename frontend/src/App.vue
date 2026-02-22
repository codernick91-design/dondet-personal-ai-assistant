<template>
  <div class="app-container">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: isSidebarCollapsed }">
      <div class="sidebar-top">
        <button class="menu-btn" @click="toggleSidebar">
          <i class="fas fa-bars"></i>
        </button>
        <button class="new-chat-btn" @click="createNewChat">
          <i class="fas fa-plus"></i>
          <span v-if="!isSidebarCollapsed">New chat</span>
        </button>
      </div>

      <div class="sidebar-section scrollable" v-if="!isSidebarCollapsed">
        <div class="section-title">Recent</div>
        <div class="history-list">
          <div 
            v-for="conv in conversations" 
            :key="conv.id" 
            class="history-item" 
            :class="{ active: currentConvId === conv.id }"
            @click="loadConversation(conv.id)"
          >
            <i class="far fa-message"></i>
            <span class="history-title">{{ conv.title }}</span>
            <button class="delete-conv-btn" @click="deleteConversation(conv.id, $event)" v-if="currentConvId === conv.id">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="footer-item" @click="showDocsModal = true">
          <i class="fas fa-gem"></i>
          <span v-if="!isSidebarCollapsed">Document</span>
        </div>
        <div class="footer-item" @click="showSettingsModal = true">
          <i class="fas fa-cog"></i>
          <span v-if="!isSidebarCollapsed">Settings</span>
        </div>
        <div class="location-info" v-if="!isSidebarCollapsed">
          <span class="dot"></span> Shanghai, China
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="main-content">
      <header class="topbar">
        <div class="header-title">dondet</div>
        <div class="header-actions">
          <button class="upgrade-btn" @click="showSystemPromptModal = true">
            <i class="fas fa-sliders-h"></i> Customize
          </button>
          <div class="user-avatar">D</div>
        </div>
      </header>

      <div class="chat-area" ref="chatArea">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="greeting">
            <span class="gradient-text">Hello, Dong</span>
            <div class="sub-greeting">How can I help you today?</div>
          </div>
          <div class="suggestions">
            <div class="suggestion-card" @click="setInput('Explain quantum computing')">
              <p>Explain quantum computing</p>
              <div class="card-icon"><i class="fas fa-lightbulb"></i></div>
            </div>
            <div class="suggestion-card" @click="setInput('Suggest a dinner recipe')">
              <p>Suggest a dinner recipe</p>
              <div class="card-icon"><i class="fas fa-utensils"></i></div>
            </div>
            <div class="suggestion-card" @click="setInput('Plan a trip to Paris')">
              <p>Plan a trip to Paris</p>
              <div class="card-icon"><i class="fas fa-plane"></i></div>
            </div>
            <div class="suggestion-card" @click="setInput('Write a Python script to scrape a website')">
              <p>Write a code snippet</p>
              <div class="card-icon"><i class="fas fa-code"></i></div>
            </div>
          </div>
        </div>
        
        <div v-for="(msg, index) in messages" :key="index" class="message" :class="msg.role">
          <div class="msg-avatar" v-if="msg.role === 'assistant'">
            <i class="fas fa-sparkles" style="color: #4285f4; font-size: 24px;"></i>
          </div>
          
          <div class="msg-content">
            <div class="sender-name" v-if="msg.role === 'assistant'">dondet</div>
            
            <!-- Status Indicator -->
            <div v-if="msg.role === 'assistant' && msg.status" class="status-indicator" :class="msg.statusType">
              <i :class="msg.statusIcon" v-if="isLoading.valueOf"></i> {{ msg.statusText }}
            </div>
            
            <!-- Message Text -->
            <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
            
            <!-- Footer Actions -->
            <div class="msg-footer" v-if="msg.role === 'assistant' && !msg.status">
              <!-- Logs Toggle -->
              <div v-if="msg.logs" class="logs-toggle" @click="msg.showLogs = !msg.showLogs">
                <i class="fas fa-chart-bar"></i> Stats
              </div>
            </div>

            <!-- Retrieval Logs -->
            <div v-if="msg.logs && msg.showLogs" class="retrieval-logs">
               <div class="logs-content">
                <div><span class="log-label blue">Vector Search:</span> {{ msg.logs.vector_count }} docs ({{ msg.logs.vector_time.toFixed(3) }}s)</div>
                <div><span class="log-label blue">BM25 Search:</span> {{ msg.logs.bm25_count }} docs ({{ msg.logs.bm25_time.toFixed(3) }}s)</div>
                <div><span class="log-label green">Re-ranking:</span> {{ msg.logs.rerank_count }} candidates ({{ msg.logs.rerank_time.toFixed(3) }}s)</div>
                <div><span class="log-label red">Final Context:</span> {{ msg.logs.final_count }} chunks</div>
                <div class="top-scores">Top Scores: {{ msg.logs.top_scores.map(s => s.toFixed(2)).join(', ') }}</div>
              </div>
            </div>
            
            <!-- Cost Summary -->
            <div v-if="msg.costSummary" class="cost-summary">
              <span>{{ msg.costSummary.retrieval_time.toFixed(3) }}s</span>
              <span>{{ msg.costSummary.completion_tokens }} tokens</span>
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="input-wrapper">
          <div class="input-container">
            <button class="attach-btn" @click="showDocsModal = true"><i class="fas fa-plus"></i></button>
            <textarea 
              v-model="inputQuery" 
              @keydown.enter.prevent="handleSendMessage"
              @input="adjustHeight"
              placeholder="Enter a prompt here" 
              rows="1"
              ref="inputBox"
            ></textarea>
            <button class="send-btn" @click="isLoading.valueOf === true? stopGeneration() : handleSendMessage()" :disabled="!isLoading.valueOf && !inputQuery.trim()">
              <i class="fas" :class="isLoading.valueOf === true? 'fa-stop' : 'fa-paper-plane'"></i>
            </button>
          </div>
          <div class="footer-text">dondet may display inaccurate info, including about people, so double-check its responses.</div>
        </div>
      </div>
    </main>

    <!-- Modals -->
    <div v-if="showDocsModal" class="modal-overlay" @click.self="showDocsModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Documents</h3>
          <button @click="showDocsModal = false"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
          <div class="upload-area" @drop.prevent="handleDrop" @dragover.prevent @click="$refs.fileInput.click()">
            <i class="fas fa-cloud-upload-alt"></i>
            <p>Drag & drop files here or click to upload</p>
            <input type="file" ref="fileInput" @change="handleFileUpload" multiple hidden>
          </div>
          <div class="doc-list">
            <div v-for="doc in documents" :key="doc.id" class="doc-item">
              <div class="doc-info">
                <span class="doc-name">{{ doc.filename }}</span>
                <span class="doc-meta">{{ doc.status }} • {{ formatTime(doc.created_at) }}</span>
              </div>
              <button class="delete-btn" @click="deleteDocument(doc.id)"><i class="fas fa-trash"></i></button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Settings Modal -->
    <div v-if="showSettingsModal" class="modal-overlay" @click.self="showSettingsModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Settings</h3>
          <button @click="showSettingsModal = false"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
           <div class="form-group">
             <label>LM Studio API Key (Optional)</label>
             <input v-model="apiKey" type="password" placeholder="sk-...">
           </div>
           <button class="save-btn" @click="saveSettings">Save</button>
        </div>
      </div>
    </div>

    <!-- System Prompt Modal -->
    <div v-if="showSystemPromptModal" class="modal-overlay" @click.self="showSystemPromptModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>System Prompt</h3>
          <button @click="showSystemPromptModal = false"><i class="fas fa-times"></i></button>
        </div>
        <div class="modal-body">
           <textarea v-model="systemPrompt" rows="10" class="full-width" placeholder="Enter system prompt..."></textarea>
           <button class="save-btn" @click="saveSystemPrompt">Update</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { marked } from 'marked';
import axios from 'axios';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css'; // Light theme
import { useChat } from './composables/useChat';

// Configure marked with highlight.js
marked.setOptions({
  highlight: function(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  },
  langPrefix: 'hljs language-'
});

// Use Composable
const { 
  messages, 
  conversations, 
  currentConvId, 
  isLoading, 
  loadConversations, 
  createNewChat, 
  deleteConversation, 
  loadConversation, 
  sendMessage, 
  stopGeneration 
} = useChat();

// UI State
const isSidebarCollapsed = ref(false);
const showDocsModal = ref(false);
const showSettingsModal = ref(false);
const showSystemPromptModal = ref(false);
const inputQuery = ref('');
const documents = ref([]);
const apiKey = ref(localStorage.getItem('lm_api_key') || '');
const systemPrompt = ref('');
const chatArea = ref(null);
const inputBox = ref(null);

// Lifecycle
onMounted(() => {
  loadConversations();
  loadDocuments();
  loadSystemPrompt();
});

// Watchers
watch(messages, () => {
  nextTick(() => scrollToBottom());
}, { deep: true });

// UI Actions
const toggleSidebar = () => isSidebarCollapsed.value = !isSidebarCollapsed.value;

const scrollToBottom = () => {
  if (chatArea.value) {
    chatArea.value.scrollTop = chatArea.value.scrollHeight;
  }
};

const setInput = (text) => {
  inputQuery.value = text;
  nextTick(() => adjustHeight());
};

const adjustHeight = () => {
  if (inputBox.value) {
    inputBox.value.style.height = 'auto';
    inputBox.value.style.height = Math.min(inputBox.value.scrollHeight, 200) + 'px';
  }
};

const handleSendMessage = () => {
  const q = inputQuery.value.trim();
  if (!q) return;
  sendMessage(q, apiKey.value);
  inputQuery.value = '';
  if (inputBox.value) inputBox.value.style.height = 'auto';
};

const formatTime = (ts) => new Date(ts * 1000).toLocaleString();

const renderMarkdown = (text) => marked.parse(text || '');

// Document API Calls (kept in component for now as they are simple resource management)
const loadDocuments = async () => {
  try {
    const res = await axios.get('/api/documents');
    documents.value = res.data;
  } catch (e) { console.error(e); }
};

const deleteDocument = async (id) => {
  if(!confirm('Delete this document?')) return;
  try {
    await axios.delete(`/api/documents/${id}`);
    loadDocuments();
  } catch (e) { console.error(e); }
};

const handleFileUpload = async (e) => {
  const files = e.target.files;
  for (let file of files) {
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post('/api/documents/upload', formData);
    } catch (e) { console.error(e); }
  }
  loadDocuments();
};

const handleDrop = async (e) => {
  const files = e.dataTransfer.files;
  for (let file of files) {
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post('/api/documents/upload', formData);
    } catch (e) { console.error(e); }
  }
  loadDocuments();
};

const loadSystemPrompt = async () => {
  try {
    const res = await axios.get('/api/system_prompt');
    systemPrompt.value = res.data.content;
  } catch (e) { console.error(e); }
};

const saveSystemPrompt = async () => {
  try {
    await axios.post('/api/system_prompt', new URLSearchParams({ content: systemPrompt.value }));
    showSystemPromptModal.value = false;
  } catch (e) { console.error(e); }
};

const saveSettings = () => {
  if (apiKey.value) localStorage.setItem('lm_api_key', apiKey.value);
  else localStorage.removeItem('lm_api_key');
  showSettingsModal.value = false;
};
</script>

<style>
:root {
  --primary: #1a73e8;
  --bg-sidebar: #f0f4f9;
  --bg-main: #ffffff;
  --text-main: #1f1f1f;
  --text-sidebar: #444746;
  --border: #e0e3e7;
  --msg-user-bg: #f0f4f9;
  --gradient-start: #4285f4;
  --gradient-end: #d96570;
}

* { box-sizing: border-box; }
body { margin: 0; font-family: 'Google Sans', 'Inter', sans-serif; background: var(--bg-main); color: var(--text-main); height: 100vh; overflow: hidden; }

.app-container { display: flex; height: 100vh; }

/* Sidebar */
.sidebar {
  width: 280px;
  background: var(--bg-sidebar);
  color: var(--text-sidebar);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 12px;
  border-right: none;
}
.sidebar.collapsed { width: 72px; padding: 12px 8px; }

.sidebar-top { display: flex; flex-direction: column; gap: 16px; margin-bottom: 20px; }
.menu-btn { align-self: flex-start; background: none; border: none; padding: 12px; border-radius: 50%; cursor: pointer; color: var(--text-sidebar); margin-left: 4px; }
.menu-btn:hover { background: rgba(0,0,0,0.05); }

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #dde3ea;
  border: none;
  color: #1f1f1f;
  border-radius: 24px;
  cursor: pointer;
  width: fit-content;
  font-family: 'Google Sans', sans-serif;
  font-weight: 500;
  font-size: 14px;
  transition: background 0.2s, box-shadow 0.2s;
  min-height: 48px;
}
.sidebar.collapsed .new-chat-btn { width: 40px; height: 40px; padding: 0; justify-content: center; border-radius: 50%; min-height: 40px; }
.new-chat-btn:hover { background: #d3dbe5; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }

.scrollable { flex: 1; overflow-y: auto; padding-right: 4px; }
/* Custom Scrollbar */
.scrollable::-webkit-scrollbar { width: 6px; }
.scrollable::-webkit-scrollbar-thumb { background: #c4c7c5; border-radius: 3px; }
.scrollable::-webkit-scrollbar-track { background: transparent; }

.section-title { font-size: 14px; font-weight: 500; margin: 16px 16px 8px; color: #1f1f1f; }

.history-list { display: flex; flex-direction: column; gap: 2px; }
.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 20px;
  cursor: pointer;
  color: var(--text-sidebar);
  font-size: 14px;
  height: 36px;
  transition: background 0.1s;
}
.history-item:hover { background: #e0e5eb; color: #1f1f1f; }
.history-item.active { background: #c2e7ff; color: #001d35; font-weight: 500; }
.history-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Delete Button */
.delete-conv-btn {
  background: none;
  border: none;
  color: #757575;
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  display: none; /* Hidden by default */
  margin-left: auto;
}
.delete-conv-btn:hover {
  background: #d3dbe5;
  color: #1f1f1f;
}
.history-item:hover .delete-conv-btn {
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-footer { margin-top: auto; padding-top: 10px; }
.footer-item { display: flex; align-items: center; gap: 12px; padding: 10px 16px; cursor: pointer; border-radius: 20px; color: var(--text-sidebar); font-size: 14px; height: 44px; }
.footer-item:hover { background: #e0e5eb; color: #1f1f1f; }
.location-info { font-size: 12px; color: #444746; padding: 16px; display: flex; align-items: center; gap: 6px; }
.dot { width: 6px; height: 6px; background: #444746; border-radius: 50%; }

/* Main Content */
.main-content { flex: 1; display: flex; flex-direction: column; background: var(--bg-main); position: relative; border-radius: 24px; margin: 12px 12px 12px 0; box-shadow: 0 0 15px rgba(0,0,0,0.02); z-index: 2; overflow: hidden; border: 1px solid #e0e3e7; }
.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.header-title { font-family: 'Google Sans', sans-serif; font-size: 22px; color: #444746; display: flex; align-items: center; gap: 4px; }
.header-title::after { content: "▼"; font-size: 12px; margin-left: 4px; color: #444746; }

.header-actions { display: flex; align-items: center; gap: 16px; }
.upgrade-btn {
  background: linear-gradient(90deg, #d3e3fd 0%, #e8def8 100%);
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  color: #001d35;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.user-avatar { width: 32px; height: 32px; background: #a50e0e; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 500; }

.chat-area { flex: 1; overflow-y: auto; padding-bottom: 160px; max-width: 900px; margin: 0 auto; width: 100%; padding-left: 20px; padding-right: 20px; }

/* Empty State */
.empty-state { display: flex; flex-direction: column; height: 100%; padding-top: 10vh; max-width: 800px; margin: 0 auto; }
.greeting { margin-bottom: 48px; }
.gradient-text { 
  font-size: 56px; 
  font-weight: 500; 
  background: linear-gradient(90deg, #4285f4 0%, #9b72cb 50%, #d96570 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: block;
  margin-bottom: 8px;
  font-family: 'Google Sans', sans-serif;
  letter-spacing: -1px;
  line-height: 1.2;
}
.sub-greeting { font-size: 56px; font-weight: 500; color: #c4c7c5; font-family: 'Google Sans', sans-serif; letter-spacing: -1px; line-height: 1.2; }

.suggestions { display: flex; gap: 16px; overflow-x: auto; padding-bottom: 10px; }
.suggestion-card {
  background: #f0f4f9;
  border-radius: 12px;
  padding: 16px;
  width: 200px;
  height: 200px;
  flex-shrink: 0;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
  display: flex;
  flex-direction: column;
}
.suggestion-card:hover { background: #e0e5eb; }
.suggestion-card p { margin: 0; font-size: 16px; color: #1f1f1f; line-height: 1.4; }
.card-icon { position: absolute; bottom: 16px; right: 16px; background: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }

/* Messages */
.message { display: flex; gap: 20px; padding: 24px 0; }
.message.user { flex-direction: row-reverse; }
.message.user .msg-content { background: var(--msg-user-bg); padding: 12px 20px; border-radius: 20px 4px 20px 20px; max-width: 80%; }
.message.assistant .msg-content { max-width: 100%; }

.msg-avatar { width: 32px; height: 32px; flex-shrink: 0; margin-top: 4px; }
.msg-avatar img { width: 100%; height: 100%; object-fit: contain; animation: rotate 4s linear infinite; }
@keyframes rotate { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.msg-content { flex: 1; }
.sender-name { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #1f1f1f; }

.status-indicator { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #444746; margin-bottom: 12px; }
.status-indicator i { font-size: 16px; }

.markdown-body { font-size: 16px; line-height: 1.6; color: #1f1f1f; }
.markdown-body p { margin-bottom: 16px; }
.markdown-body pre { background: #f0f4f9; padding: 16px; border-radius: 12px; overflow-x: auto; margin-bottom: 16px; }
.markdown-body code { font-family: 'Roboto Mono', monospace; font-size: 14px; }

.msg-footer { display: flex; gap: 8px; margin-top: 12px; }
.icon-btn-small { background: none; border: none; color: #444746; cursor: pointer; padding: 6px; border-radius: 50%; }
.icon-btn-small:hover { background: #f0f4f9; color: #1f1f1f; }
.logs-toggle { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #444746; cursor: pointer; padding: 4px 8px; border-radius: 8px; margin-left: auto; }
.logs-toggle:hover { background: #f0f4f9; }

.retrieval-logs { margin-top: 12px; background: #f8f9fa; border-radius: 8px; padding: 12px; font-size: 12px; border: 1px solid #e0e3e7; }
.logs-content div { margin-bottom: 4px; }
.log-label { font-weight: 600; }
.cost-summary { margin-top: 8px; font-size: 11px; color: #757575; display: flex; gap: 12px; }

/* Input Area */
.input-area { position: absolute; bottom: 0; left: 0; right: 0; background: #ffffff; padding: 0 20px 24px; display: flex; justify-content: center; z-index: 10; }
.input-wrapper { width: 100%; max-width: 800px; }
.input-container {
  background: #f0f4f9;
  border-radius: 36px;
  padding: 10px 16px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  min-height: 56px;
  transition: background 0.2s;
  border: 1px solid transparent;
}
.input-container:focus-within { background: #e9eef6; border-color: #e0e3e7; }

.attach-btn, .mic-btn { width: 40px; height: 40px; border-radius: 50%; border: none; background: none; cursor: pointer; color: #1f1f1f; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.attach-btn:hover, .mic-btn:hover { background: rgba(0,0,0,0.05); }

textarea { flex: 1; background: transparent; border: none; resize: none; outline: none; padding: 10px 0; font-family: inherit; font-size: 16px; color: #1f1f1f; max-height: 200px; line-height: 1.5; }

.send-btn { width: 40px; height: 40px; border-radius: 50%; border: none; background: transparent; cursor: pointer; color: #1f1f1f; display: flex; align-items: center; justify-content: center; font-size: 18px; margin-bottom: 0; flex-shrink: 0; }
.send-btn:hover:not(:disabled) { background: rgba(0,0,0,0.05); }
.send-btn:disabled { color: #8e918f; cursor: default; }

.footer-text { text-align: center; font-size: 11px; color: #444746; margin-top: 12px; }

/* Modals */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #ffffff; width: 500px; border-radius: 24px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); padding: 0; overflow: hidden; }
.modal-header { padding: 20px 24px; border-bottom: 1px solid #e0e3e7; display: flex; justify-content: space-between; align-items: center; }
.modal-header h3 { font-family: 'Google Sans', sans-serif; font-weight: 500; margin: 0; font-size: 20px; }
.modal-header button { background: none; border: none; font-size: 20px; cursor: pointer; color: #444746; }
.modal-body { padding: 24px; }

.upload-area { border: 2px dashed #c4c7c5; border-radius: 12px; padding: 40px; text-align: center; color: #444746; margin-bottom: 24px; cursor: pointer; transition: background 0.2s; }
.upload-area:hover { background: #f0f4f9; border-color: #1a73e8; }
.doc-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #e0e3e7; }
.doc-name { font-weight: 500; color: #1f1f1f; display: block; }
.doc-meta { font-size: 12px; color: #444746; }

.save-btn { background: #1a73e8; color: white; border: none; padding: 10px 24px; border-radius: 20px; font-weight: 500; cursor: pointer; margin-top: 16px; float: right; }
.save-btn:hover { background: #1557b0; }
.form-group label { color: #1f1f1f; margin-bottom: 8px; display: block; font-size: 14px; font-weight: 500; }
.form-group input { width: 100%; background: #f0f4f9; border: 1px solid transparent; padding: 12px; border-radius: 8px; transition: border 0.2s; font-family: inherit; }
.form-group input:focus { border-color: #1a73e8; outline: none; background: #ffffff; }
.full-width { width: 100%; background: #f0f4f9; border: 1px solid transparent; padding: 12px; border-radius: 8px; font-family: inherit; resize: vertical; }
.full-width:focus { border-color: #1a73e8; outline: none; background: #ffffff; }
</style>
