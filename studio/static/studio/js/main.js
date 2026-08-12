const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".site-nav");

function closeMenu({ restoreFocus = false } = {}) {
  navigation?.classList.remove("open");
  menuButton?.setAttribute("aria-expanded", "false");
  menuButton?.setAttribute("aria-label", "Открыть меню");
  if (restoreFocus) menuButton?.focus();
}

menuButton?.setAttribute("aria-label", "Открыть меню");
menuButton?.addEventListener("click", () => {
  const isOpen = menuButton.getAttribute("aria-expanded") === "true";
  menuButton.setAttribute("aria-expanded", String(!isOpen));
  menuButton.setAttribute(
    "aria-label",
    isOpen ? "Открыть меню" : "Закрыть меню",
  );
  navigation?.classList.toggle("open", !isOpen);
});

navigation?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && navigation?.classList.contains("open")) {
    closeMenu({ restoreFocus: true });
  }
});

document.addEventListener("pointerdown", (event) => {
  if (!navigation?.classList.contains("open")) return;
  if (!navigation.contains(event.target) && !menuButton?.contains(event.target))
    closeMenu();
});

document.querySelectorAll('a[href="#top"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (["http:", "https:"].includes(window.location.protocol)) {
      history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}`,
      );
    }
  });
});

const dateInput = document.querySelector('input[type="date"]');
if (dateInput) {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  dateInput.min = `${year}-${month}-${day}`;
}

const revealItems = document.querySelectorAll(".reveal");
const reducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)",
).matches;

if (reducedMotion || !("IntersectionObserver" in window)) {
  revealItems.forEach((item) => item.classList.add("is-visible"));
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12 },
  );

  revealItems.forEach((item) => observer.observe(item));
}

document.querySelectorAll("[data-accordion]").forEach((accordionElement) => {
  const items = accordionElement.querySelectorAll(".faq-item");

  items.forEach((item) => {
    const button = item.querySelector(".faq-question");
    if (!button) return;

    button.addEventListener("click", () => {
      const willOpen = !item.classList.contains("is-open");

      items.forEach((otherItem) => {
        otherItem.classList.remove("is-open");
        otherItem
          .querySelector(".faq-question")
          ?.setAttribute("aria-expanded", "false");
      });

      if (willOpen) {
        item.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");
      }
    });
  });
});
