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

## The booking form

The booking page lets a customer **pick a preferred date, choose the services
they need, describe the work, and attach photos**. Everything — including the
photos — is emailed to you.

Because the site is static (no server of its own), the form posts to
[**Web3Forms**](https://web3forms.com) — a free service that emails submissions
straight to your inbox. There's **no activation step**: it works as soon as the
access key is in the form.

- **Destination inbox** is whatever email the access key was generated for
  (currently `ikonize.business@gmail.com`). To change it, generate a new key at
  [web3forms.com](https://web3forms.com) and replace the `access_key` value in
  `contact.html`.
- **The access key is safe to have in the page** — it only lets the form deliver
  to your verified inbox, and the hidden `botcheck` honeypot blocks spam bots.

### Good to know
- **Photo limit:** Web3Forms' free tier caps total attachments at about
  **5 MB** per submission. The form checks this in the browser and warns the
  customer if they go over. The booking's text details always come through even
  if photos are skipped.
- **Availability:** the date picker only allows future dates, and the time field
  offers weekday evening (5–8pm) or weekend daytime (8am–7pm) hourly slots. It's
  a *requested* date/time — the booking email asks the customer to wait for your
  confirmation.
- **Thank-you page:** on success Web3Forms redirects to `thank-you.html` (set via
  the hidden `redirect` field, which the script points at the current domain).
- **Send to more than one inbox:** upgrade options and multi-recipient routing
  are configured in your Web3Forms dashboard.

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
