from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'booking.db'
CHAIN_PATH = DATA_DIR / 'blockchain.json'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'


# ----------------------------
# Blockchain Layer
# ----------------------------
@dataclass
class Block:
    index: int
    timestamp: str
    transaction_type: str
    data: Dict[str, Any]
    previous_hash: str
    nonce: int = 0
    hash: str = ''

    def compute_hash(self) -> str:
        payload = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transaction_type': self.transaction_type,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def mine(self, difficulty: int = 3) -> None:
        prefix = '0' * difficulty
        while True:
            computed = self.compute_hash()
            if computed.startswith(prefix):
                self.hash = computed
                return
            self.nonce += 1


class Blockchain:
    def __init__(self, chain_file: Path, difficulty: int = 3) -> None:
        self.chain_file = chain_file
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self._load_or_create()

    def _load_or_create(self) -> None:
        self.chain_file.parent.mkdir(parents=True, exist_ok=True)
        if self.chain_file.exists():
            raw = json.loads(self.chain_file.read_text(encoding='utf-8'))
            self.chain = [Block(**item) for item in raw]
        else:
            genesis = Block(
                index=0,
                timestamp=datetime.utcnow().isoformat(),
                transaction_type='GENESIS',
                data={'message': 'Genesis block for booking ledger'},
                previous_hash='0',
            )
            genesis.mine(self.difficulty)
            self.chain = [genesis]
            self._save()

    def _save(self) -> None:
        self.chain_file.write_text(
            json.dumps([asdict(block) for block in self.chain], indent=2),
            encoding='utf-8',
        )

    def add_block(self, transaction_type: str, data: Dict[str, Any]) -> Block:
        previous = self.chain[-1]
        block = Block(
            index=len(self.chain),
            timestamp=datetime.utcnow().isoformat(),
            transaction_type=transaction_type,
            data=data,
            previous_hash=previous.hash,
        )
        block.mine(self.difficulty)
        self.chain.append(block)
        self._save()
        return block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
            if not current.hash.startswith('0' * self.difficulty):
                return False
        return True


blockchain = Blockchain(CHAIN_PATH)


