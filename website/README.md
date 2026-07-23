# Verdant Grounds — gardening business website

A simple, fast, fully static marketing site for a gardening business that
offers soil maintenance, de-weeding, planting and general garden care.

Two pages, no build step, no dependencies:

| File | Page |
|---|---|
| `index.html` | Landing page — hero, services, why-us, results, call-to-action |
| `contact.html` | Contact page — enquiry form + contact details |
| `css/styles.css` | All styling (green, nature-forward, fully responsive) |
| `js/main.js` | Mobile menu, scroll reveals, contact-form validation |

## View it locally

Just open `index.html` in a browser, or serve the folder:

```bash
cd website
python3 -m http.server 8000
# then open http://localhost:8000
```

## Making the contact form live

The site is static, so the form currently validates in the browser and shows
a confirmation message — it does not send email on its own. To receive real
enquiries, choose one of:

- **Formspree** — set `<form action="https://formspree.io/f/your-id" method="POST">`
  in `contact.html` and remove the `event.preventDefault()` demo handler in
  `js/main.js`.
- **Netlify Forms** — add `netlify` to the `<form>` tag and deploy on Netlify.
- **Your own endpoint** — replace the success block in `js/main.js` with a
  `fetch()` POST to your backend.

## Deploying

Any static host works — GitHub Pages, Netlify, Vercel, Cloudflare Pages, or an
ordinary web server. For GitHub Pages, point Pages at this `website/` folder
(or move the files to the repo root / `docs/`).

## Customising

- **Business name, phone, email, hours** — search/replace `Verdant Grounds`,
  the `tel:` / `mailto:` links, and the opening hours in both HTML files.
- **Colours** — edit the CSS variables at the top of `css/styles.css`.
- **Hero photo** — swap the `background-image` URL on `.hero-photo` in the CSS
  for your own image (a green gradient fallback shows if it can't load).
- **Services** — edit the `.card` blocks in `index.html` and the `<select>`
  options in `contact.html`.
