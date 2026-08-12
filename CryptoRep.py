# © 2026 Guillermo Antonio Herrera Argueta. All Rights Reserved.
# Author: Guillermo Antonio Herrera Argueta
# Crypto Rep - Royalty engine for GitHub developers
# License: Proprietary. All rights globally reserved to Crypto Rep NFP.

import os
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("CR_GITHUB_TOKEN") # Personal access token with repo scope

class CryptoRep:
    def __init__(self, org_name="CryptoRep"):
        self.org_name = org_name
        self.rate_per_star = 0.01 # $0.01 per star per month
        self.rate_per_fork = 0.05 # $0.05 per fork per month
        self.rate_per_loc = 0.0001 # $0.0001 per line of code written per month
        self.min_payout = 5.00 # Minimum $5 to trigger payout

    def get_user_repos(self, username):
        """Fetch all public repos for a user"""
        url = f"{GITHUB_API}/users/{username}/repos?per_page=100&type=owner"
        r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        r.raise_for_status()
        return r.json()

    def get_repo_stats(self, owner, repo):
        """Get stars, forks, contributors, LOC"""
        repo_data = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}",
            headers={"Authorization": f"token {GITHUB_TOKEN}"}
        ).json()

        # LOC requires code frequency stats
        stats = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/stats/code_frequency",
            headers={"Authorization": f"token {GITHUB_TOKEN}"}
        ).json()

        additions = sum([week[1] for week in stats]) if stats else 0

        return {
            "name": repo,
            "stars": repo_data["stargazers_count"],
            "forks": repo_data["forks_count"],
            "additions_loc": additions,
            "owner": owner
        }

    def calculate_royalty(self, stats):
        """Core royalty formula: usage + contribution"""
        usage_pay = stats["stars"] * self.rate_per_star + stats["forks"] * self.rate_per_fork
        contribution_pay = stats["additions_loc"] * self.rate_per_loc
        return round(usage_pay + contribution_pay, 2)

    def assign_credits(self, username):
        """Main: scan user repos and assign monthly credits"""
        repos = self.get_user_repos(username)
        ledger = defaultdict(float)

        for repo in repos:
            try:
                stats = self.get_repo_stats(username, repo["name"])
                royalty = self.calculate_royalty(stats)
                ledger[username] += royalty
                print(f"{repo['name']}: {stats['stars']} stars, {stats['forks']} forks, {stats['additions_loc']} LOC -> ${royalty}")
            except Exception as e:
                print(f"Skip {repo['name']}: {e}")

        return dict(ledger)

    def payout(self, ledger):
        """Mock payout. Replace with Stripe/PayPal/Web3"""
        for user, amount in ledger.items():
            if amount >= self.min_payout:
                print(f"PAY ${amount} to {user} via wallet/stripe")
                # stripe.Charge.create(amount=int(amount*100), currency="usd", source=...)
            else:
                print(f"HOLD ${amount} for {user}: below minimum ${self.min_payout}")

if __name__ == "__main__":
    cr = CryptoRep()
    users = ["torvalds", "gvanrossum", "bookshelves"]
    # Replace with registered users
    total_ledger = {}
    for u in users:
        user_ledger = cr.assign_credits(u)
        total_ledger.update(user_ledger)
    cr.payout(total_ledger)