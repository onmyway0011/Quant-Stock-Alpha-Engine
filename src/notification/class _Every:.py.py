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