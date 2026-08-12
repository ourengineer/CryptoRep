# © 2026 Guillermo Antonio Herrera Argueta. All Rights Reserved.
# Author: Guillermo Antonio Herrera Argueta
# app.py - Crypto Rep Flask API
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, os, stripe
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

app = Flask(__name__)
CORS(app)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
GITHUB_TOKEN = os.getenv("CR_GITHUB_TOKEN")

# DB setup
engine = create_engine('sqlite:///cryptorep.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    github_username = Column(String, unique=True)
    email = Column(String)
    stripe_account_id = Column(String)
    tier = Column(String, default='free') # free or pro
    created_at = Column(DateTime, default=datetime.utcnow)

class Royalty(Base):
    __tablename__ = 'royalties'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    repo_name = Column(String)
    amount = Column(Float)
    month = Column(String) # YYYY-MM
    paid = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

def calculate_royalty_for_repo(owner, repo):
    """Same logic as before, simplified"""
    h = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=h).json()
    stars, forks = r.get("stargazers_count", 0), r.get("forks_count", 0)
    # Basic formula: change to your model
    return round(stars * 0.01 + forks * 0.05, 2)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    session = Session()
    if session.query(User).filter_by(github_username=data['github_username']).first():
        return jsonify({"error": "User exists"}), 400
    user = User(
        github_username=data['github_username'],
        email=data['email'],
        tier='free'
    )
    session.add(user)
    session.commit()
    return jsonify({"id": user.id, "tier": user.tier})

@app.route('/api/scan/<username>', methods=['POST'])
def scan_user(username):
    session = Session()
    user = session.query(User).filter_by(github_username=username).first()
    if not user: return jsonify({"error": "User not found"}), 404

    repos = requests.get(
        f"https://api.github.com/users/{username}/repos?per_page=100",
        headers={"Authorization": f"token {GITHUB_TOKEN}"}
    ).json()

    total = 0
    month = datetime.utcnow().strftime("%Y-%m")
    for repo in repos:
        amt = calculate_royalty_for_repo(username, repo['name'])
        if amt > 0:
            fee = 0.15 if user.tier == 'free' else 0.10
            net = round(amt * (1 - fee), 2)
            session.add(Royalty(
                user_id=user.id, repo_name=repo['name'],
                amount=net, month=month
            ))
            total += net
    session.commit()
    return jsonify({"scanned_repos": len(repos), "earned_this_month": total})

@app.route('/api/dashboard/<username>', methods=['GET'])
def dashboard(username):
    session = Session()
    user = session.query(User).filter_by(github_username=username).first()
    if not user: return jsonify({"error": "User not found"}), 404
    royalties = session.query(Royalty).filter_by(user_id=user.id).all()
    unpaid = sum([r.amount for r in royalties if not r.paid])
    return jsonify({
        "username": user.github_username,
        "tier": user.tier,
        "total_earned": sum([r.amount for r in royalties]),
        "unpaid_balance": round(unpaid, 2),
        "royalties": [{"repo": r.repo_name, "amount": r.amount, "month": r.month, "paid": r.paid} for r in royalties]
    })

@app.route('/api/upgrade', methods=['POST'])
def upgrade():
    # Stripe Checkout for Pro tier
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Crypto Rep Pro'},
                'unit_amount': 1200,
                'recurring': {'interval': 'month'},
            },
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://cryptorep.org/success',
        cancel_url='https://cryptorep.org/cancel',
    )
    return jsonify({"checkout_url": session.url})

if __name__ == '__main__':
    app.run(debug=True, port=5000)