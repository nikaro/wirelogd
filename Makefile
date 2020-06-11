all: build

install:
	pip install -qq .

install-dev:
	pip install -e .[dev]

lint:
	autopep8 --diff ./wirelogd/
	flake8 ./wirelogd/
	pylint --rcfile=setup.cfg ./wirelogd/
	bandit -r ./wirelogd/

build:
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf *.egg-info/ build/ dist/
