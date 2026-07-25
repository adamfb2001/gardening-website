# The Allrounders — garden care & general labour website

A simple, fast, fully static marketing site for a business that offers
garden maintenance alongside general household labour — furniture
assembly, heavy lifting, and odd jobs.

No build step, no dependencies:

| File | Page |
|---|---|
| `index.html` | Landing page — hero, services, why-us, results, call-to-action |
| `contact.html` | **Booking page** — pick a date, describe the job, attach photos |
| `thank-you.html` | Confirmation page shown after a booking is submitted |
| `css/styles.css` | All styling (dark green with gradient accents, fully responsive) |
| `js/main.js` | Mobile menu, scroll reveals, date limits, photo preview, form validation |

## View it locally

Open `index.html` in a browser, or serve the folder:

```bash
cd docs
python3 -m http.server 8000
# then open http://localhost:8000
```

## The booking form (important — one-time setup)

The booking page lets a customer **pick a preferred date, choose the services
they need, describe the work, and attach photos**. Everything — including the
photos — is emailed to you.

Because the site is static (no server of its own), the form posts to
[**FormSubmit.co**](https://formsubmit.co) — a free service, no account needed,
that supports photo attachments. To turn it on:

1. **Set your email.** In `contact.html`, change the form's `action`:
   ```html
   <form ... action="https://formsubmit.co/YOUR-EMAIL@example.com" ...>
   ```
   (It currently uses FormSubmit's random alias for
   `ikonize.business@gmail.com` so the real address isn't exposed in the page
   source — it routes to the same inbox.)

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
  they go over.
- **Availability:** the date picker only allows future dates and blocks Sundays
  (open Mon–Sat), and the time field offers hourly slots from 8am–6pm. It's a
  *requested* date/time — the booking email asks the customer to wait for your
  confirmation.
- **Spam:** a hidden honeypot field blocks most bots. To add FormSubmit's
  captcha, set the hidden `_captcha` field to `true` in `contact.html`.
- **Privacy:** once live, you can swap the raw email in `action` for the random
  alias FormSubmit gives you after activation (e.g.
  `https://formsubmit.co/abc123…`) so your address isn't visible in the page.

## Deploying to theallrounders.co.uk (GitHub Pages)

This repo is set up for GitHub Pages, serving from the `docs/` folder on the
default branch, with a `docs/CNAME` file pointing at `theallrounders.co.uk`.

1. **On GitHub:** repo → **Settings → Pages** → set *Source* to your default
   branch, folder **`/docs`**. GitHub will pick up the `CNAME` file and offer
   to set `theallrounders.co.uk` as the custom domain — confirm it, and tick
   **Enforce HTTPS** once the certificate has provisioned (can take a bit
   after DNS is live).

2. **At your domain registrar (where you bought theallrounders.co.uk):**
   add these DNS records so the domain points at GitHub Pages:

   | Type | Host | Value |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `adamfb2001.github.io.` |

   DNS changes can take anywhere from a few minutes to a few hours to
   propagate.

Any other static host also works — Netlify, Vercel, Cloudflare Pages, or an
ordinary web server — just point it at the `docs/` folder and set the custom
domain there instead.

## Customising

- **Business name, phone, email, hours** — search/replace `The Allrounders`,
  the `tel:` / `mailto:` links, and the opening hours across the HTML files.
- **Colours** — edit the CSS variables at the top of `css/styles.css`.
- **Services** — edit the `.card` blocks in `index.html` (grouped into
  "Garden work" and "House & labour work") and the service checkboxes in
  `contact.html`.
