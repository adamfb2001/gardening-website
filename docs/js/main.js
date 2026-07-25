/* The Allrounders — small progressive-enhancement helpers.
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
  // Never let the reveal animation hide the booking form for JS users whose
  // observer is slow to fire — the form is the whole point of the page.
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

  /* ----- Booking form -----
     The form posts to FormSubmit.co, which emails the booking (and any
     attached photos) to the business. We enhance it here: restrict the date
     picker, give feedback on chosen photos, validate before submitting, and —
     crucially — only block the native submit when something is actually wrong.
     When everything checks out we let the real POST through. */
  var form = document.getElementById("booking-form");
  var status = document.getElementById("form-status");

  if (form) {
    var MAX_BYTES = 10 * 1024 * 1024; // FormSubmit's 10 MB total attachment cap
    var dateInput = form.querySelector("#date");
    var photos = form.querySelector("#photos");
    var fileList = document.getElementById("file-list");
    var submitBtn = document.getElementById("booking-submit");

    var showStatus = function (message, type) {
      if (!status) return;
      status.textContent = message;
      status.className = "form-status " + type;
      status.hidden = false;
    };

    var isEmail = function (value) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    };

    var formatSize = function (bytes) {
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
      return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    };

    /* -- Restrict the date picker: earliest = tomorrow -- */
    if (dateInput) {
      var tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      dateInput.min = tomorrow.toISOString().split("T")[0];
    }

    /* -- Read the currently chosen photos as an array -- */
    var chosenFiles = function () {
      return photos && photos.files ? Array.prototype.slice.call(photos.files) : [];
    };

    var totalSize = function () {
      return chosenFiles().reduce(function (sum, f) { return sum + f.size; }, 0);
    };

    /* -- Show a friendly list of chosen photos + total size -- */
    if (photos && fileList) {
      photos.addEventListener("change", function () {
        var files = chosenFiles();
        fileList.innerHTML = "";
        if (!files.length) {
          fileList.hidden = true;
          return;
        }
        files.forEach(function (f) {
          var li = document.createElement("li");
          li.textContent = f.name + " (" + formatSize(f.size) + ")";
          fileList.appendChild(li);
        });
        var total = totalSize();
        var summary = document.createElement("li");
        summary.className = "file-total";
        summary.textContent =
          files.length + (files.length === 1 ? " photo · " : " photos · ") +
          formatSize(total) + " total";
        if (total > MAX_BYTES) {
          summary.textContent += " — too big, please remove some (10 MB max)";
          fileList.classList.add("over");
        } else {
          fileList.classList.remove("over");
        }
        fileList.appendChild(summary);
        fileList.hidden = false;
      });
    }

    form.addEventListener("submit", function (event) {
      // Look up by id: `form.name` would return the form's own name property,
      // not the <input name="name">, so query the controls explicitly.
      var name = form.querySelector("#name");
      var email = form.querySelector("#email");
      var details = form.querySelector("#details");
      var consent = form.querySelector("#consent");
      var firstInvalid = null;

      // Clear previous invalid states.
      [name, email, details, dateInput].forEach(function (field) {
        if (field) field.classList.remove("invalid");
      });
      consent.closest(".field-check").classList.remove("invalid");

      var mark = function (field) {
        if (field) field.classList.add("invalid");
        firstInvalid = firstInvalid || field;
      };

      if (dateInput && !dateInput.value) mark(dateInput);
      else if (dateInput) {
        // Reject past dates and Sundays (closed on Sundays).
        var picked = new Date(dateInput.value + "T00:00:00");
        var today = new Date();
        today.setHours(0, 0, 0, 0);
        if (picked < today || picked.getDay() === 0) mark(dateInput);
      }
      if (!name.value.trim()) mark(name);
      if (!isEmail(email.value.trim())) mark(email);
      if (!details.value.trim()) mark(details);
      if (!consent.checked) {
        consent.closest(".field-check").classList.add("invalid");
        firstInvalid = firstInvalid || consent;
      }

      // Photos are optional, but if attached they must fit FormSubmit's cap.
      var tooBig = totalSize() > MAX_BYTES;

      if (firstInvalid || tooBig) {
        event.preventDefault();
        if (tooBig && !firstInvalid) {
          showStatus("Your photos add up to more than 10 MB. Please remove a few or use smaller images.", "error");
          if (photos) photos.focus();
        } else {
          showStatus("Please check the highlighted fields. For the date, choose a future day (Mon–Sat).", "error");
          if (firstInvalid) firstInvalid.focus();
        }
        return;
      }

      // Valid — let the real POST to FormSubmit proceed.
      // Point the post-submit redirect at OUR thank-you page on whatever
      // domain the site is served from (works on any host / subpath).
      var next = document.getElementById("_next");
      if (next && /^https?:/.test(window.location.protocol)) {
        next.value = new URL("thank-you.html", window.location.href).href;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending…";
      }
      showStatus("Sending your booking request… 🛠️", "success");
      // (No preventDefault: the browser now submits the form for real.)
    });
  }
})();
