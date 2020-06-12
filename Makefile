.PHONY: all
all: clean build

.PHONY: install
install:
	python3 -m pip install -qq .

.PHONY: install-dev
install-dev:
	python3 -m pip install -e .[dev]

.PHONY: lint
lint:
	autopep8 --diff ./wirelogd/
	flake8 ./wirelogd/
	pylint --rcfile=setup.cfg ./wirelogd/
	bandit -r ./wirelogd/

.PHONY: build
build:
	python3 setup.py sdist bdist_wheel

.PHONY: clean
clean:
	rm -rf *.egg-info/ build/ dist/
