# a-book
Repo template for  book writters 
.
├─ book/                    #
│  ├─ 00-front-matter.md
│  ├─ 01-chapter-1.md
│  ├─ 02-chapter-2.md
│  ├─ images/
│  ├─ styles/
│  │   ├─ book.css          # common style (for HTML/EPUB/PDF via  CSS)
│  │   └─ fonts.css         # @font-face 
│  └─ fonts/
│      ├─ Inter-Regular.woff2
│      └─ ...
├─ build/                   # ( CI;  .gitignore)
├─ metadata/
│  ├─ metadata.yaml         # (title, author, lang, cover, isbn, etc.)
│  └─ epub-metadata.xml     # extended epub metadata
├─ .github/
│  ├─ workflows/
│  │   ├─ preview.yml       # 
│  │   └─ release.yml       # 
│  ├─ pull_request_template.md
│  └─ ISSUE_TEMPLATE.md
├─ .editorconfig
├─ .markdownlint.json
├─ .vale.ini                # author style, tone, AI actor/system 
├─ .gitignore
├─ Makefile                 # CI
└─ README.md

