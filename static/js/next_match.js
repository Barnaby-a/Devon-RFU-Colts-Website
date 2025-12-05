document.addEventListener('DOMContentLoaded', function () {
  const el = document.querySelector('.nm-countdown');
  if (!el) return;

  const targetISO = el.getAttribute('data-datetime');
  if (!targetISO) return;
  const target = new Date(targetISO);
  if (isNaN(target)) return;

  function pad(n) { return String(n).padStart(2, '0'); }

  function update() {
    const now = new Date();
    let diff = Math.max(0, target.getTime() - now.getTime());
    if (diff <= 0) {
      // show started
      el.querySelector('.cd-days').textContent = '00';
      el.querySelector('.cd-hours').textContent = '00';
      el.querySelector('.cd-mins').textContent = '00';
      el.querySelector('.cd-secs').textContent = '00';
      el.querySelector('.cd-label').textContent = 'Kick-off';
      clearInterval(interval);
      return;
    }
    const secs = Math.floor(diff / 1000);
    const days = Math.floor(secs / 86400);
    const hours = Math.floor((secs % 86400) / 3600);
    const mins = Math.floor((secs % 3600) / 60);
    const s = secs % 60;

    const daysEl = el.querySelector('.cd-days');
    const hoursEl = el.querySelector('.cd-hours');
    const minsEl = el.querySelector('.cd-mins');
    const secsEl = el.querySelector('.cd-secs');

    if (daysEl) daysEl.textContent = pad(days);
    if (hoursEl) hoursEl.textContent = pad(hours);
    if (minsEl) minsEl.textContent = pad(mins);
    if (secsEl) secsEl.textContent = pad(s);
  }

  update();
  const interval = setInterval(update, 1000);
});
