/* Verdant Grounds — small progressive-enhancement helpers.
   No dependencies; everything degrades gracefully if JS is off. */
(function () {
  "use strict";

  /* ----- Current year in the footer ----- */
  document.querySelectorAll("#year").forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  /* ----- Mobile navigation toggle ----- */
  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("primary-nav");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });

    // Close the menu after tapping a link (mobile).
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Open menu");
      });
    });
  }

  /* ----- Reveal-on-scroll ----- */
  var revealTargets = document.querySelectorAll(
    ".card, .stat, .why-list li, .section-head, .info-card, .contact-form-wrap"
  );
  if ("IntersectionObserver" in window && revealTargets.length) {
    revealTargets.forEach(function (el) {
      el.classList.add("reveal");
    });
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    revealTargets.forEach(function (el) {
      io.observe(el);
    });
  }

  /* ----- Contact form handling -----
     This is a static site, so there is no server to receive the message.
     We validate client-side and show a friendly confirmation. To make it
     live, point the <form> at a service such as Formspree / Netlify Forms,
     or wire the fetch() below to your own endpoint. */
  var form = document.getElementById("contact-form");
  var status = document.getElementById("form-status");

  if (form && status) {
    var showStatus = function (message, type) {
      status.textContent = message;
      status.className = "form-status " + type;
      status.hidden = false;
    };

    var isEmail = function (value) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    };

    form.addEventListener("submit", function (event) {
      event.preventDefault();

      var name = form.name;
      var email = form.email;
      var message = form.message;
      var consent = form.consent;

      // Clear previous invalid states.
      [name, email, message].forEach(function (field) {
        field.classList.remove("invalid");
      });
      consent.closest(".field-check").classList.remove("invalid");

      var firstInvalid = null;

      if (!name.value.trim()) {
        name.classList.add("invalid");
        firstInvalid = firstInvalid || name;
      }
      if (!isEmail(email.value.trim())) {
        email.classList.add("invalid");
        firstInvalid = firstInvalid || email;
      }
      if (!message.value.trim()) {
        message.classList.add("invalid");
        firstInvalid = firstInvalid || message;
      }
      if (!consent.checked) {
        consent.closest(".field-check").classList.add("invalid");
        firstInvalid = firstInvalid || consent;
      }

      if (firstInvalid) {
        showStatus("Please check the highlighted fields and try again.", "error");
        firstInvalid.focus();
        return;
      }

      // Success (demo). Swap this block for a real submission when going live.
      var button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;

      showStatus(
        "Thanks, " + name.value.trim().split(" ")[0] +
          "! Your message has been received — we'll be in touch shortly. 🌿",
        "success"
      );
      form.reset();
      if (button) {
        window.setTimeout(function () {
          button.disabled = false;
        }, 1500);
      }
    });
  }
})();
