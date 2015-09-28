CLOCBIN     = cloc.pl
CLOCPY		= bin/countlines.py
CLOCDEF		= .cloc.defs

DOC_DIR		= sphinx
TEST_DIR	= tests

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
cloc:
	$(CLOCPY) -p $(CLOCBIN) -d $(CLOCDEF) site src tests conf,templates examples sphinx

# Clean all the directories
clean: $(CLEANDIRS)
$(CLEANDIRS):
	$(MAKE) -C $(@:clean-%=%) clean

