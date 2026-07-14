# TKEG Expat CLI — User Manual

**Version 0.22.0**

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

### Step 2 — Open the app

Type `tkegexpat` and press **Enter** to open the app. You'll see the TKEG Expat logo and a prompt:

```
tkegexpat>
```

Public lookup commands can run without logging in. Type `login` only when you need protected account data. It will ask for your **email** and **password** (the same ones you use on portal.tkegexpat.com). When you type your password, nothing will appear on screen — this is normal. Just type it and press Enter.

> **Note on languages:** When you are **not** logged in, results are shown as the raw bilingual text stored in the database (both English and Chinese together). Once you **log in**, results are shown in your account's language (English by default).

You only need to log in once. The tool remembers your credentials.

### Step 3 — You're ready

You're now inside the TKEG Expat environment. Just type commands at the `tkegexpat>` prompt — no need to type `tkegexpat` before each one.

Type `exit` when you're done. Type `restart` to reload the app (e.g. after an update).

---

## Commands

All commands below are typed at the `tkegexpat>` prompt. You do **not** need to type `tkegexpat` before each command.

### `login`

Log in with your email and password. Public lookup commands can run without it; protected account data and write actions still require it.

### `logout`

Log out and clear your saved credentials.

### `status`

Check whether you're logged in and if your session is still valid.

### `user`

Show the profile of the account you're currently logged in as. Requires login.

```
tkegexpat> user
```

This shows your name, TKEG user ID, login email, user type, entity, jurisdiction, language, currency, account status, and the ids of your linked **CRM / RD / admin / client** entities (whichever apply to your account).

### `product <code | slug | id>`

Look up products. You can pass any of three things:

**1. A service code** — lists every matching product. The code is made of two parts:

- **Country** — a 2-letter code (e.g. `us` for United States, `gb` for United Kingdom, `hk` for Hong Kong)
- **Service** — a 2-letter code for the type of service (see the table below)

```
tkegexpat> product usci
```

This shows a table of matching products with their names, prices, and IDs. Use `view <number>` to open one.

**2. A product slug** — opens that one product directly (no list step):

```
tkegexpat> product united-kingdom-accounting-1
```

**3. A product ID** (the internal `_id`) — also opens that one product directly:

```
tkegexpat> product 1707576750806x567280454812041200
```

Because a slug or ID matches exactly one product, the tool skips the list and jumps straight to the full product detail view (the same view you get from `product usci` → `view 1`).

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

### `company <country | id> [status]`

Look up managed companies in one of two ways.

**1. By country** — lists every managed company in that country, optionally filtered by status:

```
tkegexpat> company us
tkegexpat> company hk live
tkegexpat> company gb expired
```

This shows a table of companies with their name, registration number (SIN), company ID, status, registration date, and tax ID. Use `view <number>` to see full details for any company in the list.

**2. By company ID** — opens one company directly (no list step), using either its **TKEG company ID** or its internal **`_id`**:

```
tkegexpat> company 1111111120
tkegexpat> company 1702587118257x231937979278314720
```

Because an ID matches exactly one company, the tool skips the list and jumps straight to the full company detail view (the same view you get from `company us` → `view 1`). This mirrors how `product` accepts a slug or `_id`.

### `project <code | id | slug>`

Look up client projects in one of two ways.

**1. By service code** — lists every project in a country for a service type, using the same `<country><service>` code as `product` (e.g. `usci` = US company-incorporation):

```
tkegexpat> project usci
tkegexpat> project nlac
```

This shows a simplified table with each project's name, TKEG project ID, service type(s), country, total value, and progress. Use `view <number>` to open one.

#### Filtering a list by CRM or client

The list forms of `project`, `project-item`, `company`, and `cos` accept two optional filters:

```
tkegexpat> project usci --crm 1709124866674x995775865500729300
tkegexpat> company us --client 2803639004
tkegexpat> cos usac project --crm <_id> --client <_id>
```

- `--crm <_id>` — the CRM entity's `_id` (copy it from the `crm` directory or a detail view).
- `--client <_id | tkeg-id>` — the client's `_id`, **or** its TKEG id (a number like `2803639004`), which the tool resolves to the `_id` for you (Bubble constraints only accept `_id`s).

**2. By project ID** — opens one project directly (no list step), using either its internal **`_id`** or its **TKEG project ID** (which, for projects, is the same value as the **slug**):

```
tkegexpat> project 4922376208
tkegexpat> project 1705400923505x291076600717843600
```

Use `view <number>` to open a project's full detail. The detail view shows:

- **Basic info** — name, TKEG project ID, service type(s), country, status, progress, total value, profit, start date, and end date (the project has no end-date field of its own, so it is derived from the latest project-item end date)
- **Entities** — client, TKEG, CRM, and company entities, each shown as its resolved entity name over its UID
- **Project items** — name, service, quantity, status, start date, end date, and price
- **Invoices** — invoice ID, status, pre-tax / tax / total amounts, and issue date
- **Contracts** — name, status, value, and generation / finalization dates

From within a project detail, open a specific row of any of those tables:

```
tkegexpat> view-project-item 1     open item #1
tkegexpat> view-invoice 2          open invoice #2
tkegexpat> view-contract 1         open contract #1  (then view-content for its text)
```

### `project-item <code | id> [status]`

Look up individual project items (the line items that make up projects).

**1. By service code** — lists items in a country for a service type, using the same `<country><service>` code, with an optional status filter:

```
tkegexpat> project-item usci
tkegexpat> project-item usci completed
```

