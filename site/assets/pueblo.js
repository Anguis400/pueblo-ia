/* Progressive enhancement only. No requests, analytics, payments or fabricated activity. */
"use strict";
(() => {
  const map = document.querySelector(".village-panel");
  if (!map) return;
  const panels = [...document.querySelectorAll("[data-panel]")];
  const controls = [...document.querySelectorAll("[data-department]")];
  const all = document.getElementById("all-roles");
  const inspector = document.getElementById("inspector");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const zoneFromHash = () => {
    const hash = location.hash.replace("#departamento-", "");
    if (panels.some((panel) => panel.dataset.panel === hash)) return hash;
    const role = document.getElementById(location.hash.slice(1));
    return role?.closest("[data-panel]")?.dataset.panel || null;
  };
  function selectZone(key, userAction = false) {
    panels.forEach((panel) => {
      panel.hidden = key !== null && panel.dataset.panel !== key;
    });
    controls.forEach((control) => {
      if (control.dataset.department === key)
        control.setAttribute("aria-current", "true");
      else control.removeAttribute("aria-current");
    });
    if (all) {
      all.hidden = false;
      all.textContent = key === null ? "Volver a Producto" : "Ver los 21 roles";
    }
    if (userAction) {
      inspector.scrollTop = 0;
      const panel = panels.find((item) => item.dataset.panel === key);
      const heading = panel?.querySelector("h3");
      heading?.focus({ preventScroll: true });
      if (innerWidth < 981)
        inspector.scrollIntoView({
          block: "start",
          behavior: reducedMotion.matches ? "instant" : "smooth",
        });
    }
  }
  controls.forEach((control) =>
    control.addEventListener("click", (event) => {
      // Preserve native modifier-click and link behavior.
      if (
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey ||
        event.button > 0
      )
        return;
      event.preventDefault();
      const key = control.dataset.department;
      history.pushState(null, "", "#departamento-" + key);
      selectZone(key, true);
    }),
  );
  if (all)
    all.addEventListener("click", () => {
      const showAll = panels.some((panel) => panel.hidden);
      history.pushState(
        null,
        "",
        showAll ? "#todos-los-roles" : "#departamento-producto",
      );
      selectZone(showAll ? null : "producto");
      inspector.scrollTop = 0;
    });
  window.addEventListener("hashchange", () =>
    selectZone(
      location.hash === "#todos-los-roles"
        ? null
        : zoneFromHash() || "producto",
    ),
  );
  window.addEventListener("popstate", () =>
    selectZone(
      location.hash === "#todos-los-roles"
        ? null
        : zoneFromHash() || "producto",
    ),
  );
  selectZone(
    location.hash === "#todos-los-roles" ? null : zoneFromHash() || "producto",
  );
  const linkedRole = document.getElementById(location.hash.slice(1));
  if (linkedRole?.matches("details.role-card")) linkedRole.open = true;

  const toggle = document.getElementById("motion-toggle");
  let paused = reducedMotion.matches;
  function syncMotion() {
    map.classList.toggle("motion-paused", paused);
    if (!toggle) return;
    toggle.hidden = false;
    toggle.disabled = reducedMotion.matches;
    toggle.setAttribute("aria-pressed", String(paused));
    toggle.querySelector("span").textContent = reducedMotion.matches
      ? "Movimiento reducido"
      : paused
        ? "Activar movimiento"
        : "Pausar movimiento";
  }
  toggle?.addEventListener("click", () => {
    paused = !paused;
    syncMotion();
  });
  reducedMotion.addEventListener("change", () => {
    paused = reducedMotion.matches;
    syncMotion();
  });
  syncMotion();
})();
