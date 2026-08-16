/* ═══════════════════════════════════════════════════════════
   Theme toggle

   Shared by the home page and every generated project page, so the
   preference and the wiring can never drift apart between the two.

   The stored value is only ever "light" or "dark". Absent means "no
   choice made", which is deliberately different from either - it lets
   the CSS fall through to prefers-color-scheme and follow the OS.
   ═══════════════════════════════════════════════════════════ */

(function () {
  var KEY = 'theme';
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  if (!btn) return;

  function stored() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      // Private browsing and blocked storage both throw. The toggle
      // still works for the current page; it just will not persist.
      return null;
    }
  }

  // What the user is actually looking at right now, which is not the
  // same as what they picked: with nothing stored, the OS decides.
  function current() {
    var choice = stored();
    if (choice === 'light' || choice === 'dark') return choice;
    return window.matchMedia('(prefers-color-scheme: light)').matches
      ? 'light'
      : 'dark';
  }

  function label() {
    var next = current() === 'light' ? 'dark' : 'light';
    btn.setAttribute('aria-label', 'Switch to ' + next + ' theme');
  }

  btn.addEventListener('click', function () {
    var next = current() === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    try {
      localStorage.setItem(KEY, next);
    } catch (e) {
      /* not persistable; the attribute above still applies */
    }
    label();
  });

  // Follow the OS live, but only while the visitor has no explicit
  // preference of their own - overriding a deliberate choice because
  // the system went dark at sunset would be hostile.
  window
    .matchMedia('(prefers-color-scheme: light)')
    .addEventListener('change', function () {
      if (!stored()) label();
    });

  label();
})();
