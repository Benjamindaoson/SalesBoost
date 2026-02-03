class GovernanceDashboard:
    def __init__(self):
        self.kpis = {}

    def update(self, kpi: str, value):
        self.kpis[kpi] = value

    def report(self):
        return dict(self.kpis)
