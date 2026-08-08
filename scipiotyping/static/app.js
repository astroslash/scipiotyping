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
})();

