.PHONY: all
all: clean build

.PHONY: install
install:
	python3 -m pip install -qq .

.PHONY: install-test
install-test:
	python3 -m pip install -e .[test]

.PHONY: install-dev
install-dev: install-test
	python3 -m pip install -e .[dev]

.PHONY: lint
lint:
	autopep8 --diff --recursive ./wirelogd/
	flake8 ./wirelogd/
	pylint --rcfile=setup.cfg ./wirelogd/
	bandit -r ./wirelogd/

.PHONY: test
test:
	pytest --cov-report=html --cov-report=term-missing --cov=wirelogd

.PHONY: build
build:
	python3 setup.py sdist bdist_wheel

.PHONY: clean
clean:
	rm -rf *.egg-info/ build/ dist/