This shows a table of items with name, service, quantity, status, start / end dates, and price. The status option set for items is **Completed, Lost, Paused, Refunded, Credit** (different from a project's status). Use `view <number>` to open one.

**2. By item ID** — opens one item directly by its internal **`_id`** (project items have no slug or short id):

```
tkegexpat> project-item 1711510007997x965481436808478700
```

The item detail shows its status, service, country, quantity, dates, belonging project, product, full pricing / cost / profit, and its client, CRM, supplier, and RD entities (each resolved to its entity name over its UID).

### `cos <code | id> [status]`

Look up **check-out sessions** (the sales / lead sessions that can convert to projects). Read-only.

**1. By service code** — lists sessions in a country for a service type, with an optional status filter:

```
tkegexpat> cos usac
tkegexpat> cos usac project
```

This shows a table of sessions with date, status, main product, and unit price. The status option set for sessions is **ARCHIVED, PROJECT, LOST** (its own set). Use `view <number>` to open one.

**2. By session ID** — opens one session directly by its internal **`_id`**:

```
tkegexpat> cos 1715569179354x662628426944610300
```

The session detail shows status, service, country, main product, unit price, CRM, user, dates — and a table of its session items (product, quantity, sum).

### `invoice <invoice-id | _id>`

Opens one invoice directly by its **invoice-id** (the short numeric id) or its internal **`_id`**:

```
tkegexpat> invoice 1111111114
tkegexpat> invoice 1777069193142x368449971970985500
```

The detail shows status, currency, pre-tax / tax / total, issue date, Stripe invoice id, belonging project, TKEG entity, and who issued it — plus a table of the invoice's line items (product, quantity, unit, pre-tax, tax, total).

### `contract <_id>`

Opens one contract directly by its internal **`_id`** (contracts have no short id):

```
tkegexpat> contract 1777069271956x625453515163327900
```

The detail shows name, status, currency, value, generation / finalization dates, the associated project, and a table of signing parties (each resolved to its entity name).

### `message [next]`

While viewing a **project**, **project item**, or **company** detail, show that entity's messages (newest first). A project item shows its belonging project's messages. Because there can be thousands of messages, they are paged — 20 at a time:

```
tkegexpat> company 1111111140
tkegexpat> message           show the first page
tkegexpat> message next      show the next page
```

Each row shows the date, sender, and message text.

### `crm` · `rd` · `admin`

Browse the internal team-entity directory (read-only). Each command works the same way:

```
tkegexpat> crm                                open the CRM directory (all entities)
tkegexpat> view 1                             open the first one
tkegexpat> crm 1709124866674x995775865500729300   open one directly by its _id
```

- `crm` — CRM entities · `rd` — RD operator entities · `admin` — admin entities

The list shows each entity's name, email, and authorized jurisdictions. The detail adds portal user, WeCom ID, who they report to, points, and type-specific fields (CRM: languages, active, busy rate, pending leads/projects; RD: authorized services, busy rate, on-going items). Passing an `_id` (e.g. one you copied from a project or company detail) opens that entity directly.

### `client`

Look up clients (read-only). There are ~660 clients, so there is **no bare list** — you must either scope by CRM or open one directly:

```
tkegexpat> client --crm 1709124866674x995775865500729300   list that CRM's clients
tkegexpat> view 1                                          open the first one
tkegexpat> client 5745830949                               open one by TKEG id
tkegexpat> client 1709080924300x813296447888438500         open one by _id
```

The list shows each client's name, TKEG id, and active status. The detail adds the belonging CRM (resolved to its name), TKEG entity, miles, qualifying points, and linked user account(s). A numeric `--client`-style value is a TKEG id, resolved to the client's `_id` automatically.

### `view-content`

While viewing a contract, display its full text body — headings and clause lists rendered as readable, wrapped terminal text:

```
tkegexpat> contract 1777069271956x625453515163327900
tkegexpat> view-content
```

### `view <number>`

After running `product`, `company`, `project`, `project-item`, or `legal-entity`, each result has a number (#). Use `view` with that number to see full details:

```
tkegexpat> product usci
tkegexpat> view 1
```

For **products**, this shows:
- Product and supply information (price, cost, estimated days)
- Memos (public and internal notes)
- Included services
- Required documents (grouped by entity type, with format, process, and notes)
- Requirements (conditions, service type, solution status)

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

### `resolve <number>`

After viewing a product, use this to resolve one requirement into matching TKEG products:

```
tkegexpat> product nlci
tkegexpat> view 1
tkegexpat> resolve 1
```

The product view lists requirements but does not show sellable resolving products directly. `resolve` uses the requirement-resolution logic scoped to the country from the product search when available.

### `faq`

After viewing a product, use this to show the FAQs linked to that product's supply:

```
tkegexpat> product nlci
tkegexpat> view 1
tkegexpat> faq
```

This shows a table of FAQ questions and answers in your selected language.

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

### `tkeginfo`

List TKEG Expat's own group entities (the legal firms that make up the TKEG group). No login required.

```
tkegexpat> tkeginfo
```

This shows a table of every group entity with its **name**, **registered address**, and whether it is currently **active** (Yes / No). Active firms are listed first.

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

**"Not logged in" or "HTTP Error 401/403"**
The command needs protected API access. Type `login` first, then try again.

**Screen looks garbled or has weird characters**
Make sure you're using a modern terminal (the default Terminal app on Mac works fine). Some very old terminal programs don't support the formatting this tool uses.

**Want to update to the latest version**
Type `update`.

**Forgot your password**
Reset it on portal.tkegexpat.com, then type `login` again with the new password.
