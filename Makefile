CLOCPY		= bin/countlines.py
CLOCDEF		= project/cloc.defs
ifeq ($(shell uname),Darwin)
	CLOCBIN     = cloc
else
	CLOCBIN     = cloc.pl
endif

DOC_DIR		= sphinx
TEST_DIR	   = tests

SUBDIRS		= tests sphinx
CLEANDIRS 	= $(SUBDIRS:%=clean-%)


.PHONY: check tests cover doc cloc clean $(CLEANDIRS)


# Run a minimal set of tests (should always succeed)
check:
	$(MAKE) -C $(TEST_DIR)

# Run all the test suite using nose
tests:
	$(MAKE) -C $(TEST_DIR) tests

# Run the unittest's code coverage analysis
cover:
	$(MAKE) -C $(TEST_DIR) cover

# Build the sphinx documentation
doc:
	$(MAKE) -C $(DOC_DIR)

# Count the number of source code lines
cloc    : ; $(CLOCPY) -p $(CLOCBIN) -d $(CLOCDEF) site src tests conf templates examples sphinx
cloc_all: ; $(CLOCPY) -p $(CLOCBIN) -d $(CLOCDEF) .

# Code quality analysis : pyflakes + pep8 + McCabe (cyclomatic complexity)
flake8: ; flake8 --config=project/flake8.ini --statistics . > project/flake8_report.txt || true

# Code quality analysis : pylint
pylint: ; pylint --rcfile=project/pylint.rc src/* site/* > project/pylint_global.txt || true

# Clean all the directories, then locally
clean: $(CLEANDIRS)
	rm -f project/{flake8_report,pylint_global}.txt

$(CLEANDIRS):
	$(MAKE) -C $(@:clean-%=%) clean

# Usual target
clobber: clean
