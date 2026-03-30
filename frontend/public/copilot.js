/**
 * SalesBoost Copilot SDK
 * Embeddable widget for real-time sales coaching.
 *
 * Usage:
 *   <script src="https://your-domain.com/copilot.js"></script>
 *   <script>
 *     SalesBoost.init({ apiKey: "sk-xxx", dealId: 123, baseUrl: "http://localhost:8000" });
 *     SalesBoost.onCustomerMessage("你们比竞品贵30%");
 *   </script>
 */
(function () {
  'use strict';

  var config = {
    apiKey: '',
    dealId: null,
    baseUrl: (typeof window !== 'undefined' && window.location.origin) || 'http://localhost:8000',
    methodology: 'meddpicc',
    position: 'right',
    mode: 'live',
  };

  var container = null;
  var isOpen = false;

  function createStyles() {
    var style = document.createElement('style');
    style.textContent = [
      '.sb-copilot-toggle{position:fixed;bottom:24px;right:24px;width:48px;height:48px;border-radius:50%;background:#7c3aed;color:#fff;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(124,58,237,0.4);z-index:99998;display:flex;align-items:center;justify-content:center;font-size:20px;}',
      '.sb-copilot-toggle:hover{background:#6d28d9;}',
      '.sb-copilot-panel{position:fixed;top:0;right:0;width:360px;max-width:100vw;height:100vh;background:#fff;box-shadow:-4px 0 24px rgba(0,0,0,0.1);z-index:99999;display:flex;flex-direction:column;font-family:system-ui,sans-serif;}',
      '.sb-copilot-panel[data-position="left"]{right:auto;left:0;box-shadow:4px 0 24px rgba(0,0,0,0.1);}',
      '.sb-copilot-header{padding:16px;background:#f9fafb;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;}',
      '.sb-copilot-title{font-weight:600;color:#111827;}',
      '.sb-copilot-close{background:none;border:none;cursor:pointer;font-size:20px;color:#6b7280;}',
      '.sb-copilot-body{flex:1;overflow-y:auto;padding:16px;}',
      '.sb-copilot-suggestion{padding:12px;margin-bottom:12px;background:#f3f4f6;border-radius:8px;border-left:4px solid #7c3aed;}',
      '.sb-copilot-suggestion strong{display:block;margin-bottom:4px;color:#374151;}',
      '.sb-copilot-suggestion span{font-size:12px;color:#6b7280;}',
      '.sb-copilot-loading{text-align:center;padding:24px;color:#6b7280;}',
      '.sb-copilot-empty{text-align:center;padding:24px;color:#9ca3af;}',
    ].join('');
    document.head.appendChild(style);
  }

  function createToggle() {
    var btn = document.createElement('button');
    btn.className = 'sb-copilot-toggle';
    btn.innerHTML = '&#9998;';
    btn.setAttribute('aria-label', 'SalesBoost Copilot');
    btn.onclick = togglePanel;
    document.body.appendChild(btn);
    return btn;
  }

  function createPanel() {
    var panel = document.createElement('div');
    panel.className = 'sb-copilot-panel';
    panel.setAttribute('data-position', config.position);
    panel.style.display = 'none';
    panel.innerHTML = [
      '<div class="sb-copilot-header">',
      '  <span class="sb-copilot-title">SalesBoost 销转助手</span>',
      '  <button class="sb-copilot-close" aria-label="关闭">&times;</button>',
      '</div>',
      '<div class="sb-copilot-body"></div>',
    ].join('');
    panel.querySelector('.sb-copilot-close').onclick = togglePanel;
    document.body.appendChild(panel);
    return panel;
  }

  function togglePanel() {
    isOpen = !isOpen;
    if (container) {
      container.style.display = isOpen ? 'flex' : 'none';
    }
  }

  function setBodyContent(html) {
    var body = container && container.querySelector('.sb-copilot-body');
    if (body) body.innerHTML = html;
  }

  function suggest(customerMessage) {
    if (!container) return Promise.reject(new Error('SDK not initialized'));
    setBodyContent('<div class="sb-copilot-loading">正在生成建议...</div>');
    var url = config.baseUrl.replace(/\/$/, '') + '/api/v1/copilot/suggest';
    var body = {
      customer_message: customerMessage,
      deal_id: config.dealId,
      methodology: config.methodology,
      mode: config.mode,
    };
    var headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (config.apiKey) headers['Authorization'] = 'Bearer ' + config.apiKey;

    return fetch(url, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body),
    })
      .then(function (r) {
        if (!r.ok) throw new Error('API error: ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var suggestions = data.suggestions || [];
        if (suggestions.length === 0) {
          setBodyContent('<div class="sb-copilot-empty">暂无建议，请继续对话</div>');
          return data;
        }
        var html = suggestions
          .map(function (s) {
            return (
              '<div class="sb-copilot-suggestion">' +
              '<strong>' + (s.content || '').replace(/</g, '&lt;') + '</strong>' +
              '<span>' + (s.tactic || '') + ' · 置信度 ' + Math.round((s.confidence || 0) * 100) + '%</span>' +
              '</div>'
            );
          })
          .join('');
        setBodyContent(html);
        return data;
      })
      .catch(function (err) {
        setBodyContent('<div class="sb-copilot-empty">加载失败: ' + (err.message || '网络错误') + '</div>');
        throw err;
      });
  }

  var SalesBoost = {
    init: function (opts) {
      if (typeof opts !== 'object') opts = {};
      config.apiKey = opts.apiKey || config.apiKey;
      config.dealId = opts.dealId != null ? opts.dealId : config.dealId;
      config.baseUrl = opts.baseUrl || config.baseUrl;
      config.methodology = opts.methodology || config.methodology;
      config.position = opts.position || config.position;
      config.mode = opts.mode || config.mode;
      createStyles();
      var toggle = createToggle();
      container = createPanel();
      return this;
    },
    onCustomerMessage: function (message) {
      if (!message || typeof message !== 'string') return Promise.reject(new Error('Invalid message'));
      if (!container) container = document.querySelector('.sb-copilot-panel');
      if (!container) {
        this.init({});
      }
      isOpen = true;
      if (container) container.style.display = 'flex';
      return suggest(message);
    },
    close: togglePanel,
  };

  if (typeof window !== 'undefined') {
    window.SalesBoost = SalesBoost;
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = SalesBoost;
  }
})();
