import pandas as pd
from numba import jit

class ExecutionData:
    def initialize(self):
        self.child_order_acceptance_id = []
        self.size = []
        self.price = []
        self.exec_date = []
