SHELL := /bin/bash

PREFIX?=/usr/local
_INSTDIR=${DESTDIR}${PREFIX}
BINDIR?=${_INSTDIR}/bin
SHAREDIR?=${_INSTDIR}/share/wirelogd
MANDIR?=${_INSTDIR}/share/man

VERSION=0.1.2-3

.PHONY: all
all: build

.PHONY: install
## install: Install the application
install:
	@echo "Installing..."
	@mkdir -m755 -p ${BINDIR} ${SHAREDIR} ${MANDIR}/man1
	@install -m755 wirelogd/main.py ${BINDIR}/wirelogd
	@install -m644 man/wirelogd.1 ${MANDIR}/man1/wirelogd.1
	@install -m644 contrib/wirelogd.cfg ${SHAREDIR}/
	@install -m644 contrib/wirelogd.service ${SHAREDIR}/
	@install -m644 contrib/wirelogd-nopasswd ${SHAREDIR}/

.PHONY: uninstall
## uninstall: Uninstall the application
uninstall:
	@echo "Uninstalling..."
	@rm -f ${BINDIR}/wirelogd
	@rm -f ${MANDIR}/man1/wirelogd.1
	@rm -f ${SHAREDIR}/*
	@rmdir --ignore-fail-on-non-empty ${BINDIR}
	@rmdir --ignore-fail-on-non-empty ${SHAREDIR}
	@rmdir --ignore-fail-on-non-empty ${MANDIR}/man1
	@rmdir --ignore-fail-on-non-empty ${MANDIR}

.PHONY: dev
## dev: Install development dependencies with pip
dev:
	python3 -m pip install -e .[dev,test]

.PHONY: lint
## lint: Run linters
lint:
	flake8 ./wirelogd/

.PHONY: test
## test: Run tests
test:
	pytest --cov-report=html --cov-report=term-missing --cov=wirelogd

.PHONY: man
## man: Build manpage
man:
	@echo "Generating..."
	@argparse-manpage \
		--pyfile wirelogd/main.py \
		--function setup_parser \
		--author 'Nicolas Karolak' \
		--author-email nicolas.karolak@univ-eiffel.fr \
		--project-name wirelogd \
		--url https://openproject.u-pem.fr/projects/wirelogd \
		--output man/wirelogd.1

.PHONY: build
## build: Build Python package
build:
	python3 setup.py sdist bdist_wheel


.PHONY: deb
## deb: Build Debian package
deb:
	$(MAKE) DESTDIR=tmp/deb PREFIX=/usr install
	mkdir -p \
		dist \
		tmp/deb/etc \
		tmp/deb/etc/systemd/system \
		tmp/deb/etc/sudoers.d
	cp -f tmp/deb/usr/share/wirelogd/wirelogd.cfg tmp/deb/etc/
	cp -f tmp/deb/usr/share/wirelogd/wirelogd.service tmp/deb/etc/systemd/system/
	cp -f tmp/deb/usr/share/wirelogd/wirelogd-nopasswd tmp/deb/etc/sudoers.d/
	cp -r DEBIAN tmp/deb/
	fakeroot dpkg-deb --build tmp/deb dist/wirelogd-${VERSION}.deb

.PHONY: clean
## clean: Remove build artifacts
clean:
	@echo "Cleaning..."
	@rm -rf \
		*.egg-info/ \
		__pycache__/ \
		build/ \
		dist/ \
		htmlcov/ \
		tests/__pycache__/ \
		tmp/ \
		wirelogd/__pycache__/

.PHONY: help
## help: Print this help message
help:
	@echo -e "Usage: \n"
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'
