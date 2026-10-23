/* Instructions are public; problem PDFs require a signed-in team. */
(() => {
  'use strict';
  function mount() {
    document.getElementById('lcpc-resources')?.remove();
    const header = document.querySelector('app-header > header');
    if (!header) return;
    let nav = header.querySelector(':scope > nav:not(#lcpc-public-navigation)');
    let publicNav = document.getElementById('lcpc-public-navigation');
    const loggedIn = globalThis.LCPCSession?.isAuthenticated() && nav && !/^#\/(login|logout)(?:\?|$)/.test(location.hash);
    if (nav) publicNav?.remove();
    else {
      if (!publicNav) {
        publicNav = document.createElement('nav');
        publicNav.id = 'lcpc-public-navigation';
        publicNav.setAttribute('aria-label', 'Public resources');
        header.append(publicNav);
      }
      nav = publicNav;
    }
    if (!loggedIn) document.getElementById('lcpc-resource-problems')?.remove();
    const logout = nav.querySelector('a[href$="/logout"]');
    for (const [id, label, href] of [
      ['lcpc-resource-instructions', 'Instructions', '/instructions/'],
      ['lcpc-resource-problems', 'Problem PDFs', '/problems/']
    ]) {
      if (id === 'lcpc-resource-problems' && !loggedIn) continue;
      if (document.getElementById(id)) continue;
      const link = document.createElement('a');
      link.id = id;
      link.className = 'lcpc-resource-link';
      link.textContent = label;
      link.href = href;
      link.target = '_blank';
      link.rel = 'noopener';
      link.title = label + ' — opens in a new tab';
      nav.insertBefore(link, logout);
    }
    if (loggedIn) {
      const priority = ['/problems/', '/runs', '/clarifications', '/scoreboard', '/instructions/', '/options', '/logout'];
      const position = link => {
        const url = new URL(link.href, location.href);
        const route = url.hash.startsWith('#/') ? url.hash.slice(1).split('?')[0] : url.pathname;
        const index = priority.indexOf(route);
        return index < 0 ? priority.length : index;
      };
      const links = Array.from(nav.children).filter(node => node.tagName === 'A');
      links.sort((a, b) => position(a) - position(b));
      const focused = nav.contains(document.activeElement) ? document.activeElement : null;
      let cursor = nav.firstElementChild;
      for (const link of links) {
        if (link !== cursor) nav.insertBefore(link, cursor);
        cursor = link.nextElementSibling;
      }
      if (focused && document.activeElement !== focused) focused.focus({preventScroll: true});
    }
  }
  new MutationObserver(mount).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', mount);
  document.addEventListener('lcpc-auth-change', mount);
  window.addEventListener('hashchange', mount);
  mount();
})();
