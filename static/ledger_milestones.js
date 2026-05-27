/*
 * Milestone map interactions:
 *   - Inline edit form toggle per row
 *   - Drag-to-reorder with HTML5 drag + touch long-press fallback
 */
(function () {
  // ---- inline edit toggles ----
  document.querySelectorAll('[data-edit-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.editToggle;
      const form = document.getElementById('lg-edit-' + id);
      if (!form) return;
      form.style.display = (form.style.display === 'none' || !form.style.display) ? 'block' : 'none';
    });
  });

  // ---- drag-to-reorder ----
  const list = document.getElementById('lg-milestone-list');
  if (!list) return;

  let dragging = null;

  list.addEventListener('dragstart', (e) => {
    const li = e.target.closest('.lg-milestone');
    if (!li) return;
    dragging = li;
    li.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', li.dataset.id); } catch (err) {}
  });

  list.addEventListener('dragover', (e) => {
    e.preventDefault();
    const li = e.target.closest('.lg-milestone');
    if (!li || li === dragging) return;
    // Clear any previous drop-target highlight
    document.querySelectorAll('.lg-milestone.drop-target').forEach(el => el.classList.remove('drop-target'));
    li.classList.add('drop-target');
  });

  list.addEventListener('dragleave', (e) => {
    const li = e.target.closest('.lg-milestone');
    if (li) li.classList.remove('drop-target');
  });

  list.addEventListener('drop', (e) => {
    e.preventDefault();
    const target = e.target.closest('.lg-milestone');
    if (!target || !dragging || target === dragging) return cleanup();
    const targetRect = target.getBoundingClientRect();
    const before = e.clientY < targetRect.top + targetRect.height / 2;
    if (before) target.parentNode.insertBefore(dragging, target);
    else        target.parentNode.insertBefore(dragging, target.nextSibling);
    cleanup();
    persistOrder();
  });

  list.addEventListener('dragend', cleanup);

  function cleanup() {
    if (dragging) dragging.classList.remove('dragging');
    document.querySelectorAll('.lg-milestone.drop-target').forEach(el => el.classList.remove('drop-target'));
    dragging = null;
  }

  async function persistOrder() {
    const ids = Array.from(list.querySelectorAll('.lg-milestone')).map(li => parseInt(li.dataset.id, 10));
    try {
      const res = await fetch('/ledger/milestones/reorder', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order: ids}),
      });
      const data = await res.json();
      if (!data.ok) console.warn('reorder failed:', data);
      // Soft-refresh so position numbers + status flags re-render correctly.
      window.location.reload();
    } catch (err) { console.error(err); }
  }
})();
