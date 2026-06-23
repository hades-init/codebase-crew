from functools import cache
from pathlib import Path
import sqlite3

from crew.core.config import settings


@cache
def get_conn():
    return sqlite3.connect(settings.CHECKPOINT_DATABASE, check_same_thread=False)
