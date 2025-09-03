# Book Makefile (Markdown -> HTML/EPUB/PDF) via Pandoc
# Local usage assumes pandoc and a LaTeX engine are installed.
# CI uses docker images for reproducible builds.

BOOK_DIR := book
META := metadata/metadata.yaml
BUILD := build
SOURCES := $(wildcard $(BOOK_DIR)/*.md)
CSS := $(BOOK_DIR)/styles/book.css

HTML := $(BUILD)/book.html
EPUB := $(BUILD)/book.epub
PDF  := $(BUILD)/book.pdf

.PHONY: all html epub pdf clean
all: html epub pdf

$(BUILD):
	mkdir -p $(BUILD)

html: $(HTML)
$(HTML): $(SOURCES) $(CSS) $(META) | $(BUILD)
	pandoc $(SOURCES) \
	  --from gfm --to html5 \
	  --standalone \
	  --metadata-file=$(META) \
	  --css=$(CSS) \
	  -o $(HTML)

epub: $(EPUB)
$(EPUB): $(SOURCES) $(CSS) $(META) | $(BUILD)
	pandoc $(SOURCES) \
	  --from gfm --to epub3 \
	  --metadata-file=$(META) \
	  --css=$(CSS) \
	  --epub-cover-image=book/images/cover.png \
	  -o $(EPUB)

pdf: $(PDF)
$(PDF): $(SOURCES) $(CSS) $(META) | $(BUILD)
	# By default use xelatex for portability; CSS is not applied in LaTeX route.
	pandoc $(SOURCES) \
	  --from gfm --to pdf \
	  --pdf-engine=xelatex \
	  --metadata-file=$(META) \
	  -o $(PDF)

clean:
	rm -rf $(BUILD)
