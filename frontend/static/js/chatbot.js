/**
 * GrievanceAI — Chatbot Widget
 * Include this on every page. Adds a floating chat button.
 */
(function() {
  function createChatbot() {
    // Toggle button
    const toggle = document.createElement("button");
    toggle.className = "chatbot-toggle";
    toggle.innerHTML = "🤖";
    toggle.title = "Ask AI Assistant";
    toggle.onclick = () => {
      const win = document.getElementById("chatbot-window");
      win.classList.toggle("open");
      if (win.classList.contains("open")) {
        document.getElementById("chatbot-input").focus();
      }
    };

    // Window
    const window_html = `
      <div class="chatbot-window" id="chatbot-window">
        <div class="chatbot-header">
          <span>🤖 GrievanceAI Assistant</span>
          <button class="chatbot-close" onclick="document.getElementById('chatbot-window').classList.remove('open')">✕</button>
        </div>
        <div class="chatbot-messages" id="chatbot-messages">
          <div class="chatbot-msg bot">Hello! I'm your AI assistant. Ask me anything about submitting complaints, priority scoring, duplicate detection, uploads, reports, and more!</div>
        </div>
        <div class="chatbot-input-row">
          <input type="text" id="chatbot-input" placeholder="Type your question..." onkeypress="if(event.key==='Enter')sendChat()">
          <button onclick="sendChat()">Send</button>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML("beforeend", window_html);
    document.body.appendChild(toggle);
  }

  window.sendChat = async function() {
    const input = document.getElementById("chatbot-input");
    const msg = input.value.trim();
    if (!msg) return;
    const messages = document.getElementById("chatbot-messages");

    // Add user message
    messages.innerHTML += `<div class="chatbot-msg user">${escapeHtml(msg)}</div>`;
    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    // Typing indicator
    messages.innerHTML += `<div class="chatbot-msg bot" id="typing">⏳ Thinking...</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch(`/api/chatbot?query=${encodeURIComponent(msg)}`, { method: "POST" });
      const data = await res.json();
      document.getElementById("typing").remove();
      messages.innerHTML += `<div class="chatbot-msg bot">${escapeHtml(data.reply)}</div>`;
    } catch (e) {
      document.getElementById("typing").remove();
      messages.innerHTML += `<div class="chatbot-msg bot">Sorry, I couldn't process that. Please try again.</div>`;
    }
    messages.scrollTop = messages.scrollHeight;
  };

  // Initialize after DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createChatbot);
  } else {
    createChatbot();
  }
})();
