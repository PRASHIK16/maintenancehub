/**
 * MaintenanceHub — Core Application JavaScript
 * Minimal, framework-free. HTMX handles most interactions.
 * This file only contains browser-specific utilities that cannot
 * be done server-side or via HTMX.
 */

/* ── Theme management ───────────────────────────────────────────────────────── */

function setTheme(theme) {
  const root = document.documentElement;
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = theme === 'dark' || (theme === 'system' && prefersDark);

  root.setAttribute('data-theme', theme);
  root.classList.toggle('dark', isDark);
  localStorage.setItem('mh-theme', theme);

  // Update icons
  document.querySelectorAll('.dark-icon').forEach(el => el.classList.toggle('hidden', !isDark));
  document.querySelectorAll('.light-icon').forEach(el => el.classList.toggle('hidden', isDark));

  // Persist to server (for SSR)
  fetch('/auth/theme/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrf(),
    },
    body: JSON.stringify({ theme }),
  }).catch(() => {}); // non-critical
}

function toggleTheme() {
  const current = localStorage.getItem('mh-theme') || 'system';
  const next = current === 'dark' ? 'light' : 'dark';
  setTheme(next);
}

// Apply theme on load
(function() {
  const stored = localStorage.getItem('mh-theme') || 'system';
  setTheme(stored);
})();

// Sync with OS preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  const pref = localStorage.getItem('mh-theme') || 'system';
  if (pref === 'system') setTheme('system');
});

/* ── Toast notifications ─────────────────────────────────────────────────────── */

function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const typeConfig = {
    success: { icon: '✓', class: 'toast-success', bg: '#22c55e' },
    error:   { icon: '✕', class: 'toast-error',   bg: '#ef4444' },
    warning: { icon: '⚠', class: 'toast-warning', bg: '#f59e0b' },
    info:    { icon: 'ℹ', class: '',              bg: '#6366f1' },
  };
  const cfg = typeConfig[type] || typeConfig.info;

  const toast = document.createElement('div');
  toast.className = `toast ${cfg.class}`;
  toast.innerHTML = `
    <span style="color:${cfg.bg};font-size:1.1em;font-weight:700;">${cfg.icon}</span>
    <span class="flex-1 text-sm">${escapeHtml(message)}</span>
    <button onclick="dismissToast(this.parentElement)" class="text-gray-400 hover:text-gray-600 ml-2 text-lg leading-none">&times;</button>
  `;

  container.appendChild(toast);

  // Auto-dismiss
  const timer = setTimeout(() => dismissToast(toast), duration);
  toast.dataset.timer = timer;
}

function dismissToast(toast) {
  if (!toast || toast.classList.contains('toast-exit')) return;
  clearTimeout(parseInt(toast.dataset.timer));
  toast.classList.add('toast-exit');
  setTimeout(() => toast.remove(), 150);
}

/* ── Sidebar mobile ─────────────────────────────────────────────────────────── */

function openSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar?.classList.add('open');
  overlay?.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar?.classList.remove('open');
  overlay?.classList.add('hidden');
  document.body.style.overflow = '';
}

/* ── Modal management ────────────────────────────────────────────────────────── */

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    // Focus first focusable element
    const focusable = modal.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
    setTimeout(() => focusable?.focus(), 50);
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }
}

// Close modal on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop').forEach(m => {
      if (m.style.display !== 'none') closeModal(m.id);
    });
    closeSidebar();
  }
});

/* ── File upload preview ─────────────────────────────────────────────────────── */

function initFileUpload(inputId, previewId) {
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  if (!input || !preview) return;

  input.addEventListener('change', function() {
    preview.innerHTML = '';
    Array.from(this.files).forEach(file => {
      const item = document.createElement('div');
      item.className = 'flex items-center gap-3 p-2 bg-slate-50 rounded-lg border border-slate-200';

      if (file.type.startsWith('image/')) {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.className = 'w-12 h-12 object-cover rounded';
        item.appendChild(img);
      } else {
        const icon = document.createElement('div');
        icon.className = 'w-12 h-12 bg-slate-100 rounded flex items-center justify-center text-slate-400 text-xs font-600';
        icon.textContent = file.name.split('.').pop().toUpperCase();
        item.appendChild(icon);
      }

      const info = document.createElement('div');
      info.className = 'flex-1 min-w-0';
      info.innerHTML = `
        <p class="text-sm font-500 text-slate-700 truncate">${escapeHtml(file.name)}</p>
        <p class="text-xs text-slate-400">${formatFileSize(file.size)}</p>
      `;
      item.appendChild(info);
      preview.appendChild(item);
    });
  });

  // Drag and drop
  const zone = document.querySelector(`[data-upload-zone="${inputId}"]`);
  if (zone) {
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      input.files = e.dataTransfer.files;
      input.dispatchEvent(new Event('change'));
    });
    zone.addEventListener('click', () => input.click());
  }
}

/* ── Utility functions ────────────────────────────────────────────────────────── */

function getCsrf() {
  const el = document.querySelector('[name=csrfmiddlewaretoken]');
  return el ? el.value : '';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/* ── HTMX event hooks ─────────────────────────────────────────────────────────── */

document.addEventListener('htmx:afterSwap', function(evt) {
  // Re-init any file upload zones in swapped content
  evt.target.querySelectorAll('[data-file-upload]').forEach(el => {
    initFileUpload(el.dataset.fileUpload, el.dataset.filePreview);
  });
});

document.addEventListener('htmx:responseError', function(evt) {
  showToast('Something went wrong. Please try again.', 'error');
});

// Show/hide loading indicator
document.addEventListener('htmx:beforeRequest', function(evt) {
  const btn = evt.detail.elt;
  if (btn.tagName === 'BUTTON' || btn.tagName === 'A') {
    btn.dataset.originalText = btn.innerHTML;
    btn.disabled = true;
  }
});
document.addEventListener('htmx:afterRequest', function(evt) {
  const btn = evt.detail.elt;
  if (btn.dataset.originalText) {
    btn.innerHTML = btn.dataset.originalText;
    btn.disabled = false;
    delete btn.dataset.originalText;
  }
});

/* ── Keyboard shortcut: Cmd+K for search ────────────────────────────────────── */
document.addEventListener('keydown', function(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.querySelector('[name=q]');
    searchInput?.focus();
    searchInput?.select();
  }
});

/* ── Auto-submit filter forms on change ─────────────────────────────────────── */
document.querySelectorAll('[data-auto-submit]').forEach(form => {
  form.querySelectorAll('select, input[type=checkbox], input[type=radio]').forEach(el => {
    el.addEventListener('change', () => form.requestSubmit());
  });
});

/* ── Confirmation dialogs via data attribute ─────────────────────────────────── */
document.addEventListener('click', function(e) {
  const target = e.target.closest('[data-confirm]');
  if (target) {
    if (!confirm(target.dataset.confirm)) {
      e.preventDefault();
      e.stopPropagation();
    }
  }
});

/* ── Copy to clipboard ───────────────────────────────────────────────────────── */
function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn?.textContent;
    if (btn) btn.textContent = 'Copied!';
    showToast('Copied to clipboard', 'success', 2000);
    setTimeout(() => { if (btn) btn.textContent = orig; }, 2000);
  }).catch(() => showToast('Failed to copy', 'error'));
}
