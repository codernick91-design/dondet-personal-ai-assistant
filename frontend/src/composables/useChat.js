import { ref, nextTick } from 'vue';
import axios from 'axios';

export function useChat() {
  const messages = ref([]);
  const conversations = ref([]);
  const currentConvId = ref(null);
  const isLoading = ref(false);
  const abortController = ref(null);
  const timerInterval = ref(null);

  const loadConversations = async () => {
    try {
      const res = await axios.get('/api/conversations');
      conversations.value = res.data;
    } catch (e) { console.error(e); }
  };

  const createNewChat = async () => {
    currentConvId.value = null;
    messages.value = [];
  };

  const deleteConversation = async (id) => {
    if(!confirm('Delete this conversation?')) return;
    try {
      await axios.delete(`/api/conversations/${id}`);
      if (currentConvId.value === id) {
        currentConvId.value = null;
        messages.value = [];
      }
      loadConversations();
    } catch (e) { console.error(e); }
  };

  const loadConversation = async (id) => {
    try {
      currentConvId.value = id;
      const res = await axios.get(`/api/conversations/${id}`);
      messages.value = res.data.map(m => ({
        role: m.role,
        content: m.content,
      }));
    } catch (e) { console.error(e); }
  };

  const stopGeneration = () => {
    if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
    }
    if (timerInterval.value) {
      clearInterval(timerInterval.value);
      timerInterval.value = null;
    }
    isLoading.value = false;
    
    // Update the last assistant message if it was loading
    if (messages.value.length > 0) {
      const lastMsg = messages.value[messages.value.length - 1];
      if (lastMsg.role === 'assistant' && lastMsg.status) {
        lastMsg.status = false;
        if (!lastMsg.content) {
          lastMsg.content = 'Generation stopped by user.';
        }
      }
    }
  };

  const sendMessage = async (query, apiKey) => {
    if (!query.trim() || isLoading.value) return;

    if (!currentConvId.value) {
      try {
        const res = await axios.post('/api/conversations', new URLSearchParams({ title: 'New Conversation' }));
        currentConvId.value = res.data.id;
        await loadConversations();
      } catch(e) { console.error(e); return; }
    }

    // Add User Message
    messages.value.push({ role: 'user', content: query });
    isLoading.value = true;

    // Add Placeholder Assistant Message
    messages.value.push({
      role: 'assistant',
      content: '',
      status: true,
      statusType: 'loading',
      statusText: '0.0s',
      statusIcon: 'fas fa-spinner fa-spin',
      logs: null,
      costSummary: null,
      showLogs: false
    });
    const assistantMsg = messages.value[messages.value.length - 1];

    const startTime = performance.now();
    timerInterval.value = setInterval(() => {
      const elapsed = (performance.now() - startTime) / 1000;
      assistantMsg.statusText = `${elapsed.toFixed(1)}s`;
    }, 100);

    abortController.value = new AbortController();

    try {
      const form = new URLSearchParams();
      form.append('conversation_id', currentConvId.value);
      form.append('query', query);
      if (apiKey) form.append('api_key', apiKey);

      const response = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
        signal: abortController.value.signal
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let isStreamDone = false;

      const processLine = (line) => {
        if (!line) return;
        try {
          const data = JSON.parse(line);
          if (data.status === 'retrieval_done') {
            assistantMsg.logs = data.logs;
          } else if (data.status === 'reasoning_start') {
             // Do nothing for status text, keep loading
          } else if (data.status === 'chunk') {
             assistantMsg.content += data.content;
          } else if (data.status === 'done') {
            assistantMsg.status = false; // Hide status completely when done
            assistantMsg.content = data.response; 
            assistantMsg.costSummary = data.cost_summary;
            loadConversations(); 
            if (timerInterval.value) clearInterval(timerInterval.value);
            isStreamDone = true;
          } else if (data.status === 'error') {
            assistantMsg.content = `Error: ${data.message}`;
            assistantMsg.status = false;
            if (timerInterval.value) clearInterval(timerInterval.value);
            isStreamDone = true;
          }
        } catch (e) { console.error(e); }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done || isStreamDone) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        for (let i = 0; i < lines.length - 1; i++) {
          processLine(lines[i].trim());
          if (isStreamDone) break;
        }
        buffer = lines[lines.length - 1];
      }

      if (buffer.trim() && !isStreamDone) {
        processLine(buffer.trim());
      }
      
      if (!isStreamDone && assistantMsg.status) {
         if (!assistantMsg.content) {
           assistantMsg.content = 'Error: Stream ended unexpectedly.';
         }
         assistantMsg.status = false;
         if (timerInterval.value) clearInterval(timerInterval.value);
      }

    } catch (e) {
      if (e.name === 'AbortError') {
        console.log('Fetch aborted');
      } else {
        console.error(e);
        assistantMsg.content = 'Error connecting to server.';
      }
      assistantMsg.status = false;
      if (timerInterval.value) clearInterval(timerInterval.value);
    } finally {
      isLoading.value = false;
      abortController.value = null;
      if (timerInterval.value) {
        clearInterval(timerInterval.value);
        timerInterval.value = null;
      }
    }
  };

  return {
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
  };
}
