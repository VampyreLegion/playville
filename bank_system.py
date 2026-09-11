import time
import random


class BankTransaction:
    def __init__(self, npc_name, amount, t_type, description):
        self.npc_name = npc_name
        self.amount = amount       # positive=deposit, negative=withdrawal
        self.t_type = t_type       # 'deposit','withdrawal','salary','robbery'
        self.description = description
        self.timestamp = time.time()


class BankSystem:
    def __init__(self):
        self.accounts = {}         # npc_name -> balance
        self.transactions = []     # BankTransaction list
        self.total_reserves = 5000 # town bank vault
        self.last_robbery_check = 0

    def get_balance(self, npc_name):
        return self.accounts.get(npc_name, 0)

    def deposit(self, npc_name, amount, desc="deposit"):
        if amount <= 0:
            return False
        self.accounts[npc_name] = self.accounts.get(npc_name, 0) + amount
        self.total_reserves += amount
        tx = BankTransaction(npc_name, amount, 'deposit', desc)
        self.transactions.append(tx)
        return True

    def withdraw(self, npc_name, amount, desc="withdrawal"):
        if amount <= 0:
            return False
        balance = self.accounts.get(npc_name, 0)
        if balance < amount:
            return False
        self.accounts[npc_name] = balance - amount
        self.total_reserves -= amount
        tx = BankTransaction(npc_name, -amount, 'withdrawal', desc)
        self.transactions.append(tx)
        return True

    def pay_salary(self, npc_name, amount):
        self.accounts[npc_name] = self.accounts.get(npc_name, 0) + amount
        self.total_reserves += amount
        tx = BankTransaction(npc_name, amount, 'salary', f"Weekly salary payment")
        self.transactions.append(tx)

    def attempt_robbery(self, npc_name):
        """1% chance per call; returns stolen amount or 0."""
        if random.random() > 0.01:
            return 0
        max_steal = min(500, self.total_reserves)
        if max_steal <= 0:
            return 0
        stolen = random.randint(50, max_steal)
        self.total_reserves -= stolen
        tx = BankTransaction(npc_name, stolen, 'robbery', f"Bank robbery by {npc_name}")
        self.transactions.append(tx)
        return stolen

    def get_account_summary(self, npc_name):
        balance = self.accounts.get(npc_name, 0)
        tx_count = sum(1 for t in self.transactions if t.npc_name == npc_name)
        return {'balance': balance, 'tx_count': tx_count}
