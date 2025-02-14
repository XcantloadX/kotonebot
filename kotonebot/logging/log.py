import logging
from typing import cast

LEVEL_VERBOSE = 5

def enable_verbose():
    logging.addLevelName(LEVEL_VERBOSE, 'VERBOSE')

class VerboseLogger(logging.Logger):
    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(LEVEL_VERBOSE):
            self._log(LEVEL_VERBOSE, msg, args, **kwargs)

def getLogger(name: str | None = None) -> VerboseLogger:
    logger = logging.getLogger(name)
    if not isinstance(logger, VerboseLogger):
        logger.__class__ = VerboseLogger
    return cast(VerboseLogger, logger)