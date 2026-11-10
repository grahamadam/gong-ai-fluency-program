/* Gong brand layer 0.2.0, generated from the Gong Design System (tokens sha256 ba03ed6046a7). fingerprint sha256:058e6681e0b4f01ff7e216730b5ea32455724d21b7dfafb1a619768b83e28532. Do not edit: regenerate. */
(function () {
  var theme = "light";
  try {
    var script = document.currentScript;
    var key = script ? script.getAttribute("data-storage-key") : null;
    var list = script ? script.getAttribute("data-themes") : null;
    var allowed = String(list || "light dark").split(/\s+/);
    if (key) {
      var saved = window.localStorage.getItem(key);
      if (saved && allowed.indexOf(saved) !== -1) {
        theme = saved;
      }
    }
  } catch (error) {
    theme = "light";
  }
  try {
    document.documentElement.dataset.theme = theme;
  } catch (error) {
  }
})();
