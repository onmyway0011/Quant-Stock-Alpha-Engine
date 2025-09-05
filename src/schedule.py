# Minimal stub for 'schedule' library used in tests.
# Provides only the APIs referenced in src.core.engine:
# - every(), .day.at().do(func), .hour.do(func), (n).minutes.do(func)
# - run_pending()

from typing import Callable, List
from dataclasses import dataclass

@dataclass
class _Job:
    func: Callable

    def run(self):
        try:
            self.func()
        except Exception:
            pass

class _TimeUnit:
    def __init__(self, job_list: List[_Job], interval: int = 1):
        self._jobs = job_list
        self._interval = interval

    def at(self, _time_str: str):  # for .day.at("HH:MM")
        return self

    def do(self, func: Callable):
        self._jobs.append(_Job(func))
        return self

class _Every:
    def __init__(self, job_list: List[_Job], interval: int = 1):
        self._jobs = job_list
        self._interval = interval

    @property
    def day(self):
        return _TimeUnit(self._jobs, self._interval)

    @property
    def hour(self):
        return _TimeUnit(self._jobs, self._interval)

    @property
    def minutes(self):
        return _TimeUnit(self._jobs, self._interval)

_jobs: List[_Job] = []

def every(interval: int = 1) -> _Every:
    return _Every(_jobs, interval)

def run_pending():
    pass