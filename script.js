/* ═══════════════════════════════════════════════════════════
   Portfolio JS — Gallery, Lightbox, Video, Navigation
   ═══════════════════════════════════════════════════════════ */

// ── Design Work Gallery Items ──────────────────────────────
// Categories mirror the three sections of the source portfolio deck.
// Deck title, section dividers, and the closing contact slide are
// intentionally omitted — the site already covers that ground.
const CATEGORIES = [
  { key: 'all',       label: 'All Work' },
  { key: 'merch',     label: 'Merch & Packaging' },
  { key: 'ad',        label: 'Ad & Event' },
  { key: 'marketing', label: 'Marketing Assets' },
];

const galleryImages = [
  // ── Section One — Merch & Packaging ──
  {
    file: 'Artboard 3.png',
    client: 'Asphalt Clothing',
    title: 'T-Shirt Merch Collection',
    category: 'merch',
    desc: 'A six-design apparel collection, each piece reinterpreting the brand\u2019s triangle logo — from bold and graphic to minimal and understated.',
  },
  {
    file: 'Artboard 4.png',
    client: 'Grenco Science',
    title: 'Vape Pen Packaging',
    category: 'merch',
    desc: 'A two-design packaging collection delivered with production-ready dielines: a blue watercolor series and a sleek brushed-aluminum finish.',
  },
  {
    file: 'Artboard 5.png',
    client: 'Red Bull Global Rallycross',
    title: 'T-Shirt Merch Designs',
    category: 'merch',
    desc: 'Four rally-racing merch designs using aggressive tread marks, mud lines, and a world map to capture the sport\u2019s speed and global reach.',
  },
  {
    file: 'Artboard 6.png',
    client: 'Rain City Brew',
    title: 'Porter Label & Package Design',
    category: 'merch',
    desc: 'Bottle label and six-pack carrier built on Pacific Northwest imagery — a lighthouse beacon cutting through Puget Sound storm clouds.',
  },
  {
    file: 'Artboard 7.png',
    client: 'Music Industry',
    title: 'Logo & Merch Designs',
    category: 'merch',
    desc: 'Apparel and logo work for Redman, Caviar Gold, Cavigold Records, Arisen From Nothing, Dead Kiss, The Rockefellers, and Jimmy Nuge.',
  },
  {
    file: 'Artboard 8.png',
    client: 'Arisen From Nothing / The Rockefellers',
    title: 'EP Album Covers',
    category: 'merch',
    desc: 'Front and back covers for two EPs, including logo design, track listings, band credits, and original cover photography.',
  },
  {
    file: 'Artboard 9.png',
    client: 'Action Sports',
    title: 'Logo & Merch Designs',
    category: 'merch',
    desc: 'Merch and branding for Vitalire, Stevens Pass, and Kash Vault Clothing — including a benefit design raising medical costs for a local PNW rider.',
  },

  // ── Section Two — Ad & Event ──
  {
    file: 'Artboard 11.png',
    client: 'Local Events',
    title: 'Poster & Handbill Designs',
    category: 'ad',
    desc: 'Poster and handbill designs across music, art, and comedy — including EMP semi-finals, Hard Rock Cafe, Splintered Throne, and the Big Fat Comedy Show.',
  },
  {
    file: 'Artboard 12.png',
    client: 'Buzz Inn Steakhouse',
    title: 'Social & Event Headers',
    category: 'ad',
    desc: 'Shareable social graphics and event headers for holiday promotions and menu specials across nine restaurant locations.',
  },
  {
    file: 'Artboard 13.png',
    client: 'Crypticon Seattle',
    title: 'Convention Poster & Magazine Ads',
    category: 'ad',
    desc: 'Poster and magazine ad campaign for the Pacific Northwest\u2019s largest horror convention, built around the 2014 celebrity guest lineup.',
  },
  {
    file: 'Artboard 14.png',
    client: 'Crypticon Seattle',
    title: 'Full Event Collateral',
    category: 'ad',
    desc: 'Two-year project scope: posters, magazine ads, handbills, event badges, drink vouchers, tickets, business cards, email banners, and the weekend-pass \u201cCertificate of Death.\u201d',
  },
  {
    file: 'Artboard 15.png',
    client: 'LEGIT Cannabis Co.',
    title: 'Handbill & Magazine Ad',
    category: 'ad',
    desc: 'Print campaign establishing the brand as a premium crafted pre-roll, carried from handbill through to a full-page magazine ad.',
  },
  {
    file: 'Artboard 16.png',
    client: 'Fantasy Wrestling Alliance',
    title: 'Event Header Series',
    category: 'ad',
    desc: 'Sixteen pay-per-view header designs ranging from bold and colorful to sleek and minimal, each themed to its event\u2019s season and tone.',
  },
  {
    file: 'Artboard 17.png',
    client: 'Fantasy Wrestling Alliance',
    title: 'Event Poster Series',
    category: 'ad',
    desc: 'Full-page poster and ad designs for marquee pay-per-view events, including full match-card typography.',
  },

  // ── Section Three — Marketing Assets ──
  {
    file: 'Artboard 19.png',
    client: 'Seaweed Cannabis Co.',
    title: 'Educational Display Slides',
    category: 'marketing',
    desc: 'A digital-display series breaking down terpenes — taste, experience, and effects — designed to make technical product information scannable in-store.',
  },
  {
    file: 'Artboard 20.png',
    client: 'Various',
    title: 'Document & Menu Design',
    category: 'marketing',
    desc: 'A to-go menu for The Hearty Galley plus employment applications, order forms, sponsor and press kits, product analysis forms, surveys, coupons, and letterheads.',
  },
  {
    file: 'Artboard 21.png',
    client: 'BizTech RX',
    title: 'Branding & Identity',
    category: 'marketing',
    desc: 'Complete identity rollout: logo, website, promotional mailers, door hangers, business cards, email banners, and stationery.',
  },
  {
    file: 'Artboard 22.png',
    client: 'Fantasy Wrestling Alliance',
    title: 'Branding & Identity',
    category: 'marketing',
    desc: 'The master FWA mark plus twelve individual promotion logos, each styled to a different era and attitude of pro wrestling.',
  },
  {
    file: 'Artboard 23.png',
    client: 'Fantasy Wrestling Alliance',
    title: 'Annual Awards Magazine Layout',
    category: 'marketing',
    desc: 'A multi-page year-end awards magazine designed as a deliberate homage to 1980s pro-wrestling print, using bold typography and muted color.',
  },
  {
    file: 'Artboard 24.png',
    client: 'Fantasy Wrestling Alliance',
    title: 'Report & Instruction Manual',
    category: 'marketing',
    desc: 'A weekly four-page commissioner report plus a four-page beginner\u2019s manual using step-by-step instructions and visual aids to make a complex ruleset approachable.',
  },
  {
    file: 'Artboard 25.png',
    client: 'Fantasy Wrestling Alliance',
    title: 'Patreon Membership Assets',
    category: 'marketing',
    desc: 'Membership tier graphics and channel banner in a black-and-gold system built to signal quality and value at every price point.',
  },
  {
    file: 'Artboard 26.png',
    client: 'Chronos World',
    title: 'Streaming Channel Identity',
    category: 'marketing',
    desc: 'A full weekly programming schedule with individual logo designs for ten shows, plus intro/outro stings, cover photos, and promotional graphics.',
  },
  {
    file: 'Artboard 27.png',
    client: 'Chronos World',
    title: 'Live Stream Overlays',
    category: 'marketing',
    desc: 'Custom broadcast overlays and character frames for live stream productions, each themed to its show\u2019s world and tone.',
  },
  {
    file: 'Artboard 28.png',
    client: 'Various Authors',
    title: 'Book Cover Design',
    category: 'marketing',
    desc: 'Three covers — a poetry collection, a chef\u2019s memoir, and a supernatural mystery — delivered as print-ready wraps with spine and dieline specs.',
  },
  {
    file: 'Artboard 29.png',
    client: '3G\u2019s Coffeeshop',
    title: 'Logo, Menu & Loyalty Cards',
    category: 'marketing',
    desc: 'Seaside identity built on the Westport Lookout Tower and jetty, with three gulls representing the three generations who run the shop.',
  },
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

// ── Build Gallery + Category Filters ───────────────────────
const galleryEl = document.getElementById('gallery');
const filtersEl = document.getElementById('gallery-filters');

let activeCategory = 'all';
// The set currently rendered — the lightbox navigates within this,
// so arrow keys stay inside the active filter.
let visibleImages = [];

function itemsFor(category) {
  return category === 'all'
    ? galleryImages
    : galleryImages.filter((item) => item.category === category);
}

function fullLabel(item) {
  return item.client ? `${item.client} — ${item.title}` : item.title;
}

function renderGallery() {
  visibleImages = itemsFor(activeCategory);
  galleryEl.innerHTML = '';
  visibleImages.forEach((item, i) => {
    const div = document.createElement('div');
    div.className = 'gallery-item';
    div.dataset.index = i;
    div.innerHTML = `
      <img src="${escapeAttr(item.file)}" alt="${escapeAttr(fullLabel(item))}" loading="lazy">
      <div class="gallery-caption">
        ${item.client ? `<span class="gallery-client">${escapeHtml(item.client)}</span>` : ''}
        <span class="gallery-title">${escapeHtml(item.title)}</span>
      </div>
    `;
    div.addEventListener('click', () => openLightbox(i));
    galleryEl.appendChild(div);
  });
}

function renderFilters() {
  if (!filtersEl) return;
  CATEGORIES.forEach((cat) => {
    const count = itemsFor(cat.key).length;
    if (!count) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'filter-btn' + (cat.key === activeCategory ? ' active' : '');
    btn.dataset.category = cat.key;
    btn.innerHTML = `${escapeHtml(cat.label)} <span class="filter-count">${count}</span>`;
    btn.addEventListener('click', () => {
      activeCategory = cat.key;
      filtersEl.querySelectorAll('.filter-btn').forEach((b) => {
        b.classList.toggle('active', b.dataset.category === activeCategory);
      });
      renderGallery();
    });
    filtersEl.appendChild(btn);
  });
}

renderFilters();
renderGallery();

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
const lightboxCaption = document.getElementById('lightbox-caption');
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
  const item = visibleImages[currentIndex];
  if (!item) return;
  lightboxImg.src = item.file;
  lightboxImg.alt = fullLabel(item);
  if (lightboxCaption) {
    lightboxCaption.innerHTML = `
      ${item.client ? `<span class="lightbox-client">${escapeHtml(item.client)}</span>` : ''}
      <span class="lightbox-title">${escapeHtml(item.title)}</span>
      ${item.desc ? `<span class="lightbox-desc">${escapeHtml(item.desc)}</span>` : ''}
    `;
  }
  lightboxCounter.textContent = `${currentIndex + 1} / ${visibleImages.length}`;
}

function nextImage() {
  if (!visibleImages.length) return;
  currentIndex = (currentIndex + 1) % visibleImages.length;
  updateLightbox();
}

function prevImage() {
  if (!visibleImages.length) return;
  currentIndex = (currentIndex - 1 + visibleImages.length) % visibleImages.length;
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
