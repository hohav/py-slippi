import logging, os

from termcolor import colored


COLORS = {
    'WARNING': 'yellow',
    'INFO': 'white',
    'DEBUG': 'grey',
    'CRITICAL': 'red',
    'ERROR': 'red'}


_old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = _old_factory(*args, **kwargs)
    l = record.levelname
    record.levelname_colored = colored(l, COLORS.get(l, 'white'))
    return record


logging.setLogRecordFactory(record_factory)
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'WARNING').upper(),
    format="%(levelname_colored)s: %(message)s")
log = logging.getLogger(__name__)
