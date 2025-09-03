<!-- markdownlint-disable MD013 -->
# Book Publishing Pipeline

This repository contains the source files and build system for a Markdown-first book. The goal is to treat the text and layout as code so that you can collaborate via pull requests, run automated tests on your chapters, and build reproducible releases in multiple formats (HTML, EPUB and PDF).

## Directory structure

```text
book-repo/
├── book/              # Markdown chapters and assets
│   ├── 00-front-matter.md
│   ├── 1-chapter-1.md
│   └── styles/        # CSS and fonts for HTML/EPUB styling
├── metadata/          # Metadata for the book (title, author, etc.)
├── Makefile           # Local build commands (pandoc)
├── .github/workflows/ # CI workflows
└── README.md          # This file
```

## Build locally

Requirements: Pandoc and optionally LaTeX (for PDF).

```bash
make all    # builds html, epub, pdf
make html   # builds html
make epub   # builds epub
make pdf    # builds pdf
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

## License

Content license is defined by the author. Default: © 2025 Anonymous.
