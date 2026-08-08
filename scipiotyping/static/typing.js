(() => {
  const app = document.querySelector('#typing-app');
  if (!app) return;
  const target = app.dataset.text;
  const display = document.querySelector('#passage');
  const input = document.querySelector('#typing-input');
  const timerEl = document.querySelector('#timer');
  const wpmEl = document.querySelector('#wpm');
  const accuracyEl = document.querySelector('#accuracy');
  const results = document.querySelector('#results');
  let started = null, interval = null, errors = 0, correctedErrors = 0, previous = '', saved = false;

  function paint(value = '') {
    display.replaceChildren(...Array.from(target).map((char, i) => {
      const span = document.createElement('span'); span.textContent = char;
      span.className = i < value.length ? (value[i] === char ? 'correct' : 'wrong') : (i === value.length ? 'current' : '');
      return span;
    }));
  }
  function elapsed() { return started ? Math.max(.1, (performance.now() - started) / 1000) : 0; }
  function metrics(value) {
    const correct = Array.from(value).filter((c, i) => c === target[i]).length;
    const seconds = elapsed();
    return { correct, seconds, wpm: seconds ? Math.max(0, value.length / 5 / (seconds / 60) - errors / (seconds / 60)) : 0, accuracy: value.length ? correct / value.length * 100 : 100 };
  }
  function update() {
    const m = metrics(input.value); const s = Math.floor(m.seconds);
    timerEl.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
    wpmEl.textContent = Math.round(m.wpm); accuracyEl.textContent = `${Math.round(m.accuracy)}%`;
  }
  async function finish() {
    if (saved) return; saved = true; clearInterval(interval); input.disabled = true;
    const m = metrics(input.value);
    try {
      const response = await fetch('/api/attempts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({passage_id:document.querySelector('meta[name="passage-id"]').content,duration_seconds:m.seconds,typed_characters:input.value.length,correct_characters:m.correct,errors,corrected_errors:correctedErrors,completed:true})});
      if (!response.ok) throw new Error(); const score = await response.json();
      results.innerHTML = `<h2>Expedition complete</h2><p><strong>${score.net_wpm}</strong> WPM · <strong>${score.accuracy}%</strong> accuracy</p><p>${score.accuracy >= 95 ? 'Excellent control. Accuracy is building lasting speed.' : 'Good effort. A careful second attempt will strengthen the difficult spots.'}</p><a class="button" href="/library">Choose another</a>`;
    } catch { saved = false; input.disabled = false; results.textContent = 'The result could not be saved. Check that the local server is running and try again.'; }
    results.hidden = false; results.focus();
  }
  input.addEventListener('paste', e => e.preventDefault());
  input.addEventListener('input', () => {
    if (!started && input.value) { started = performance.now(); interval = setInterval(update, 500); }
    const value = input.value.slice(0, target.length); if (input.value !== value) input.value = value;
    if (value.length > previous.length) for (let i = previous.length; i < value.length; i++) if (value[i] !== target[i]) errors++;
    if (value.length < previous.length) correctedErrors += previous.length - value.length;
    previous = value; paint(value); update(); if (value === target) finish();
  });
  document.querySelector('#restart').addEventListener('click', () => location.reload());
  paint(); input.focus();
})();

