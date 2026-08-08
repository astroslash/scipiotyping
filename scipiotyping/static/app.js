(() => {
  const root = document.documentElement;
  const apply = () => {
    root.classList.toggle('large-text', localStorage.getItem('scipio-large') === '1');
    root.classList.toggle('high-contrast', localStorage.getItem('scipio-contrast') === '1');
  };
  document.querySelectorAll('[data-display]').forEach(button => button.addEventListener('click', () => {
    const key = `scipio-${button.dataset.display}`;
    localStorage.setItem(key, localStorage.getItem(key) === '1' ? '0' : '1'); apply();
  }));
  apply();

  const daily = document.querySelector('#daily-goal');
  if (daily) {
    let baseSeconds = Number(daily.dataset.baseSeconds || 0);
    const goalSeconds = Number(daily.dataset.goalSeconds || 900);
    const progress = document.querySelector('#daily-goal-progress');
    const label = document.querySelector('#daily-goal-label');
    const format = seconds => {
      const total = Math.max(0, Math.floor(seconds));
      const hours = Math.floor(total / 3600), minutes = Math.floor(total % 3600 / 60), remainder = total % 60;
      return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}` : `${minutes}:${String(remainder).padStart(2, '0')}`;
    };
    const render = (additional = 0) => {
      const total = Math.max(0, baseSeconds + additional);
      progress.value = Math.min(total, goalSeconds);
      daily.classList.toggle('goal-reached', total >= goalSeconds);
      label.textContent = total >= goalSeconds ? `Daily goal reached! Today: ${format(total)} / ${format(goalSeconds)}` : `Today: ${format(total)} / ${format(goalSeconds)}`;
      daily.dataset.displaySeconds = String(total);
    };
    window.ScipioDaily = {
      format,
      updateCurrent: additional => render(additional),
      setAbsolute: seconds => { baseSeconds = Number(seconds || 0); daily.dataset.baseSeconds = String(baseSeconds); render(); },
      values: () => ({baseSeconds, goalSeconds})
    };
    render();
  }
})();
