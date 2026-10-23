/* Add the university logos alongside the original PC2 and ICPC branding. */
(() => {
  'use strict';
  let displayNames = null;
  let loadingNames = false;
  let namesRequested = false;
  function showTeamName() {
    const label = document.querySelector('app-header > header > .teamid-container > p');
    if (!label || !globalThis.LCPCSession?.isAuthenticated()) {
      document.getElementById('lcpc-team-display-name')?.remove();
      return;
    }
    const team = /^TEAM\s+(\d+)\b/i.exec(label.firstChild?.textContent || '');
    if (!team) return;
    const name = displayNames?.get(team[1]);
    if (name) {
      let suffix = label.querySelector('#lcpc-team-display-name');
      if (!suffix) {
        suffix = document.createElement('span');
        suffix.id = 'lcpc-team-display-name';
        const separator = document.createElement('span');
        separator.textContent = ' / ';
        const display = document.createElement('bdi');
        suffix.append(separator, display);
        label.append(suffix);
      }
      const display = suffix.querySelector('bdi');
      if (display.textContent !== name) display.textContent = name;
      return;
    }
    if (loadingNames || namesRequested) return;
    loadingNames = true;
    namesRequested = true;
    // Match the stable team ID, never the row's rank or position. Use only
    // the standings snapshot already published by the contest exporter.
    fetch('/standings/data.json', {credentials: 'same-origin', cache: 'no-store'})
      .then(response => {
        if (!response.ok) throw new Error('Team names unavailable');
        return response.json();
      })
      .then(payload => {
        const rows = payload?.contestStandings?.teamStanding;
        const teams = Array.isArray(rows) ? rows : rows ? [rows] : [];
        displayNames = new Map(teams
          .filter(row => /^\d+$/.test(String(row.teamId)) && typeof row.teamName === 'string' && row.teamName.trim())
          .map(row => [String(row.teamId), row.teamName.trim()]));
      })
      .catch(() => {})
      .finally(() => { loadingNames = false; showTeamName(); });
  }
  function brandHeader() {
    showTeamName();
    const container = document.querySelector('app-header > header .logo-container');
    if (!container) return;
    if (globalThis.LCPCParticipantIdentity?.renderHeader(container)) return;
    const images = container.querySelectorAll('img');
    if (images.length < 3) return;
    for (const [image, src, alt] of [
      [images[0], '/assets/PC2Logo.png', 'PC^2 Logo'],
      [images[2], '/assets/icpc-banner.png', 'ICPC Programming Contest Logo']
    ]) {
      if (image.getAttribute('src') !== src) image.setAttribute('src', src);
      if (image.alt !== alt) image.alt = alt;
    }
    for (const [id, file, alt] of [
      ['lcpc-header-university', 'omu-logo.png', 'Omar Al-Mukhtar University'],
      ['lcpc-header-contest', 'lcpc-logo.png', 'Omar Al-Mukhtar University Programming Contest']
    ]) {
      if (container.querySelector('#' + id)) continue;
      const image = document.createElement('img');
      image.id = id;
      image.className = 'lcpc-institution-logo';
      image.src = '/assets/lcpc-branding/' + file;
      image.alt = alt;
      container.append(image);
    }
    container.classList.add('lcpc-header-logos');
  }
  new MutationObserver(brandHeader).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', brandHeader);
  document.addEventListener('lcpc-auth-change', brandHeader);
  document.addEventListener('lcpc-participant-identity', brandHeader);
  window.addEventListener('focus', () => {
    if (!loadingNames) { displayNames = null; namesRequested = false; }
    showTeamName();
  });
  brandHeader();
})();
