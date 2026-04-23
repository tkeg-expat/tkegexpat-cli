# TKEG Expat CLI — User Manual

**Version 0.2.0**

A simple tool that lets you look up TKEG Expat products and services from your computer's terminal (the black window where you type commands).

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

Type this and press **Enter**:

```
tkegexpat login
```

It will ask for your **email** and **password** (the same ones you use on tkegexpat.com). When you type your password, nothing will appear on screen — this is normal. Just type it and press Enter.

You only need to log in once. The tool remembers your credentials.

### Step 3 — You're ready

Type `tkegexpat` by itself to enter interactive mode, or type commands directly (see below).

---

## Commands

### `tkegexpat`

Opens interactive mode. You'll see the TKEG Expat logo and a prompt (`tkegexpat>`). Type commands without the `tkegexpat` prefix. Type `exit` to leave.

### `tkegexpat login`

Log in with your email and password. Required before using any other command.

### `tkegexpat logout`

Log out and clear your saved credentials.

### `tkegexpat status`

Check whether you're logged in and if your session is still valid.

### `tkegexpat product <code>`

Look up products. The code is made of two parts:

- **Country** — a 2-letter code (e.g. `us` for United States, `gb` for United Kingdom, `hk` for Hong Kong)
- **Service** — a 2-letter code for the type of service

**Example:** To find company incorporation products in the US:

```
tkegexpat product usci
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

### `tkegexpat view <number>`

After running `product`, each result has a number (#). Use `view` with that number to see full details:

```
tkegexpat product usci
tkegexpat view 1
```

This shows:
- Product and supply information (price, cost, estimated days)
- Memos (public and internal notes)
- Included services
- Required documents (grouped by entity type, with format, process, and notes)
- Requirements (conditions, supplier, related products)

### `tkegexpat update`

Update the tool to the latest version. Run this whenever a new version is announced.

### `tkegexpat help`

Show a quick reference of all commands.

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
Run `tkegexpat login` first.

**Screen looks garbled or has weird characters**
Make sure you're using a modern terminal (the default Terminal app on Mac works fine). Some very old terminal programs don't support the formatting this tool uses.

**Want to update to the latest version**
Run `tkegexpat update`.

**Forgot your password**
Reset it on tkegexpat.com, then run `tkegexpat login` again with the new password.
