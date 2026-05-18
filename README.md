# ChainTransit - Bus and Rail Ticket Booking System with Blockchain

ChainTransit is a professional academic project built with Flask, SQLite, HTML, CSS, and JavaScript. It supports bus and rail ticket booking with an attractive seat layout and a lightweight blockchain ledger that stores each confirmed booking as an immutable transaction.

## Features

- Bus and rail booking dashboard
- Professional glassmorphism UI with premium background
- Interactive seat layout for bus and rail modes
- SQLite database for schedules and bookings
- Blockchain ledger using SHA-256 hashing and proof-of-work mining
- Ticket generation with blockchain hash
- Ledger page to verify booking integrity

## Project Structure

```text
bus_rail_blockchain_booking_system/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── blockchain.json
│   └── booking.db
├── static/
│   ├── css/styles.css
│   └── js/app.js
└── templates/
    ├── base.html
    ├── index.html
    ├── booking.html
    ├── ticket.html
    └── ledger.html
```

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Default Demo Data

The app seeds four demo schedules:

- Chennai → Bengaluru (Bus)
- Coimbatore → Madurai (Bus)
- Chennai → Mysuru (Rail)
- Salem → Trichy (Rail)

## How Blockchain Is Used

When a booking is confirmed:

1. Passenger and seat details are collected.
2. A transaction payload is created.
3. A new block is mined with a SHA-256 hash.
4. The block stores the previous hash, creating the chain.
5. The booking row stores the generated block hash.

