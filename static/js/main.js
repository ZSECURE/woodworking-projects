/**
 * Conservatory Roof Calculator — JavaScript
 */

// ── Form helpers ──────────────────────────────────────────────────────────────

function resetForm() {
  const form = document.getElementById('roofForm');
  if (!form) return;
  form.reset();
  // Re-sync slider
  const pitchInput  = document.getElementById('pitch');
  const pitchSlider = document.getElementById('pitchSlider');
  const pitchLabel  = document.getElementById('pitchLabel');
  if (pitchSlider && pitchInput) {
    pitchSlider.value = pitchInput.value;
    if (pitchLabel) pitchLabel.textContent = pitchInput.value + '°';
  }
  // Clear live preview
  ['prev-rise', 'prev-ridge', 'prev-cr', 'prev-hip'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '—';
  });
}

// ── Form validation ───────────────────────────────────────────────────────────

(function () {
  const form = document.getElementById('roofForm');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    const length = parseFloat(document.getElementById('length')?.value);
    const width  = parseFloat(document.getElementById('width')?.value);
    const pitch  = parseFloat(document.getElementById('pitch')?.value  || 30);
    const ovhng  = parseFloat(document.getElementById('overhang')?.value || 300);
    const spc    = parseFloat(document.getElementById('spacing')?.value || 600);

    const errs = [];
    if (!length || length < 1 || length > 20) errs.push('Length must be between 1 m and 20 m.');
    if (!width  || width  < 1 || width  > 15) errs.push('Width must be between 1 m and 15 m.');
    if (pitch < 10 || pitch > 60)              errs.push('Pitch must be between 10° and 60°.');
    if (ovhng < 0  || ovhng > 600)             errs.push('Overhang must be 0–600 mm.');
    if (spc < 300  || spc > 900)               errs.push('Rafter spacing must be 300–900 mm.');

    if (errs.length > 0) {
      e.preventDefault();
      let banner = document.querySelector('.error-banner');
      if (!banner) {
        banner = document.createElement('div');
        banner.className = 'error-banner';
        banner.innerHTML = '<div class="error-icon">⚠</div><div class="error-list"></div>';
        form.parentNode.insertBefore(banner, form);
      }
      const list = banner.querySelector('.error-list');
      list.innerHTML = errs.map(msg => `<p>${msg}</p>`).join('');
      banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // Show loading state
    const btn = document.getElementById('calcBtn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="btn-icon">⏳</span> Calculating…';
    }
  });
})();

// ── Number formatting helpers ─────────────────────────────────────────────────

function fmtMm(mm) {
  return Math.round(mm).toLocaleString();
}

// ── Smooth scroll for anchor links ───────────────────────────────────────────

document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', function (e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// ── Table sort (global, used by results.html inline calls) ───────────────────

function sortTable(tableId, colIndex) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const tbody = table.querySelector('tbody');
  const rows  = Array.from(tbody.querySelectorAll('tr'));

  const asc = table.dataset.sortCol === String(colIndex) &&
              table.dataset.sortDir !== 'asc';
  table.dataset.sortCol = colIndex;
  table.dataset.sortDir = asc ? 'asc' : 'desc';

  rows.sort((a, b) => {
    const ta = a.cells[colIndex]?.textContent.trim() || '';
    const tb = b.cells[colIndex]?.textContent.trim() || '';
    const na = parseFloat(ta);
    const nb = parseFloat(tb);
    if (!isNaN(na) && !isNaN(nb)) {
      return asc ? na - nb : nb - na;
    }
    return asc ? ta.localeCompare(tb) : tb.localeCompare(ta);
  });

  rows.forEach(r => tbody.appendChild(r));
}
