from flask import Blueprint, render_template, jsonify, request
from db import get_db, serialize_row

bp = Blueprint('fuel', __name__)

FUEL_TYPES = ['Oxygen Isotopes', 'Hydrogen Isotopes', 'Nitrogen Isotopes', 'Helium Isotopes']

FUEL_RACE_MAP = {
    'Oxygen Isotopes':   {'race': 'Amarr',    'ships': ['Ark', 'Archon', 'Revelation', 'Aeon', 'Avatar', 'Redeemer']},
    'Hydrogen Isotopes': {'race': 'Gallente',  'ships': ['Anshar', 'Thanatos', 'Moros', 'Nyx', 'Erebus', 'Sin']},
    'Nitrogen Isotopes': {'race': 'Caldari',   'ships': ['Rhea', 'Chimera', 'Phoenix', 'Wyvern', 'Leviathan', 'Widow']},
    'Helium Isotopes':   {'race': 'Minmatar',  'ships': ['Nomad', 'Nidhoggur', 'Naglfar', 'Hel', 'Ragnarok', 'Panther']},
}


@bp.route('/fuel/')
def fuel_page():
    return render_template('partials/fuel/index.html')


@bp.route('/api/fuel/prices')
def get_prices():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, fuel_type, price_per_unit, source, updated_at
        FROM ejrp_fuel_prices
        ORDER BY fuel_type
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = [serialize_row(r) for r in rows]

    for item in result:
        meta = FUEL_RACE_MAP.get(item['fuel_type'], {})
        item['race'] = meta.get('race', '')
        item['ships'] = meta.get('ships', [])

    return jsonify(result)


@bp.route('/api/fuel/prices', methods=['POST'])
def update_prices():
    data = request.get_json(silent=True) or []
    if isinstance(data, dict):
        data = [data]

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    conn = get_db()
    cur = conn.cursor()
    updated = 0
    for item in data:
        fuel_type = item.get('fuel_type', '').strip()
        try:
            price = float(item.get('price_per_unit', 0))
        except (TypeError, ValueError):
            continue
        source = item.get('source', 'manual').strip()

        if fuel_type not in FUEL_TYPES:
            continue
        if price < 0:
            continue

        cur.execute("""
            INSERT INTO ejrp_fuel_prices (fuel_type, price_per_unit, source, updated_at)
            VALUES (%(ft)s, %(price)s, %(source)s, NOW())
            ON CONFLICT (fuel_type) DO UPDATE
            SET price_per_unit = EXCLUDED.price_per_unit,
                source = EXCLUDED.source,
                updated_at = NOW()
        """, {'ft': fuel_type, 'price': price, 'source': source})
        updated += 1

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'updated': updated})


@bp.route('/api/fuel/estimate')
def estimate_cost():
    fuel_type = request.args.get('fuel_type', '')
    try:
        quantity = int(request.args.get('quantity', 0))
    except (TypeError, ValueError):
        quantity = 0

    if not fuel_type:
        return jsonify({'error': 'fuel_type required'}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT price_per_unit FROM ejrp_fuel_prices WHERE fuel_type = %(ft)s
    """, {'ft': fuel_type})
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({'error': 'Fuel type not found'}), 404

    price = float(row['price_per_unit'])
    cost = price * quantity
    return jsonify({
        'fuel_type': fuel_type,
        'quantity': quantity,
        'price_per_unit': price,
        'total_cost_isk': round(cost, 2),
    })


@bp.route('/api/fuel/history')
def price_history():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.fuel_type,
               COUNT(*) AS route_count,
               COALESCE(SUM(r.total_fuel), 0) AS total_isotopes,
               COALESCE(SUM(r.fuel_cost_isk), 0) AS total_spent_isk,
               COALESCE(AVG(r.fuel_price_isk), 0) AS avg_price_used,
               fp.price_per_unit AS current_price
        FROM ejrp_routes r
        LEFT JOIN ejrp_fuel_prices fp ON fp.fuel_type = r.fuel_type
        WHERE r.status != 'archived' AND r.fuel_type IS NOT NULL
        GROUP BY r.fuel_type, fp.price_per_unit
        ORDER BY total_spent_isk DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([serialize_row(r) for r in rows])
