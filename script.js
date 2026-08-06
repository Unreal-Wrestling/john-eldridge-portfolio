/* ═══════════════════════════════════════════════════════════
   Portfolio JS — Gallery, Lightbox, Video, Navigation
   ═══════════════════════════════════════════════════════════ */

// ── Design Work Gallery Items ──────────────────────────────
const galleryImages = [
  { file: 'Artboard 1.png',  title: 'Design Work — Artboard 1' },
  { file: 'Artboard 2.png',  title: 'Design Work — Artboard 2' },
  { file: 'Artboard 3.png',  title: 'Design Work — Artboard 3' },
  { file: 'Artboard 4.png',  title: 'Design Work — Artboard 4' },
  { file: 'Artboard 5.png',  title: 'Design Work — Artboard 5' },
  { file: 'Artboard 6.png',  title: 'Design Work — Artboard 6' },
  { file: 'Artboard 7.png',  title: 'Design Work — Artboard 7' },
  { file: 'Artboard 8.png',  title: 'Design Work — Artboard 8' },
  { file: 'Artboard 9.png',  title: 'Design Work — Artboard 9' },
  { file: 'Artboard 10.png', title: 'Design Work — Artboard 10' },
  { file: 'Artboard 11.png', title: 'Design Work — Artboard 11' },
  { file: 'Artboard 12.png', title: 'Design Work — Artboard 12' },
  { file: 'Artboard 13.png', title: 'Design Work — Artboard 13' },
  { file: 'Artboard 14.png', title: 'Design Work — Artboard 14' },
  { file: 'Artboard 15.png', title: 'Design Work — Artboard 15' },
  { file: 'Artboard 16.png', title: 'Design Work — Artboard 16' },
  { file: 'Artboard 17.png', title: 'Design Work — Artboard 17' },
  { file: 'Artboard 18.png', title: 'Design Work — Artboard 18' },
  { file: 'Artboard 19.png', title: 'Design Work — Artboard 19' },
  { file: 'Artboard 20.png', title: 'Design Work — Artboard 20' },
  { file: 'Artboard 21.png', title: 'Design Work — Artboard 21' },
  { file: 'Artboard 22.png', title: 'Design Work — Artboard 22' },
  { file: 'Artboard 23.png', title: 'Design Work — Artboard 23' },
  { file: 'Artboard 24.png', title: 'Design Work — Artboard 24' },
  { file: 'Artboard 25.png', title: 'Design Work — Artboard 25' },
  { file: 'Artboard 26.png', title: 'Design Work — Artboard 26' },
  { file: 'Artboard 27.png', title: 'Design Work — Artboard 27' },
  { file: 'Artboard 28.png', title: 'Design Work — Artboard 28' },
  { file: 'Artboard 29.png', title: 'Design Work — Artboard 29' },
  { file: 'Artboard Closer.png', title: 'Show Closer Graphic' },
];

// ── Video Showcase Items (YouTube embeds) ─────────────────
const videos = [
  {
    ytId: 'gyg35mU7aus',
    title: 'The Fireside Tales — Show Opener',
    tag: 'Show Opener',
    desc: 'Full broadcast show opener with animated graphics, logos, and motion design.',
  },
  {
    ytId: 'WhIOjFfgnic',
    title: 'The Fireside Tales — Show Closer',
    tag: 'Show Closer',
    desc: 'Roll-out show closer with credits-style motion graphics and brand wrap.',
  },
  {
    ytId: 'V6cnnZgSAPk',
    title: 'Saltmarsh Legends — Show Opener',
    tag: 'Show Opener',
    desc: 'Dynamic show opener featuring custom motion graphics and brand identity.',
  },
  {
    ytId: 'yZiTWRG1apA',
    title: 'Saltmarsh Legends — Show Closer',
    tag: 'Show Closer',
    desc: 'Professional show closer with smooth transitions and branded outro.',
  },
  {
    ytId: '0giAX8tfN8o',
    title: 'Battle Arena — Logo Sting',
    tag: 'Logo Sting',
    desc: 'Animated logo reveal sting — clean, punchy, brand-forward.',
  },
  {
    ytId: 'iAQ-h9bDehc',
    title: 'Frostmaidens — Logo Sting',
    tag: 'Logo Sting',
    desc: 'Custom animated logo sting with themed visual effects and sound design.',
  },
];

