.PHONY: install uninstall test
PYTHON ?= python3
DESTDIR ?=

install:
	PYTHONPATH=src $(PYTHON) -m usbgate.install install --root "$(if $(DESTDIR),$(DESTDIR),/)"

uninstall:
	PYTHONPATH=src $(PYTHON) -m usbgate.install uninstall --root "$(if $(DESTDIR),$(DESTDIR),/)"

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
