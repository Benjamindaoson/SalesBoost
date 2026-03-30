/**
 * SalesBoost Copilot SDK
 *
 * Embeddable widget for real-time sales assistance.
 * Drop into any webpage to get AI-powered talk-track suggestions.
 *
 * Usage:
 *   <script src="https://your-domain/sdk/copilot.js"></script>
 *   <script>
 *     SalesBoost.init({ apiKey: "sk-xxx", dealId: "deal-123" });
 *     SalesBoost.onCustomerMessage("客户说的话");
 *   </script>
 */
(function (window, document) {
  'use strict';

  var API_BASE = '';
  var config = {};
  var panelEl = null;
  var contentEl = null;
  var isOpen = false;

  // -------------------------------------------------------------------------
  // Styles
  // -------------------------------------------------------------------------
  var CSS = '\
    #sb-copilot-panel {\
      position: fixed;\
      top: 0;\
      width: 360px;\
      height: 100vh;\
      background: #ffffff;\
      box-shadow: -4px 0 24px rgba(0,0,0,0.12);\
      z-index: 999999;\
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\
      transition: transform 0.3s ease;\
      display: flex;\
      flex-direction: column;\
    }\
    #sb-copilot-panel.sb-right { right: 0; transform: translateX(100%); }\
    #sb-copilot-panel.sb-left { left: 0; transform: translateX(-100%); }\
    #sb-copilot-panel.sb-open { transform: translateX(0); }\
    #sb-copilot-header {\
      padding: 16px;\
      background: linear-gradient(135deg, #6366f1, #8b5cf6);\
      color: white;\
      display: flex;\
      align-items: center;\
      justify-content: space-between;\
    }\
    #sb-copilot-header h3 { margin: 0; font-size: 14px; font-weight: 600; }\
    #sb-copilot-close {\
      background: rgba(255,255,255,0.2);\
      border: none;\
      color: white;\
      width: 28px;\
      height: 28px;\
      border-radius: 50%;\
      cursor: pointer;\
      font-size: 16px;\
      display: flex;\
      align-items: center;\
      justify-content: center;\
    }\
    #sb-copilot-content {\
      flex: 1;\
      overflow-y: auto;\
      padding: 16px;\
    }\
    .sb-suggestion {\
      background: #f5f3ff;\
      border: 1px solid #e0e7ff;\
      border-radius: 12px;\
      padding: 12px;\
      margin-bottom: 12px;\
    }\
    .sb-suggestion-text { font-size: 13px; color: #1f2937; line-height: 1.5; }\
    .sb-suggestion-meta {\
      display: flex;\
      align-items: center;\
      justify-content: space-between;\
      margin-top: 8px;\
    }\
    .sb-tactic {\
      font-size: 11px;\
      background: #e0e7ff;\
      color: #4338ca;\
      padding: 2px 8px;\
      border-radius: 10px;\
    }\
    .sb-copy-btn {\
      font-size: 11px;\
      background: none;\
      border: 1px solid #c7d2fe;\
      color: #6366f1;\
      padding: 4px 10px;\
      border-radius: 6px;\
      cursor: pointer;\
    }\
    .sb-copy-btn:hover { background: #eef2ff; }\
    #sb-copilot-input-area {\
      padding: 12px 16px;\
      border-top: 1px solid #e5e7eb;\
      display: flex;\
      gap: 8px;\
    }\
    #sb-copilot-input {\
      flex: 1;\
      border: 1px solid #d1d5db;\
      border-radius: 8px;\
      padding: 8px 12px;\
      font-size: 13px;\
      outline: none;\
    }\
    #sb-copilot-input:focus { border-color: #6366f1; }\
    #sb-copilot-send {\
      background: #6366f1;\
      color: white;\
      border: none;\
      border-radius: 8px;\
      padding: 8px 16px;\
      font-size: 13px;\
      cursor: pointer;\
    }\
    #sb-copilot-send:hover { background: #4f46e5; }\
    #sb-copilot-toggle {\
      position: fixed;\
      bottom: 24px;\
      width: 52px;\
      height: 52px;\
      border-radius: 50%;\
      background: linear-gradient(135deg, #6366f1, #8b5cf6);\
      color: white;\
      border: none;\
      box-shadow: 0 4px 16px rgba(99,102,241,0.4);\
      cursor: pointer;\
      z-index: 999998;\
      font-size: 20px;\
      display: flex;\
      align-items: center;\
      justify-content: center;\
    }\
    #sb-copilot-toggle.sb-right { right: 24px; }\
    #sb-copilot-toggle.sb-left { left: 24px; }\
    .sb-loading {\
      text-align: center;\
      padding: 20px;\
      color: #9ca3af;\
      font-size: 13px;\
    }\
  ';

  function injectStyles() {
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function createPanel() {
    var pos = config.position || 'right';

    // Toggle button
    var toggle = document.createElement('button');
    toggle.id = 'sb-copilot-toggle';
    toggle.className = 'sb-' + pos;
    toggle.innerHTML = '⚡';
    toggle.onclick = function () { togglePanel(); };
    document.body.appendChild(toggle);

    // Panel
    panelEl = document.createElement('div');
    panelEl.id = 'sb-copilot-panel';
    panelEl.className = 'sb-' + pos;
    panelEl.innerHTML = '\
      <div id="sb-copilot-header">\
        <h3>SalesBoost Copilot</h3>\
        <button id="sb-copilot-close">&times;</button>\
      </div>\
      <div id="sb-copilot-content">\
        <div style="text-align:center;padding:40px 20px;color:#9ca3af;font-size:13px;">\
          输入客户消息获取实时话术建议\
        </div>\
      </div>\
      <div id="sb-copilot-input-area">\
        <input id="sb-copilot-input" placeholder="客户说了什么..." />\
        <button id="sb-copilot-send">发送</button>\
      </div>\
    ';
    document.body.appendChild(panelEl);

    contentEl = document.getElementById('sb-copilot-content');

    document.getElementById('sb-copilot-close').onclick = function () { togglePanel(); };
    document.getElementById('sb-copilot-send').onclick = function () {
      var input = document.getElementById('sb-copilot-input');
      if (input.value.trim()) {
        SalesBoost.onCustomerMessage(input.value.trim());
        input.value = '';
      }
    };
    document.getElementById('sb-copilot-input').onkeydown = function (e) {
      if (e.key === 'Enter') {
        document.getElementById('sb-copilot-send').click();
      }
    };
  }

  function togglePanel() {
    isOpen = !isOpen;
    if (isOpen) {
      panelEl.classList.add('sb-open');
    } else {
      panelEl.classList.remove('sb-open');
    }
  }

  function renderSuggestions(suggestions) {
    var html = '';
    suggestions.forEach(function (s) {
      html += '<div class="sb-suggestion">';
      html += '<div class="sb-suggestion-text">' + escapeHtml(s.content) + '</div>';
      html += '<div class="sb-suggestion-meta">';
      html += '<span class="sb-tactic">' + escapeHtml(s.tactic) + '</span>';
      html += '<button class="sb-copy-btn" onclick="navigator.clipboard.writeText(\'' + escapeJs(s.content) + '\')">复制</button>';
      html += '</div></div>';
    });
    return html;
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function escapeJs(str) {
    return str.replace(/'/g, "\\'").replace(/\n/g, '\\n');
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------
  var SalesBoost = {
    init: function (cfg) {
      config = cfg || {};
      API_BASE = config.apiUrl || window.location.origin;
      injectStyles();
      createPanel();
    },

    onCustomerMessage: function (message) {
      if (!contentEl) return;

      // Show customer message
      contentEl.innerHTML += '<div style="text-align:right;margin-bottom:8px;">\
        <span style="background:#f3f4f6;padding:6px 12px;border-radius:12px;font-size:13px;color:#374151;">客户: ' + escapeHtml(message) + '</span>\
      </div>';
      contentEl.innerHTML += '<div class="sb-loading">AI 分析中...</div>';
      contentEl.scrollTop = contentEl.scrollHeight;

      // Call API
      var body = {
        customer_message: message,
        deal_id: config.dealId ? parseInt(config.dealId) : undefined,
        mode: config.mode || 'live',
      };

      fetch(API_BASE + '/api/v1/copilot/suggest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': config.apiKey ? 'Bearer ' + config.apiKey : '',
        },
        body: JSON.stringify(body),
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          // Remove loading
          var loadingEls = contentEl.querySelectorAll('.sb-loading');
          loadingEls.forEach(function (el) { el.remove(); });

          if (data.suggestions && data.suggestions.length > 0) {
            contentEl.innerHTML += renderSuggestions(data.suggestions);
          } else {
            contentEl.innerHTML += '<div style="color:#9ca3af;font-size:13px;padding:8px;">暂无建议</div>';
          }
          contentEl.scrollTop = contentEl.scrollHeight;

          // Auto-open panel
          if (!isOpen) togglePanel();
        })
        .catch(function (err) {
          var loadingEls = contentEl.querySelectorAll('.sb-loading');
          loadingEls.forEach(function (el) { el.remove(); });
          contentEl.innerHTML += '<div style="color:#ef4444;font-size:13px;padding:8px;">请求失败</div>';
          console.error('SalesBoost Copilot error:', err);
        });
    },

    open: function () { if (!isOpen) togglePanel(); },
    close: function () { if (isOpen) togglePanel(); },
    setDeal: function (dealId) { config.dealId = dealId; },
  };

  window.SalesBoost = SalesBoost;

})(window, document);
