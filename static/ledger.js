/* The Ledger — minimal interaction layer. Vanilla, matches the rest of the ship. */

(function () {
  // -------- live "expected vs actual" delta on payday checking input --------
  const checkingInput = document.getElementById('lg-checking-input');
  const expectedSpan  = document.getElementById('lg-checking-expected');
  const deltaSpan     = document.getElementById('lg-checking-delta');
  if (checkingInput && expectedSpan && deltaSpan) {
    const expected = parseFloat(expectedSpan.dataset.expected || '');
    const update = () => {
      const v = parseFloat(checkingInput.value);
      if (isNaN(v) || isNaN(expected)) {
        deltaSpan.textContent = '';
        return;
      }
      const delta = v - expected;
      const sign = delta > 0 ? '+' : '';
      const cls = delta < -1 ? 'lg-neg' : (delta > 1 ? 'lg-pos' : 'lg-dim');
      deltaSpan.className = 'lg-mono ' + cls;
      deltaSpan.textContent = `Δ ${sign}$${delta.toFixed(2)} from expected`;
    };
    checkingInput.addEventListener('input', update);
    update();
  }

  // -------- expand/collapse the "different amount" rows on payday autopay confirms --------
  document.querySelectorAll('[data-pending-row]').forEach(row => {
    const radios = row.querySelectorAll('input[type=radio]');
    const altBlock = row.querySelector('[data-alt-block]');
    if (!altBlock) return;
    radios.forEach(r => r.addEventListener('change', () => {
      const choice = row.querySelector('input[type=radio]:checked');
      altBlock.style.display = (choice && choice.value === 'different') ? 'block' : 'none';
    }));
  });

  // -------- dynamic +ROW behavior in payday session --------
  document.querySelectorAll('[data-add-row]').forEach(btn => {
    btn.addEventListener('click', () => {
      const container = document.getElementById(btn.dataset.target);
      if (!container) return;
      const template = container.querySelector('[data-row-template]');
      if (!template) return;
      const idx = container.querySelectorAll('[data-row]').length;
      const clone = template.cloneNode(true);
      clone.removeAttribute('data-row-template');
      clone.setAttribute('data-row', '');
      clone.style.display = '';
      // Rewrite [0] in name attributes to current index
      clone.querySelectorAll('input, select, textarea').forEach(el => {
        if (el.name) el.name = el.name.replace(/\[\d+\]/, `[${idx}]`);
        el.value = '';
      });
      container.insertBefore(clone, template);
    });
  });

  // -------- AI assistant button --------
  const aiBtn = document.getElementById('lg-ai-btn');
  const aiPanel = document.getElementById('lg-ai-panel');
  if (aiBtn && aiPanel) {
    aiBtn.addEventListener('click', async () => {
      aiBtn.disabled = true;
      aiBtn.textContent = 'thinking…';
      aiPanel.innerHTML = '<div class="lg-note">Asking Claude…</div>';
      try {
        const res = await fetch(aiBtn.dataset.endpoint, {
          method: 'POST',
          headers: {'X-Requested-With': 'fetch'},
        });
        const data = await res.json();
        const recs = data.recommendations || [];
        if (!recs.length) {
          aiPanel.innerHTML = '<div class="lg-note">No recommendations.</div>';
        } else {
          aiPanel.innerHTML = recs.map(r => `
            <div class="lg-card" style="margin-bottom:10px">
              <h4 style="font-family:var(--lg-display); font-weight:600; margin:0 0 6px;">${escapeHtml(r.headline || '')}</h4>
              <div class="lg-mono" style="color:var(--lg-brass-soft); font-size:0.92rem;">${escapeHtml(r.action || '')}</div>
              <div class="lg-note" style="margin-top:6px;">${escapeHtml(r.impact || '')}</div>
              <div style="margin-top:8px; font-size:0.92rem;">${escapeHtml(r.rationale || '')}</div>
            </div>
          `).join('');
          if (data.source === 'rule') {
            aiPanel.insertAdjacentHTML('beforeend',
              '<div class="lg-note">Rule-based fallback (Claude unavailable or returned invalid JSON).</div>');
          }
        }
      } catch (e) {
        aiPanel.innerHTML = `<div class="lg-note lg-neg">Error: ${escapeHtml(String(e))}</div>`;
      } finally {
        aiBtn.disabled = false;
        aiBtn.textContent = 'Ask Claude what to do';
      }
    });
  }

  // -------- sparkline (account detail) --------
  document.querySelectorAll('[data-sparkline]').forEach(svg => {
    const data = JSON.parse(svg.dataset.sparkline);
    if (!data.length) return;
    const w = svg.viewBox.baseVal.width || 600;
    const h = svg.viewBox.baseVal.height || 60;
    const pad = 4;
    const xs = data.map((_, i) => pad + (i / Math.max(1, data.length - 1)) * (w - 2 * pad));
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const ys = data.map(v => h - pad - ((v - min) / range) * (h - 2 * pad));
    const d = xs.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${ys[i].toFixed(1)}`).join(' ');
    svg.innerHTML = `<path d="${d}" stroke="var(--lg-brass)" stroke-width="1.5" fill="none" />`;
  });

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;"
    }[c]));
  }
})();
