import random
import datetime
from faker import Faker

fake = Faker()

narration_templates = [
    "ATM Withdrawal - {}",
    "Purchase at {}",
    "Online Purchase - {}",
    "Bill Payment - {}",
    "{} Order - {}",
    "Fund Transfer to {}",
    "UPI Transfer to {}",
    "EMI Payment - {}",
    "Salary Credit",
    "Refund from {}",
    "Cash Deposit at {}",
    "{} Subscription Payment",
]


def generate_fake_transaction(current_balance, index):
    txn_types = ["DEBIT", "CREDIT"]
    modes = ["OTHERS", "ATM", "UPI", "ONLINE", "BANK_TRANSFER", "POS"]
    amount = random.uniform(10, 5000) if index % 3 else random.uniform(500, 10000)
    txn_type = random.choice(txn_types)
    transaction_date = datetime.datetime.now() - datetime.timedelta(
        days=index * random.randint(1, 3)
    )

    template = random.choice(narration_templates)
    placeholders = template.count("{}")
    if placeholders == 1:
        narration = template.format(fake.company())
    elif placeholders == 2:
        narration = template.format(fake.company(), fake.company_suffix())
    else:
        narration = template

    if txn_type == "DEBIT":
        current_balance -= amount
    else:
        current_balance += amount

    return {
        "_txnId": f"M{random.randint(100000, 999999)}",
        "_type": txn_type,
        "_mode": random.choice(modes),
        "_amount": f"{amount:.2f}",
        "_currentBalance": f"{current_balance:.2f}",
        "_transactionTimestamp": transaction_date.isoformat(),
        "_valueDate": transaction_date.date().isoformat(),
        "_narration": narration,
        "_reference": fake.bothify(text="REF#######"),
    }


def generate_fake_account_data(transaction_count=50):
    current_balance = random.uniform(10000, 100000)
    pending_balance = 0
    transactions = []

    for i in range(transaction_count):
        transaction = generate_fake_transaction(current_balance, i)
        transactions.append(transaction)
        current_balance = float(transaction["_currentBalance"])

        if transaction["_mode"] == "PENDING":
            pending_balance += float(transaction["_amount"])

    return {
        "Account": {
            "Profile": {
                "Holders": {
                    "Holder": {
                        "_name": fake.name(),
                        "_dob": fake.date_of_birth(
                            minimum_age=18, maximum_age=65
                        ).isoformat(),
                        "_mobile": fake.phone_number(),
                        "_nominee": random.choice(["REGISTERED", "NOT-REGISTERED"]),
                        "_email": fake.email(),
                        "_pan": fake.bothify(text="?????#####?"),
                        "_ckycCompliance": random.choice(["true", "false"]),
                    },
                    "_type": random.choice(["JOINT", "SINGLE"]),
                }
            },
            "Summary": {
                "Pending": {"_amount": f"{pending_balance:.2f}"},
                "_currentBalance": f"{current_balance:.2f}",
                "_currency": "INR",
                "_exchgeRate": f"{random.uniform(3, 7):.2f}",
                "_balanceDateTime": fake.iso8601(),
                "_type": random.choice(["CURRENT", "SAVINGS"]),
                "_branch": fake.city(),
                "_facility": random.choice(["CC", "OD"]),
                "_ifscCode": fake.bothify(text="????0??????"),
                "_micrCode": fake.bothify(text="#########"),
                "_openingDate": fake.date_between(
                    start_date="-10y", end_date="today"
                ).isoformat(),
                "_currentODLimit": str(random.randint(10000, 50000)),
                "_drawingLimit": str(random.randint(5000, 25000)),
                "_status": random.choice(["ACTIVE", "INACTIVE", "CLOSED"]),
            },
            "Transactions": {
                "Transaction": transactions,
                "_startDate": fake.date_between(
                    start_date="-2y", end_date="-1y"
                ).isoformat(),
                "_endDate": fake.date_between(
                    start_date="-1y", end_date="today"
                ).isoformat(),
            },
            "_xmlns": "http://api.rebit.org.in/FISchema/deposit",
            "_xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "_xsi:schemaLocation": "http://api.rebit.org.in/FISchema/deposit ../FISchema/deposit.xsd",
            "_linkedAccRef": fake.bothify(text="REF##########"),
            "_maskedAccNumber": fake.bothify(text="##########"),
            "_version": "1.0",
            "_type": "deposit",
        }
    }


if __name__ == "__main__":
    print(generate_fake_account_data(transaction_count=10))
