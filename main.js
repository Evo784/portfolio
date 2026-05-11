document.addEventListener('DOMContentLoaded', () => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Reveal animations ──────────────────────────────────────

  const reveals = document.querySelectorAll('.reveal');

  if (prefersReducedMotion) {
    reveals.forEach(el => el.classList.add('visible'));
  } else {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '-30px 0px' }
    );
    reveals.forEach(el => revealObserver.observe(el));
  }

  // ── Ambient background gradient shifts on scroll ──────────

  const bgAmbient = document.getElementById('bgAmbient');
  if (bgAmbient) {
    const bgSections = [
      { id: 'skills', bg: 'radial-gradient(ellipse at 70% 40%, #0c1a30 0%, transparent 55%), radial-gradient(ellipse at 20% 80%, #0a1e2a 0%, transparent 50%), #06060f' },
      { id: 'about', bg: 'radial-gradient(ellipse at 20% 50%, #1a1020 0%, transparent 50%), radial-gradient(ellipse at 80% 90%, #0a1e2a 0%, transparent 55%), #06060f' },
      { id: 'projet-pro', bg: 'radial-gradient(ellipse at 50% 30%, #1a1810 0%, transparent 50%), radial-gradient(ellipse at 80% 70%, #0c1a2e 0%, transparent 50%), #06060f' },
      { id: 'projects', bg: 'radial-gradient(ellipse at 30% 60%, #0a1e2a 0%, transparent 50%), radial-gradient(ellipse at 90% 20%, #0c1a30 0%, transparent 50%), #06060f' },
      { id: 'competences', bg: 'radial-gradient(ellipse at 60% 40%, #0c1a30 0%, transparent 50%), radial-gradient(ellipse at 10% 80%, #0a1e2a 0%, transparent 50%), #06060f' },
      { id: 'contact', bg: 'radial-gradient(ellipse at 50% 80%, #1a1020 0%, transparent 45%), radial-gradient(ellipse at 30% 20%, #0c1a2e 0%, transparent 50%), #06060f' },
    ];

    const bgObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const match = bgSections.find(s => s.id === entry.target.id);
            if (match) bgAmbient.style.background = match.bg;
          }
        });
      },
      { threshold: 0.3 }
    );

    bgSections.forEach(s => {
      const el = document.getElementById(s.id);
      if (el) bgObserver.observe(el);
    });
  }

  // ── Floating nav — darken on scroll ───────────────────────

  const header = document.querySelector('.site-header');
  let ticking = false;

  function updateHeader() {
    if (window.scrollY > 80) {
      header.style.background = 'rgba(13, 13, 26, 0.88)';
      header.style.boxShadow = '0 4px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)';
    } else {
      header.style.background = 'rgba(13, 13, 26, 0.7)';
      header.style.boxShadow = '0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)';
    }
    ticking = false;
  }

  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(updateHeader);
      ticking = true;
    }
  }, { passive: true });

  // ── Contact modal ──────────────────────────────────────────

  const modal = document.getElementById('contactModal');
  const modalClose = document.getElementById('modalClose');
  const contactBtns = [
    document.getElementById('contactBtn'),
    document.getElementById('contactBtnLarge'),
    document.getElementById('contactBtnAbout'),
  ];

  function openModal(e) {
    e.preventDefault();
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }

  contactBtns.forEach(btn => { if (btn) btn.addEventListener('click', openModal); });
  if (modalClose) modalClose.addEventListener('click', closeModal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) closeModal();
  });

  // ── Smooth scroll for nav links ────────────────────────────

  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const href = anchor.getAttribute('href');
      if (href === '#') return;
      e.preventDefault();
      const target = document.querySelector(href);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // ── Project preview interactivity ─────────────────────────

  const previewUrlEl = document.getElementById('preview-url');
  const previewMetricsEl = document.getElementById('preview-metrics');
  const previewViewport = document.querySelector('.preview-viewport');
  const projectsList = document.getElementById('projects-list');

  // Static project metadata (for the 4 base projects with SVG previews)
  const projectMeta = {
    assetto: {
      url: 'localhost:3000/telemetry',
      metrics: ['60Hz capture', '< 15ms latence', '14 canaux'],
    },
    backtester: {
      url: 'github.com/evo784/backtester',
      metrics: ['10 ans de données', '50+ indicateurs', 'Sharpe 1.84'],
    },
    ressourcezvous: {
      url: 'fcgxrvo.cluster100.hosting.ovh.net',
      metrics: ['SEO 95+', '< 2s chargement', 'En production'],
    },
    arct: {
      url: 'autorcthonon.fr',
      metrics: ['Livré en 2 semaines', '9 pages statiques', '0 dépendances'],
    },
  };

  function activateProject(key) {
    document.querySelectorAll('.project-row[data-project]').forEach(r =>
      r.classList.toggle('active', r.dataset.project === key)
    );
    document.querySelectorAll('.preview-screen').forEach(s =>
      s.classList.toggle('active', s.id === `screen-${key}`)
    );
    const meta = projectMeta[key];
    if (meta && previewUrlEl) previewUrlEl.textContent = meta.url;
    if (meta && previewMetricsEl) {
      previewMetricsEl.innerHTML = meta.metrics
        .map(m => `<span class="metric">${m}</span>`)
        .join('');
    }
  }

  function bindProjectInteractivity() {
    const rows = document.querySelectorAll('.project-row[data-project]');
    rows.forEach(row => {
      row.addEventListener('mouseenter', () => activateProject(row.dataset.project));
      row.addEventListener('focus', () => activateProject(row.dataset.project));
    });
  }

  // Direct listeners + delegation on showcase container
  const showcase = document.querySelector('.projects-showcase');
  bindProjectInteractivity();

  if (showcase) {
    showcase.addEventListener('mouseover', (e) => {
      const row = e.target.closest('[data-project]');
      if (row && row.dataset.project) activateProject(row.dataset.project);
    });
  }

  // Activate first project
  const initialRows = document.querySelectorAll('.project-row[data-project]');
  if (initialRows.length > 0) activateProject('assetto');

  // ── Dynamic projects from API ────────────────────────────

  async function loadDynamicProjects() {
    try {
      const res = await fetch('/api/projects');
      if (!res.ok) return;
      const projects = await res.json();

      // IDs already in the static HTML
      const staticIds = new Set();
      document.querySelectorAll('.project-row[data-static="true"]').forEach(el => {
        staticIds.add(el.dataset.project);
      });

      // Filter to only new (admin-added) projects
      const dynamicProjects = projects.filter(p => !staticIds.has(p.id) && p.visible);
      if (dynamicProjects.length === 0) return;

      const staticCount = staticIds.size;

      dynamicProjects.forEach((p, i) => {
        const num = String(staticCount + i + 1).padStart(2, '0');
        const href = p.static_page ? `/${p.static_page}` : `/project/${p.id}`;

        // Create project row
        const row = document.createElement('a');
        row.href = href;
        row.className = 'project-row reveal visible';
        row.dataset.project = p.id;
        row.innerHTML = `
          <div class="pr-num">${num}</div>
          <div class="pr-body">
            <h3 class="pr-title">${escHtml(p.title)}</h3>
            <p class="pr-sub">${escHtml(p.subtitle || '')}</p>
            <div class="pr-tags">
              ${(p.tags || []).map(t => `<span>${escHtml(t)}</span>`).join('')}
            </div>
          </div>
          <div class="pr-arrow" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M7 17L17 7M17 7H7M17 7v10"/></svg>
          </div>`;
        projectsList.appendChild(row);

        // Create preview screen
        if (previewViewport) {
          const screen = document.createElement('div');
          screen.className = 'preview-screen';
          screen.id = `screen-${p.id}`;
          if (p.screenshot) {
            screen.innerHTML = `<img src="/${escHtml(p.screenshot)}" alt="${escHtml(p.title)}" loading="lazy">`;
          } else {
            screen.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;background:var(--bg-card);font-family:var(--font-mono);font-size:0.75rem;color:var(--text-tertiary);">${escHtml(p.title)}</div>`;
          }
          previewViewport.appendChild(screen);
        }

        // Add to metadata
        projectMeta[p.id] = {
          url: p.preview_url || p.live_url || '',
          metrics: p.preview_metrics || p.metrics || [],
        };
      });

      // Update hero stats
      const totalCount = staticCount + dynamicProjects.length;
      const statNum = document.querySelector('.hero-stat .hs-num');
      if (statNum) statNum.textContent = String(totalCount).padStart(2, '0');

      // Re-bind interactivity for new rows
      bindProjectInteractivity();

    } catch (e) {
      // API not available (e.g., static server) — fail silently, static HTML is fine
    }
  }

  function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  loadDynamicProjects();
});
