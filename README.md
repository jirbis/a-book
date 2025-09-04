<!-- markdownlint-disable MD013 -->
# Book Publishing Pipeline

This repository contains a Markdown-based book source and an automated publishing pipeline powered by GitHub Actions and Pandoc. The book is built automatically into HTML, EPUB, and PDF formats with every push to the `main` branch and tested on every pull request.

## 🧪 CI Workflow: Test and Build

### ✅ Triggers:
- On **pull request** → run `test` jobs (lint, link check, build smoke test)
- On **push to `main`** → run `test` and full `build` (HTML, EPUB, PDF)

### 🧾 Jobs Overview

#### 🔍 `test` job

Runs on every PR and on main push:
- ✅ **Checkout** repository
- ✅ **Markdownlint** via `markdownlint-cli2` to enforce style
- ✅ **Link check** via `lychee` to validate all URLs
- ✅ **Pandoc smoke test**: builds HTML preview of book to ensure structure is valid

#### 📦 `build` job

Runs **only on push to `main`**:
- ✅ Build full **HTML** version of the book
- ✅ Build **EPUB** version (with embedded styles and cover image)
- ✅ Build **PDF** version using LaTeX backend (`xelatex`)
- ✅ Upload all formats as GitHub Actions artifacts

## 🔧 Output

All formats are built into the `build/` folder:
```text
build/book.html
build/book.epub
build/book.pdf
```

These are available under GitHub Actions → Artifacts after successful `main` push.

## Directory structure

```text
book/
├── 00-front-matter.md
├── 1-chapter-1.md
├── styles/
│   ├── book.css
│   └── fonts.css
│
├── images/
│   └── placeholder-illustration-1.png
│   └── cover.png
metadata/
├── metadata.yaml
├── pub-metadata.xml

.github/
├── workflows/build.yml
├── ISSUE_TEMPLATE.md
└── pull_request_template.md
```

## 📦 Dependencies

- [Pandoc](https://pandoc.org)
- [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2)
- [lychee](https://github.com/lycheeverse/lychee)
- [LaTeX (via xelatex)](https://www.latex-project.org/)

## ✅ Local build

```bash
make all      # builds HTML, EPUB, PDF
make html     # only HTML
make epub     # only EPUB
make pdf      # only PDF
```

Output is written into \`build/\`.

## CI/CD workflow

- On merge to main branch:
  - Run tests (Markdown lint, link check, pandoc smoke build).
  - Build HTML, EPUB, PDF.
  - Upload as artifacts.

## Conventions

- Each chapter is a separate .md file in \`book/\`.
- Stylesheets and fonts live under \`book/styles/\`.
- Metadata in \`metadata/metadata.yaml\`.
- Drafts in feature branches; merging PR to \`main\` = production release.
