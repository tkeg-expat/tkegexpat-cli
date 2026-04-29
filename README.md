# TKEG Expat CLI — User Manual

**Version 0.5.0**

A simple tool that lets you look up TKEG Expat products, managed companies, tax data, and legal entity types from your computer's terminal (the black window where you type commands).

---

## Getting started

### Step 1 — Install

Open **Terminal** (on Mac, search for "Terminal" in Spotlight).

Copy and paste this line, then press **Enter**:

```
pip3 install --user git+https://github.com/tkeg-expat/tkegexpat-cli.git
```

Wait until you see "Successfully installed". This only needs to be done once.

> **If "tkegexpat" is not found after installing**, you may need to add it to your PATH. Paste this line and press Enter:
>
> ```
> echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
> ```
>
> Then try again.

### Step 2 — Log in

Type `tkegexpat` and press **Enter** to open the app. You'll see the TKEG Expat logo and a prompt:

```
tkegexpat>
```

Type `login` and press Enter. It will ask for your **email** and **password** (the same ones you use on tkegexpat.com). When you type your password, nothing will appear on screen — this is normal. Just type it and press Enter.

You only need to log in once. The tool remembers your credentials.

### Step 3 — You're ready

You're now inside the TKEG Expat environment. Just type commands at the `tkegexpat>` prompt — no need to type `tkegexpat` before each one.

Type `exit` when you're done. Type `restart` to reload the app (e.g. after an update).

---

## Commands

All commands below are typed at the `tkegexpat>` prompt. You do **not** need to type `tkegexpat` before each command.

### `login`

Log in with your email and password. Required before using any other command.

### `logout`

Log out and clear your saved credentials.

### `status`

Check whether you're logged in and if your session is still valid.

### `product <code>`

Look up products. The code is made of two parts:

- **Country** — a 2-letter code (e.g. `us` for United States, `gb` for United Kingdom, `hk` for Hong Kong)
- **Service** — a 2-letter code for the type of service

**Example:** To find company incorporation products in the US:

```
tkegexpat> product usci
```

This shows a table of matching products with their names, prices, and IDs.

#### Service codes

| Code | Service |
|------|---------|
| ci | Company Incorporation |
| ba | Bank Account Opening |
| ac | Accounting |
| co | Consulting |
| rm | Ready-Made Company |
| ra | Registered Address |
| nd | Nominee Director |
| cs | Company Secretary |
| cd | Company Dissolution |
| tr | Tax Registration |
| sl | Special License |
| ar | Annual Return |
| ca | Company Amendment |
| af | Administration Fee |
| os | Other Services |

### `company <country> [status]`

Look up managed companies by country. Optionally filter by status.

```
tkegexpat> company us
tkegexpat> company hk live
tkegexpat> company gb expired
```

This shows a table of companies with their name, registration number (SIN), company ID, status, registration date, and tax ID.

Use `view <number>` to see full details for any company in the list.

### `view <number>`

After running `product`, `company`, or `legal-entity`, each result has a number (#). Use `view` with that number to see full details:

```
tkegexpat> product usci
tkegexpat> view 1
```

For **products**, this shows:
- Product and supply information (price, cost, estimated days)
- Memos (public and internal notes)
- Included services
- Required documents (grouped by entity type, with format, process, and notes)
- Requirements (conditions, supplier, related products, solution status)

For **companies**, this shows:
- Company information (ID, status, registration date, tax ID, jurisdiction)
- Prime entity details (name, type, contact info, address)
- Additional information (credentials, bank details, etc.)
- Due dates with linked products

For **legal entities**, this shows:
- Full entity details (liability, ownership, capital market participation)
- Director, shareholder, and capital requirements
- Memo and quick view

The `view` command automatically knows which list you queried last.

### `view-product <number>`

After viewing a company (which shows due dates), use this to see the full product details linked to a due date:

```
tkegexpat> company gb live
tkegexpat> view 1
tkegexpat> view-product 3
```

This opens the same product detail view as `product` → `view`, showing supply info, documents, requirements, etc.

### `resolve-requirement <number>`

After running `view` on a product, if a requirement has a solution (Solution = "Yes"), you can drill into it to find the products that resolve it:

```
tkegexpat> product nlci
tkegexpat> view 1
tkegexpat> resolve-requirement 2
```

This searches for products matching the requirement's supplier, service type, and jurisdiction. If the viewed product applies to multiple jurisdictions, you'll be prompted to select one.

The results appear as a product table — you can then `view` any of them to see full details.

### `legal-entity <country>`

Look up legal entity types (company structures) available in a country.

```
tkegexpat> legal-entity us
```

This shows a table with each entity's abbreviation, full name, limited liability status, and capital market participation.

Use `view <number>` to see full details for any entity in the list.

```
tkegexpat> legal-entity us
tkegexpat> view 3
```

### `cit <country>`

Look up corporate income tax information for a country.

```
tkegexpat> cit gb
```

This shows:
- CIT rate, VAT rate, capital gains tax
- CIT payment and return due dates
- Withholding tax rates for residents and non-residents (dividend / interest / royalty)
- Effective average and marginal tax rates (OECD)
- All tax feature details in a table

### `vat <country>`

Look up VAT / sales tax rates for a country.

```
tkegexpat> vat gb
```

This shows all VAT rate entries with their name, type, rate percentage, active status, and description.

### `update`

Update the tool to the latest version. The tool also checks for updates automatically on startup.

### `restart`

Restart the app. Useful after an update to load the new version without closing and reopening your terminal.

### `help`

Show a quick reference of all commands.

### `exit`

Close the app.

---

## Common country codes

| Code | Country |
|------|---------|
| us | United States |
| gb | United Kingdom |
| hk | Hong Kong |
| sg | Singapore |
| ie | Ireland |
| nl | Netherlands |
| de | Germany |
| jp | Japan |
| kr | South Korea |
| au | Australia |
| ca | Canada |
| fr | France |

---

## Troubleshooting

**"command not found" when typing `tkegexpat`**
You need to add the install location to your PATH. See the note in Step 1 above.

**"Not logged in"**
Type `login` first.

**Screen looks garbled or has weird characters**
Make sure you're using a modern terminal (the default Terminal app on Mac works fine). Some very old terminal programs don't support the formatting this tool uses.

**Want to update to the latest version**
Type `update`.

**Forgot your password**
Reset it on tkegexpat.com, then type `login` again with the new password.