// ── Helpers ───────────────────────────────────────────────
function escapeAttr(str) {
  return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Build Gallery ──────────────────────────────────────────
const galleryEl = document.getElementById('gallery');
galleryImages.forEach((item, i) => {
  const div = document.createElement('div');
  div.className = 'gallery-item reveal';
  div.dataset.index = i;
  div.innerHTML = `<img src="${escapeAttr(item.file)}" alt="${escapeAttr(item.title)}" loading="lazy">`;
  div.addEventListener('click', () => openLightbox(i));
  galleryEl.appendChild(div);
});

// ── Build Video Cards ──────────────────────────────────────
const videoGridEl = document.getElementById('video-grid');
videos.forEach((v) => {
  const card = document.createElement('div');
  card.className = 'video-card reveal';
  card.innerHTML = `
    <div class="video-wrapper">
      <iframe
        src="https://www.youtube.com/embed/${escapeAttr(v.ytId)}?rel=0&modestbranding=1"
        title="${escapeAttr(v.title)}"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>
    <div class="video-info">
      <span class="video-tag">${escapeHtml(v.tag)}</span>
      <h3>${escapeHtml(v.title)}</h3>
      <p>${escapeHtml(v.desc)}</p>
    </div>
  `;
  videoGridEl.appendChild(card);
});

// ── Lightbox ───────────────────────────────────────────────
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxCounter = lightbox.querySelector('.lightbox-counter');
let currentIndex = 0;

function openLightbox(index) {
  currentIndex = index;
  updateLightbox();
  lightbox.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  lightbox.classList.remove('active');
  document.body.style.overflow = '';
}

function updateLightbox() {
  const item = galleryImages[currentIndex];
  lightboxImg.src = item.file;
  lightboxImg.alt = item.title;
  lightboxCounter.textContent = `${currentIndex + 1} / ${galleryImages.length}`;
}

function nextImage() {
  currentIndex = (currentIndex + 1) % galleryImages.length;
  updateLightbox();
}

function prevImage() {
  currentIndex = (currentIndex - 1 + galleryImages.length) % galleryImages.length;
  updateLightbox();
}

lightbox.querySelector('.lightbox-close').addEventListener('click', closeLightbox);
lightbox.querySelector('.lightbox-next').addEventListener('click', nextImage);
lightbox.querySelector('.lightbox-prev').addEventListener('click', prevImage);

lightbox.addEventListener('click', (e) => {
  if (e.target === lightbox) closeLightbox();
});

document.addEventListener('keydown', (e) => {
  if (!lightbox.classList.contains('active')) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowRight') nextImage();
  if (e.key === 'ArrowLeft') prevImage();
});

// ── Back to Top ────────────────────────────────────────────
const backToTop = document.getElementById('back-to-top');
window.addEventListener('scroll', () => {
  backToTop.classList.toggle('visible', window.scrollY > 400);
});
backToTop.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ── Mobile Nav ─────────────────────────────────────────────
const mobileNavToggle = document.getElementById('mobile-nav-toggle');
const mobileNav = document.getElementById('mobile-nav');
mobileNavToggle.addEventListener('click', () => {
  mobileNavToggle.classList.toggle('active');
  mobileNav.classList.toggle('open');
});
mobileNav.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    mobileNavToggle.classList.remove('active');
    mobileNav.classList.remove('open');
  });
});

// ── Scroll Reveal ──────────────────────────────────────────
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
);

document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));

// Also reveal section headers and about text
document.querySelectorAll('.section-header, .about-text, .contact-card').forEach((el) => {
  el.classList.add('reveal');
  observer.observe(el);
});
