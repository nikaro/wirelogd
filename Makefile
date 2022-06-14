APP=wirelogd
PREFIX?=/usr/local
_INSTDIR=${DESTDIR}${PREFIX}
BINDIR?=${_INSTDIR}/bin
SHAREDIR?=${_INSTDIR}/share/${APP}
MANDIR?=${_INSTDIR}/share/man

GOOS?=$(shell go env GOOS)
GOARCH?=$(shell go env GOARCH)

.PHONY: all
all: build

.PHONY: setup
## setup: Setup go modules
setup:
	go get -u all
	go mod tidy
	go mod vendor

.PHONY: build
## build: Build for the current target
build:
	@echo "Building..."
	env CGO_ENABLED=0 GOOS=${GOOS} GOARCH=${GOARCH} go build -mod vendor -o build/${APP}-${GOOS}-${GOARCH} .
	build/${APP}-${GOOS}-${GOARCH} man > man/wirelogd.1
	build/${APP}-${GOOS}-${GOARCH} completion bash > completions/${APP}.bash
	build/${APP}-${GOOS}-${GOARCH} completion fish > completions/${APP}.fish
	build/${APP}-${GOOS}-${GOARCH} completion zsh > completions/${APP}.zsh

.PHONY: build-all
## build-all: Build for all targets
build-all:
	env CGO_ENABLED=0 GOOS=linux GOARCH=amd64 $(MAKE) build
	env CGO_ENABLED=0 GOOS=linux GOARCH=arm64 $(MAKE) build

.PHONY: install
## install: Install the application
install:
	@echo "Installing..."
	install -Dm755 build/${APP}-${GOOS}-${GOARCH} ${BINDIR}/${APP}
	install -Dm644 man/${APP}.1 ${MANDIR}/man1/
	install -Dm644 completions/${APP}.bash ${SHAREDIR}/../bash-completion/completions/${APP}
	install -Dm644 completions/${APP}.fish ${SHAREDIR}/../fish/vendor_completions.d/${APP}.fish
	install -Dm644 completions/${APP}.zsh ${SHAREDIR}/../zsh/site-functions/_${APP}
	install -Dm644 contrib/config.toml ${SHAREDIR}/
	install -Dm644 contrib/${APP}.service ${SHAREDIR}/

.PHONY: uninstall
## uninstall: Uninstall the application
uninstall:
	@echo "Uninstalling..."
	rm -f ${BINDIR}/${APP}
	rm -f ${MANDIR}/man1/${APP}.1
	rm -f ${SHAREDIR}/*
	rm -f ${SHAREDIR}/../bash-completion/completions/${APP}
	rm -f ${SHAREDIR}/../fish/vendor_completions.d/${APP}.fish
	rm -f ${SHAREDIR}/../zsh/site-functions/_${APP}
	rmdir --ignore-fail-on-non-empty ${BINDIR}
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}
	rmdir --ignore-fail-on-non-empty ${MANDIR}/man1
	rmdir --ignore-fail-on-non-empty ${MANDIR}
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}/../bash-completion/completions
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}/../bash-completion
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}/../fish/vendor_completions.d
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}/../fish
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}/../zsh/site-functions
	rmdir --ignore-fail-on-non-empty ${SHAREDIR}/../zsh

.PHONY: lint
## lint: Run linters
lint:
	@echo "Linting..."
	golangci-lint run

.PHONY: format
## format: Runs goimports on the project
format:
	@echo "Formatting..."
	fd -t file -e go -E vendor/ | xargs goimports -l -w

.PHONY: test
## test: Runs go test
test:
	@echo "Testing..."
	go test ./...

.PHONY: man
## man: Build manpage
man:
	@echo "TODO"

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
