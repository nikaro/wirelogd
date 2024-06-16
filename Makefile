APP=wirelogd
PREFIX?=/usr/local
_INSTDIR=${DESTDIR}${PREFIX}
BINDIR?=${_INSTDIR}/bin
SHAREDIR?=${_INSTDIR}/share/${APP}
MANDIR?=${_INSTDIR}/share/man

GOOS?=$(shell go env GOOS)
GOARCH?=$(shell go env GOARCH)
VERSION = $(shell git describe --always --dirty)

.PHONY: all
all: build

.PHONY: setup
## setup: Setup go modules
setup:
	go get -u all
	go mod tidy

.PHONY: build
## build: Build for the current target
build:
	@echo "Building..."
	env CGO_ENABLED=0 GOOS=${GOOS} GOARCH=${GOARCH} go build -ldflags="-s -w -X 'main.version=${VERSION}'" -o build/${APP}-${GOOS}-${GOARCH} .

.PHONY: install
## install: Install the application
install:
	@echo "Installing..."
	install -Dm755 build/${APP}-${GOOS}-${GOARCH} ${BINDIR}/${APP}
	install -Dm644 man/${APP}.1 ${MANDIR}/man1/${APP}.1
	install -Dm644 contrib/config.json ${SHAREDIR}/config.json
	install -Dm644 contrib/${APP}.service ${SHAREDIR}/${APP}.service
	sed -i'' -e 's,/usr,${PREFIX},g' ${SHAREDIR}/${APP}.service

.PHONY: uninstall
## uninstall: Uninstall the application
uninstall:
	@echo "Uninstalling..."
	rm -f ${BINDIR}/${APP}
	rm -f ${MANDIR}/man1/${APP}.1
	rm -f ${SHAREDIR}/*
	rmdir --ignore-fail-on-non-empty ${BINDIR}
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}
	rmdir --ignore-fail-on-non-empty ${MANDIR}/man1
	rmdir --ignore-fail-on-non-empty ${MANDIR}

.PHONY: lint
## lint: Run linters
lint:
	@echo "Linting..."
	go vet ./...
	go fix ./...
	staticcheck ./...
	govulncheck ./...
	golangci-lint run


.PHONY: format
## format: Runs goimports on the project
format:
	@echo "Formatting..."
	go fmt ./...

.PHONY: test
## test: Runs go test
test:
	@echo "Testing..."
	go test ./...

.PHONY: run
## run: Runs go run
run:
	go run -race ${APP}.go

.PHONY: clean
## clean: Cleans the binary
clean:
	@echo "Cleaning..."
	rm -rf build/
	rm -rf dist/

.PHONY: help
## help: Print this help message
help:
	@echo -e "Usage: \n"
	@sed -n 's/^##//p' ${MAKEFILE_LIST} | column -t -s ':' |  sed -e 's/^/ /'