# ----------------------------
# Database Layer
# ----------------------------
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_type TEXT NOT NULL,
            vehicle_no TEXT NOT NULL,
            route_name TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            fare REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            passenger_name TEXT NOT NULL,
            passenger_email TEXT NOT NULL,
            passenger_phone TEXT NOT NULL,
            seat_no TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'CONFIRMED',
            booking_time TEXT NOT NULL,
            block_hash TEXT NOT NULL,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        );
        """
    )

    cur.execute('SELECT COUNT(*) AS count FROM schedules')
    count = cur.fetchone()['count']
    if count == 0:
        seed_rows = [
            ('BUS', 'BUS-TN-01', 'Chennai Express Bus', 'Chennai', 'Bengaluru', '2026-03-29 07:30', '2026-03-29 13:45', 650),
            ('BUS', 'BUS-TN-02', 'Night Rider Coach', 'Coimbatore', 'Madurai', '2026-03-29 21:00', '2026-03-30 01:45', 420),
            ('RAIL', 'TRAIN-12621', 'Shatabdi Corridor', 'Chennai', 'Mysuru', '2026-03-30 06:00', '2026-03-30 12:15', 980),
            ('RAIL', 'TRAIN-22671', 'Superfast Intercity', 'Salem', 'Trichy', '2026-03-30 09:15', '2026-03-30 12:05', 540),
        ]
        cur.executemany(
            '''
            INSERT INTO schedules (service_type, vehicle_no, route_name, source, destination, departure_time, arrival_time, fare)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            seed_rows,
        )
    conn.commit()
    conn.close()


init_db()


def get_seat_layout(service_type: str) -> List[Dict[str, Any]]:
    seats: List[Dict[str, Any]] = []
    if service_type.upper() == 'BUS':
        rows = list(range(1, 11))
        cols = ['A', 'B', 'C', 'D']
        for row in rows:
            for col in cols:
                seats.append({
                    'seat_no': f'{row}{col}',
                    'row': row,
                    'col': col,
                    'type': 'window' if col in {'A', 'D'} else 'aisle',
                })
    else:
        rows = list(range(1, 13))
        cols = ['A', 'B', 'C', 'D', 'E', 'F']
        for row in rows:
            for col in cols:
                seats.append({
                    'seat_no': f'{row}{col}',
                    'row': row,
                    'col': col,
                    'type': 'window' if col in {'A', 'F'} else ('middle' if col in {'C', 'D'} else 'aisle'),
                })
    return seats


@app.route('/')
def index():
    conn = get_db()
    schedules = conn.execute('SELECT * FROM schedules ORDER BY departure_time').fetchall()
    conn.close()
    return render_template('index.html', schedules=schedules, chain_valid=blockchain.is_valid())


@app.route('/schedule/<int:schedule_id>')
def schedule_detail(schedule_id: int):
    conn = get_db()
    schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
    if not schedule:
        conn.close()
        return redirect(url_for('index'))

    booked_rows = conn.execute(
        'SELECT seat_no FROM bookings WHERE schedule_id = ? AND status = ? ORDER BY seat_no',
        (schedule_id, 'CONFIRMED'),
    ).fetchall()
    conn.close()

    booked_seats = {row['seat_no'] for row in booked_rows}
    return render_template(
        'booking.html',
        schedule=schedule,
        seat_layout=get_seat_layout(schedule['service_type']),
        booked_seats=booked_seats,
        chain_valid=blockchain.is_valid(),
    )


@app.post('/book/<int:schedule_id>')
def book_ticket(schedule_id: int):
    passenger_name = request.form.get('passenger_name', '').strip()
    passenger_email = request.form.get('passenger_email', '').strip()
    passenger_phone = request.form.get('passenger_phone', '').strip()
    seat_no = request.form.get('seat_no', '').strip().upper()

    if not all([passenger_name, passenger_email, passenger_phone, seat_no]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    conn = get_db()
    schedule = conn.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
    if not schedule:
        conn.close()
        return jsonify({'success': False, 'message': 'Schedule not found.'}), 404

    existing = conn.execute(
        'SELECT id FROM bookings WHERE schedule_id = ? AND seat_no = ? AND status = ?',
        (schedule_id, seat_no, 'CONFIRMED'),
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': f'Seat {seat_no} is already booked.'}), 409

    transaction = {
        'schedule_id': schedule_id,
        'service_type': schedule['service_type'],
        'vehicle_no': schedule['vehicle_no'],
        'route_name': schedule['route_name'],
        'source': schedule['source'],
        'destination': schedule['destination'],
        'departure_time': schedule['departure_time'],
        'passenger_name': passenger_name,
        'passenger_email': passenger_email,
        'passenger_phone': passenger_phone,
        'seat_no': seat_no,
        'amount': float(schedule['fare']),
        'status': 'CONFIRMED',
    }
    block = blockchain.add_block('BOOK_TICKET', transaction)

    booking_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO bookings (schedule_id, passenger_name, passenger_email, passenger_phone, seat_no, amount, status, booking_time, block_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            schedule_id,
            passenger_name,
            passenger_email,
            passenger_phone,
            seat_no,
            float(schedule['fare']),
            'CONFIRMED',
            booking_time,
            block.hash,
        ),
    )
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify(
        {
            'success': True,
            'message': f'Booking confirmed for seat {seat_no}.',
            'booking_id': booking_id,
            'block_hash': block.hash,
            'redirect_url': url_for('ticket', booking_id=booking_id),
        }
    )


@app.route('/ticket/<int:booking_id>')
def ticket(booking_id: int):
    conn = get_db()
    booking = conn.execute(
        '''
        SELECT b.*, s.service_type, s.vehicle_no, s.route_name, s.source, s.destination,
               s.departure_time, s.arrival_time
        FROM bookings b
        JOIN schedules s ON s.id = b.schedule_id
        WHERE b.id = ?
        ''',
        (booking_id,),
    ).fetchone()
    conn.close()
    if not booking:
        return redirect(url_for('index'))
    return render_template('ticket.html', booking=booking, chain_valid=blockchain.is_valid())


@app.route('/ledger')
def ledger():
    conn = get_db()
    bookings = conn.execute(
        '''
        SELECT b.*, s.service_type, s.route_name, s.source, s.destination, s.vehicle_no
        FROM bookings b JOIN schedules s ON s.id = b.schedule_id
        ORDER BY b.id DESC
        '''
    ).fetchall()
    conn.close()
    return render_template('ledger.html', blocks=blockchain.chain, bookings=bookings, chain_valid=blockchain.is_valid())


@app.route('/api/seats/<int:schedule_id>')
def api_seats(schedule_id: int):
    conn = get_db()
    schedule = conn.execute('SELECT service_type FROM schedules WHERE id = ?', (schedule_id,)).fetchone()
    booked_rows = conn.execute(
        'SELECT seat_no FROM bookings WHERE schedule_id = ? AND status = ?', (schedule_id, 'CONFIRMED')
    ).fetchall()
    conn.close()
    if not schedule:
        return jsonify({'success': False, 'message': 'Schedule not found'}), 404
    return jsonify(
        {
            'success': True,
            'service_type': schedule['service_type'],
            'booked_seats': [row['seat_no'] for row in booked_rows],
            'seat_layout': get_seat_layout(schedule['service_type']),
            'chain_valid': blockchain.is_valid(),
        }
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
