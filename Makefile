
VERSION=0.5

FILES=README download.cgi download.cgi.html download.cgi.5

DIRECTORY=download.cgi-$(VERSION)

all: help

release: tag bundle

tag:        
	git tag $(VERSION)

bundle: download.cgi.html download.cgi.5
	rm -rf $(DIRECTORY)
	mkdir $(DIRECTORY)
	cp $(FILES) $(DIRECTORY)
	tar czf $(DIRECTORY).tar.gz $(DIRECTORY)

download.cgi.html: download.cgi
	pod2html $< > $@

download.cgi.5:    download.cgi
	pod2man  $< > $@

help:
	@echo "Individual steps:"
	@echo "  make tag VERSION=0.6"
	@echo "  make bundle VERSION=0.6"

	@echo ""
	@echo "Does both:"
	@echo "  make release VERSION=0.6"

