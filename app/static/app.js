"use strict";

const toggle = document.getElementById("menu-toggle");
const sidebar = document.getElementById("thought-sidebar");
const closeMenu = document.getElementById("menu-close");
const backdrop = document.getElementById("drawer-backdrop");
const content = document.getElementById("main");
const header = document.querySelector(".product-header");
const smallScreen = window.matchMedia("(max-width: 760px)");
let desktopOpen = true;
try { desktopOpen = localStorage.getItem("afterthought-menu") !== "closed"; } catch (_) {}

function setMenu(open, restoreFocus = false) {
  const drawer = smallScreen.matches && open;
  sidebar.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
  closeMenu.hidden = !smallScreen.matches;
  backdrop.hidden = !drawer;
  content.inert = drawer;
  header.inert = drawer;
  document.body.classList.toggle("drawer-open", drawer);
  if (drawer) {
    sidebar.setAttribute("role", "dialog");
    sidebar.setAttribute("aria-modal", "true");
    closeMenu.focus();
  } else {
    sidebar.removeAttribute("role");
    sidebar.removeAttribute("aria-modal");
    if (restoreFocus) toggle.focus();
  }
}

toggle.hidden = false;
document.body.classList.add("menu-ready");
setMenu(smallScreen.matches ? false : desktopOpen);
toggle.addEventListener("click", () => {
  const open = sidebar.hidden;
  setMenu(open);
  if (!smallScreen.matches) {
    desktopOpen = open;
    try { localStorage.setItem("afterthought-menu", open ? "open" : "closed"); } catch (_) {}
  }
});
closeMenu.addEventListener("click", () => setMenu(false, true));
backdrop.addEventListener("click", () => setMenu(false, true));
sidebar.addEventListener("keydown", event => {
  if (!smallScreen.matches || sidebar.hidden) return;
  if (event.key === "Escape") setMenu(false, true);
  if (event.key === "Tab") {
    const links = sidebar.querySelectorAll("button, a[href]");
    const first = links[0], last = links[links.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  }
});
sidebar.addEventListener("click", event => {
  if (smallScreen.matches && event.target.closest("a")) setMenu(false, true);
});
smallScreen.addEventListener("change", () => setMenu(smallScreen.matches ? false : desktopOpen, true));
