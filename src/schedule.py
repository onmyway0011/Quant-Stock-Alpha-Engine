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
    def __init__(self, job_list: List[_Job]):
        self._jobs = job_list

    def day(self):
        return _TimeUnit(self._jobs, 1)

    @property
    def hour(self):
        return _TimeUnit(self._jobs, 1)

    def minutes(self):
        return _TimeUnit(self._jobs, 1)

_jobs: List[_Job] = []


def every(interval: int = 1) -> _Every:
    # interval is ignored in stub
    return _Every(_jobs)


def run_pending():
    # In stub, we don't schedule by time. We simply do nothing to avoid side-effects during tests.
    # Alternatively, could run all jobs once:
    # for job in list(_jobs):
    #     job.run()
    pass