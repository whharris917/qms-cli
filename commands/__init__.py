"""
QMS CLI Commands Package

Individual command implementations using the CommandRegistry pattern.
Each command is defined in its own file and self-registers via decorator.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
# Commands are imported to trigger registration
# The order here doesn't matter - registration happens on import

from . import status
from . import inbox
from . import workspace
from . import create
from . import read
from . import checkout
from . import checkin
from . import route
from . import assign
from . import review
from . import approve
from . import reject
from . import release
from . import revert
from . import close
from . import fix
from . import cancel
from . import history
from . import comments
from . import migrate
from . import verify_migration
