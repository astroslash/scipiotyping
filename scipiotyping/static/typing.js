(() => {
  const app = document.querySelector('#typing-app');
  if (!app) return;
  const target = app.dataset.text;
  const display = document.querySelector('#passage');
  const input = document.querySelector('#typing-input');
  const timerEl = document.querySelector('#timer');
  const wpmEl = document.querySelector('#wpm');
  const accuracyEl = document.querySelector('#accuracy');
  const progressEl = document.querySelector('#character-progress');
  const finishButton = document.querySelector('#finish-button');
  const results = document.querySelector('#results');
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const completionMinimum = Math.max(1, Math.ceil(target.length * .85));
  const maximumLength = target.length + Math.max(20, Math.ceil(target.length * .10));
  input.maxLength = maximumLength;

  let started = null;
  let lastActivity = null;
  let inactiveMs = 0;
  let interval = null;
  let completionTimer = null;
  let correctedErrors = 0;
  let previous = '';
  let saved = false;
  let currentExpectedIndex = 0;
  let practiceSessionId = null;
  let sessionStartPromise = null;
  let recordedActiveSeconds = 0;
  let lastHeartbeatSeconds = 0;
  let heartbeatInFlight = false;
  const keyErrors = {};

  async function beginPracticeSession() {
    if (practiceSessionId) return practiceSessionId;
    if (!sessionStartPromise) {
      sessionStartPromise = fetch('/api/practice-sessions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({passage_id: document.querySelector('meta[name="passage-id"]').content, mode: app.dataset.mode})
      }).then(response => {
        if (!response.ok) throw new Error('session');
        return response.json();
      }).then(data => {
        practiceSessionId = data.id;
        if (window.ScipioDaily) window.ScipioDaily.setAbsolute(data.daily.active_seconds);
        return practiceSessionId;
      }).catch(() => {
        sessionStartPromise = null;
        return null;
      });
    }
    return sessionStartPromise;
  }

  async function saveHeartbeat(seconds = activeSeconds(), keepalive = false) {
    if (heartbeatInFlight || seconds <= recordedActiveSeconds || !await beginPracticeSession()) return;
    heartbeatInFlight = true;
    try {
      const response = await fetch(`/api/practice-sessions/${encodeURIComponent(practiceSessionId)}`, {
        method: 'PATCH', keepalive,
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({active_seconds: seconds})
      });
      if (!response.ok) throw new Error('heartbeat');
      const data = await response.json();
      recordedActiveSeconds = data.session_seconds;
      lastHeartbeatSeconds = recordedActiveSeconds;
      if (window.ScipioDaily) window.ScipioDaily.setAbsolute(data.daily.active_seconds);
    } catch {
      // The absolute value is retried on the next heartbeat, so time cannot double-count.
    } finally {
      heartbeatInFlight = false;
    }
  }

  function align(expected, typed, prefixMode = false) {
    const rows = expected.length + 1, columns = typed.length + 1;
    const cost = Array.from({length: rows}, () => Array(columns).fill(0));
    const back = Array.from({length: rows}, () => Array(columns).fill(null));
    for (let i = 1; i < rows; i++) { cost[i][0] = i; back[i][0] = 'delete'; }
    for (let j = 1; j < columns; j++) { cost[0][j] = j; back[0][j] = 'insert'; }
    for (let i = 1; i < rows; i++) {
      for (let j = 1; j < columns; j++) {
        const same = expected[i - 1] === typed[j - 1];
        const candidates = [
          [cost[i - 1][j - 1] + (same ? 0 : 1), same ? 0 : 2, same ? 'match' : 'substitute'],
          [cost[i - 1][j] + 1, 3, 'delete'],
          [cost[i][j - 1] + 1, 4, 'insert']
        ];
        if (i >= 2 && j >= 2 && expected[i - 2] === typed[j - 1] && expected[i - 1] === typed[j - 2]) {
          candidates.push([cost[i - 2][j - 2] + 1, 1, 'transpose']);
        }
        candidates.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
        [cost[i][j], , back[i][j]] = candidates[0];
      }
    }
    const operations = [];
    let endIndex = expected.length;
    if (prefixMode) {
      const limit = Math.min(expected.length, typed.length + Math.max(6, Math.ceil(typed.length * .10)));
      endIndex = 0;
      for (let candidate = 1; candidate <= limit; candidate++) {
        if (cost[candidate][typed.length] < cost[endIndex][typed.length]
            || (cost[candidate][typed.length] === cost[endIndex][typed.length] && candidate > endIndex)) {
          endIndex = candidate;
        }
      }
    }
    let i = endIndex, j = typed.length;
    while (i || j) {
      const op = back[i][j];
      const step = op === 'transpose' ? 2 : 1;
      const previousI = op === 'insert' ? i : i - step;
      const previousJ = op === 'delete' ? j : j - step;
      operations.push({op, expected: expected.slice(previousI, i), typed: typed.slice(previousJ, j)});
      i = previousI; j = previousJ;
    }
    operations.reverse();
    return operations;
  }

  function summarize(operations) {
    const summary = {matches: 0, substitutions: 0, insertions: 0, deletions: 0, transpositions: 0};
    const names = {match: 'matches', substitute: 'substitutions', insert: 'insertions', delete: 'deletions', transpose: 'transpositions'};
    operations.forEach(operation => summary[names[operation.op]]++);
    return summary;
  }

  function paint(value = '') {
    const operations = align(target, value, true);
    let lastTypedOperation = -1;
    operations.forEach((operation, index) => { if (operation.op !== 'delete') lastTypedOperation = index; });
    const classes = Array(target.length).fill('');
    let targetIndex = 0;
    operations.forEach((operation, operationIndex) => {
      if (operation.op === 'match') { classes[targetIndex] = 'correct'; targetIndex++; }
      else if (operation.op === 'substitute') { classes[targetIndex] = 'wrong'; targetIndex++; }
      else if (operation.op === 'transpose') { classes[targetIndex] = 'wrong'; classes[targetIndex + 1] = 'wrong'; targetIndex += 2; }
      else if (operation.op === 'delete') {
        if (operationIndex <= lastTypedOperation) classes[targetIndex] = 'missing';
        targetIndex++;
      }
    });
    currentExpectedIndex = 0;
    for (let index = 0; index < classes.length; index++) {
      if (!classes[index]) { currentExpectedIndex = index; break; }
      currentExpectedIndex = Math.min(target.length, index + 1);
    }
    if (currentExpectedIndex < target.length && !classes[currentExpectedIndex]) classes[currentExpectedIndex] = 'current';
    display.replaceChildren(...Array.from(target).map((character, index) => {
      const span = document.createElement('span');
      span.textContent = character;
      span.className = classes[index];
      return span;
    }));
    return operations;
  }

  function activeSeconds() {
    if (!started) return 0;
    const now = performance.now();
    const currentPause = Math.max(0, now - lastActivity - 15000);
    return Math.max(.1, (now - started - inactiveMs - currentPause) / 1000);
  }

  function metrics(value, operations = align(target, value)) {
    const summary = summarize(operations), seconds = activeSeconds(), minutes = seconds / 60;
    const errors = summary.substitutions + summary.insertions + summary.deletions + summary.transpositions;
    const denominator = summary.matches + errors;
    return {
      seconds,
      rawWpm: minutes ? value.length / 5 / minutes : 0,
      adjustedWpm: minutes ? summary.matches / 5 / minutes : 0,
      accuracy: denominator ? summary.matches / denominator * 100 : 100,
      summary
    };
  }

  function update(operations) {
    const value = input.value;
    const measurement = metrics(value, operations);
    const seconds = Math.floor(measurement.seconds);
    timerEl.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
    wpmEl.textContent = Math.round(measurement.adjustedWpm);
    accuracyEl.textContent = `${Math.round(measurement.accuracy)}%`;
    progressEl.textContent = `${Math.min(value.length, target.length)} / ${target.length} characters`;
    finishButton.hidden = value.length < completionMinimum;
    if (window.ScipioDaily) window.ScipioDaily.updateCurrent(Math.max(0, measurement.seconds - recordedActiveSeconds));
    if (measurement.seconds - lastHeartbeatSeconds >= 10) saveHeartbeat(measurement.seconds);
  }

  function likelyComplete(value) {
    if (value.length < completionMinimum) return false;
    const windowLength = Math.min(18, target.length);
    const expectedEnding = target.slice(-windowLength);
    const typedEnding = value.slice(-Math.min(value.length, windowLength + 4));
    const ending = summarize(align(expectedEnding, typedEnding));
    const endingErrors = ending.substitutions + ending.insertions + ending.deletions + ending.transpositions;
    return ending.matches / Math.max(1, ending.matches + endingErrors) >= .72;
  }

  function addText(tag, text, className = '') {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    results.appendChild(element);
    return element;
  }

  function renderDiff(operations) {
    const section = document.createElement('div');
    section.className = 'alignment-result';
    section.setAttribute('aria-label', 'Aligned typing result');
    operations.forEach(operation => {
      const span = document.createElement('span');
      if (operation.op === 'match') span.textContent = operation.expected;
      if (operation.op === 'substitute') { span.textContent = operation.typed; span.title = `Expected ${operation.expected}`; }
      if (operation.op === 'insert') { span.textContent = operation.typed; span.title = 'Extra character'; }
      if (operation.op === 'delete') { span.textContent = operation.expected === ' ' ? '␠' : operation.expected; span.title = `Missing ${operation.expected === ' ' ? 'space' : operation.expected}`; }
      if (operation.op === 'transpose') { span.textContent = operation.typed; span.title = `Reversed; expected ${operation.expected}`; }
      span.className = `diff-${operation.op}`;
      section.appendChild(span);
    });
    results.appendChild(section);
  }

  async function finish(manual = false) {
    if (saved || input.value.length < completionMinimum) return;
    saved = true;
    clearInterval(interval); clearTimeout(completionTimer);
    input.disabled = true; finishButton.disabled = true;
    const measurement = metrics(input.value);
    try {
      await beginPracticeSession();
      const response = await fetch('/api/attempts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({passage_id: document.querySelector('meta[name="passage-id"]').content,
          duration_seconds: measurement.seconds, typed_text: input.value, corrected_errors: correctedErrors,
          error_map: keyErrors, mode: app.dataset.mode, lesson_id: app.dataset.lesson,
          practice_session_id: practiceSessionId, finish_reason: manual ? 'manual' : 'automatic'})
      });
      if (!response.ok) throw new Error();
      const score = await response.json();
      recordedActiveSeconds = score.session_seconds;
      if (window.ScipioDaily) window.ScipioDaily.setAbsolute(score.daily.active_seconds);
      results.replaceChildren();
      addText('h2', 'Expedition complete');
      addText('p', `Raw speed: ${score.gross_wpm} WPM · Adjusted speed: ${score.adjusted_wpm} WPM · Accuracy: ${score.accuracy}%`);
      addText('p', `Corrected errors: ${score.corrected_errors} · Remaining errors: ${score.errors} (${score.substitutions} substitutions, ${score.insertions} insertions, ${score.deletions} deletions, ${score.transpositions} transpositions)`);
      addText('p', `You practiced for ${window.ScipioDaily ? window.ScipioDaily.format(score.session_seconds) : Math.round(score.session_seconds) + ' seconds'} this session. Today: ${window.ScipioDaily ? window.ScipioDaily.format(score.daily.active_seconds) : Math.round(score.daily.active_seconds) + ' seconds'} of your ${window.ScipioDaily ? window.ScipioDaily.format(score.daily.goal_seconds) : Math.round(score.daily.goal_seconds / 60) + ' minute'} goal.${score.daily.goal_reached ? ' Daily goal reached!' : ''}`);
      if (score.focus_feedback.length) {
        addText('h3', 'Focus-key results');
        score.focus_feedback.forEach(item => {
          const trend = item.change === null ? '' : item.change > 0 ? ` Recent accuracy improved by ${item.change} points.` : item.change < 0 ? ` Recent accuracy changed by ${item.change} points; one careful repeat will help.` : ' Recent accuracy held steady.';
          const guidance = item.status === 'mastered' ? ' Mastery reached.' : item.accuracy >= 92 ? ' This attempt was accurate; keep building evidence.' : ' Slow down and practice this key again.';
          addText('p', `${item.label}: ${item.accuracy}% accuracy across ${item.expected} uses.${trend}${guidance}`);
        });
      }
      addText('h3', 'Aligned result');
      renderDiff(score.operations);
      const message = score.accuracy >= 95 ? 'Excellent control. Accuracy is building lasting speed.' : 'Good effort. Review the marked characters, then try again carefully.';
      addText('p', message + (score.placement_level ? ` Your placement level is ${score.placement_level}.` : '') + (score.achievements.length ? ` New achievement: ${score.achievements.join(', ')}.` : ''));
      const link = addText('a', 'Continue training', 'button'); link.href = '/lessons';
    } catch {
      saved = false; input.disabled = false; finishButton.disabled = false;
      results.textContent = 'The result could not be saved. Check that the local server is running and try again.';
    }
    results.hidden = false; results.setAttribute('tabindex', '-1'); results.focus();
  }

  input.addEventListener('paste', event => event.preventDefault());
  input.addEventListener('drop', event => event.preventDefault());
  input.addEventListener('keydown', event => {
    if (event.key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey) {
      // Derive the expected key from the current value at event time. Automated
      // input and very fast typists can deliver the next key before a scheduled
      // repaint, so a cached cursor would misattribute otherwise-correct keys.
      paint(input.value);
      const expected = target[currentExpectedIndex];
      if (event.key !== expected) {
        const label = expected === ' ' ? 'space' : expected;
        if (label) keyErrors[label] = (keyErrors[label] || 0) + 1;
      }
    }
  });
  input.addEventListener('input', () => {
    const now = performance.now();
    if (!started) { started = now; lastActivity = now; beginPracticeSession(); interval = setInterval(() => update(align(target, input.value, true)), 500); }
    else if (now - lastActivity > 15000) inactiveMs += now - lastActivity - 15000;
    lastActivity = now;
    if (input.value.length < previous.length) correctedErrors += previous.length - input.value.length;
    previous = input.value;
    const operations = paint(input.value); update(operations);
    clearTimeout(completionTimer);
    if (likelyComplete(input.value)) completionTimer = setTimeout(() => finish(false), 450);
  });
  finishButton.addEventListener('click', () => finish(true));
  window.addEventListener('pagehide', () => { if (started && !saved) saveHeartbeat(activeSeconds(), true); });
  document.querySelector('#restart').addEventListener('click', () => location.reload());
  const initial = paint(); update(initial); input.focus();
})();
