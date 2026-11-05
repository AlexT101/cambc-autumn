# Play this bot against itself and open the replay in the arena's viewer.
#   make               first map in maps/
#   make MAP=lanes     a map by name
#   make VIEWER=cambc  cambc's own visualiser instead
# `.` is whichever bot this file sits in, so a copybot copy plays itself.
# The arena script is found by walking up from here, wherever the copy lives.
ARENA := $(shell d="$$PWD"; while [ "$$d" != / ] && [ ! -x "$$d/arena" ]; do d=$$(dirname "$$d"); done; echo "$$d/arena")

.PHONY: run
run:
ifeq ($(VIEWER),cambc)
	cambc run . . --view $(if $(MAP),--map $(MAP))
else
	cambc run . . $(if $(MAP),--map $(MAP))
	$(ARENA) view
endif
