CLOCPY		= bin/countlines.py
CLOCDEF		= .cloc.defs

DOC_DIR		= sphinx
TEST_DIR	= tests

SUBDIRS		= tests sphinx
CLEANDIRS 	= $(SUBDIRS:%=clean-%)


.PHONY: check doc cloc clean $(CLEANDIRS)


# Run a minimal set of tests (should always succeed)
check:
	$(MAKE) -C $(TEST_DIR)
	
# Build the sphinx documentation
doc:
	$(MAKE) -C $(DOC_DIR)

# Count the number of source code lines
cloc:
	$(CLOCPY) -d $(CLOCDEF) site src tests conf,templates examples sphinx

# Clean all the directories
clean: $(CLEANDIRS)
$(CLEANDIRS):
	$(MAKE) -C $(@:clean-%=%) clean

