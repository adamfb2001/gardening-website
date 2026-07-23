# Verdant Grounds — gardening business website

A simple, fast, fully static marketing site for a gardening business that
offers soil maintenance, de-weeding, planting and general garden care.

No build step, no dependencies:

| File | Page |
|---|---|
| `index.html` | Landing page — hero, services, why-us, results, call-to-action |
| `contact.html` | **Booking page** — pick a date, describe the job, attach garden photos |
| `thank-you.html` | Confirmation page shown after a booking is submitted |
| `css/styles.css` | All styling (green, nature-forward, fully responsive) |
| `js/main.js` | Mobile menu, scroll reveals, date limits, photo preview, form validation |

## View it locally

Open `index.html` in a browser, or serve the folder:

```bash
cd documents
python3 -m http.server 8000
# then open http://localhost:8000
```

## The booking form (important — one-time setup)

The booking page lets a customer **pick a preferred date, choose the services
they need, describe the work, and attach photos of their garden**. Everything —
including the photos — is emailed to you.

Because the site is static (no server of its own), the form posts to
[**FormSubmit.co**](https://formsubmit.co) — a free service, no account needed,
that supports photo attachments. To turn it on:

1. **Set your email.** In `contact.html`, change the form's `action`:
   ```html
   <form ... action="https://formsubmit.co/YOUR-EMAIL@example.com" ...>
   ```
   (It currently points at `adamfbrown2001@gmail.com` — change it to the inbox
   that should receive bookings.)

2. **Activate once.** The first time the form is submitted, FormSubmit emails
   you a confirmation link. Click it once — after that, bookings arrive
   automatically. (Do a test submission yourself to trigger this.)

3. **Send to more than one inbox (optional).** Add addresses to the hidden
   `_cc` field in `contact.html`:
   ```html
   <input type="hidden" name="_cc" value="second@example.com,third@example.com" />
   ```

### Good to know
- **Photo limit:** FormSubmit's free tier attaches up to **10 MB total** per
  submission. The form checks this in the browser and warns the customer if
  they go over. (Phone photos are large — 2–4 clear pictures is usually fine.)
- **Availability:** the date picker only allows future dates and blocks Sundays
  (open Mon–Sat). It's a *requested* date — the booking email asks the customer
  to wait for your confirmation, which suits a "free visit / quote" business.
  If you ever want true real-time calendar availability with locked time slots,
  use [Cal.com](https://cal.com) for scheduling — but note Cal.com can't collect
  photo uploads, so you'd gather photos separately.
- **Spam:** a hidden honeypot field blocks most bots. To add FormSubmit's
  captcha, set the hidden `_captcha` field to `true` in `contact.html`.
- **Privacy:** once live, you can swap the raw email in `action` for the random
  alias FormSubmit gives you after activation (e.g.
  `https://formsubmit.co/abc123…`) so your address isn't visible in the page.

## Deploying

Any static host works — GitHub Pages, Netlify, Vercel, Cloudflare Pages, or an
ordinary web server. For GitHub Pages, point Pages at this `documents/` folder
(or move the files to the repo root / `docs/`). The form's post-submit redirect
figures out your domain automatically, so it works on any host.

## Customising

- **Business name, phone, email, hours** — search/replace `Verdant Grounds`,
  the `tel:` / `mailto:` links, and the opening hours across the HTML files.
- **Colours** — edit the CSS variables at the top of `css/styles.css`.
- **Hero photo** — swap the `background-image` URL on `.hero-photo` in the CSS
  for your own image (a green gradient fallback shows if it can't load).
- **Services** — edit the `.card` blocks in `index.html` and the service
  checkboxes in `contact.html`.
