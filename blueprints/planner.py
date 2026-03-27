from flask import Blueprint, render_template, jsonify, request
from db import get_db, serialize_row
from jump_calc import SHIPS, SHIPS_BY_CLASS, CLASS_LABELS, calculate_route, get_ship

bp = Blueprint('planner', __name__)


@bp.route('/planner/')
def planner():
    return render_template('partials/planner/index.html')


@bp.route('/api/planner/ships')
def ships():
    result = []
    class_order = ['jump_freighter', 'carrier', 'dreadnought', 'supercarrier', 'titan', 'black_ops']
    for cls in class_order:
        if cls not in SHIPS_BY_CLASS:
            continue
        result.append({
            'class': cls,
            'label': CLASS_LABELS.get(cls, cls),
            'ships': sorted(SHIPS_BY_CLASS[cls]),
        })
    return jsonify(result)


@bp.route('/api/planner/ship/<name>')
def ship_detail(name):
    s = get_ship(name)
    if not s:
        return jsonify({'error': 'Ship not found'}), 404
    return jsonify({
        'name': name,
        'class': CLASS_LABELS.get(s['class'], s['class']),
        'race': s['race'],
        'base_range_ly': s['base_range_ly'],
        'fuel_type': s['fuel_type'],
        'base_fuel_per_ly': s['base_fuel_per_ly'],
        'cargo_m3': s.get('cargo_m3'),
    })


@bp.route('/api/planner/calculate', methods=['POST'])
def calculate():
    data = request.get_json(silent=True) or {}
    ship_name = data.get('ship_name', '')
    jdc_level = int(data.get('jdc_level', 5))
    jdfe_level = int(data.get('jdfe_level', 5))
    fuel_price_isk = float(data.get('fuel_price_isk', 500))
    waypoints = data.get('waypoints', [])

    if not ship_name:
        return jsonify({'error': 'ship_name required'}), 400
    if not waypoints:
        return jsonify({'error': 'waypoints required'}), 400

    result = calculate_route(ship_name, waypoints, jdc_level, jdfe_level, fuel_price_isk)
    return jsonify(result)


@bp.route('/api/planner/save', methods=['POST'])
def save_route():
    data = request.get_json(silent=True) or {}
    ship_name = data.get('ship_name', '')
    jdc_level = int(data.get('jdc_level', 5))
    jdfe_level = int(data.get('jdfe_level', 5))
    fuel_price_isk = float(data.get('fuel_price_isk', 500))
    waypoints = data.get('waypoints', [])
    route_name = data.get('name', '').strip()
    notes = data.get('notes', '').strip()
    tags = data.get('tags', '').strip()

    if not ship_name:
        return jsonify({'error': 'ship_name required'}), 400
    if not waypoints:
        return jsonify({'error': 'waypoints required'}), 400
    if not route_name:
        return jsonify({'error': 'Route name required'}), 400

    calc = calculate_route(ship_name, waypoints, jdc_level, jdfe_level, fuel_price_isk)
    if 'error' in calc and not calc.get('steps'):
        return jsonify({'error': calc['error']}), 400

    ship = get_ship(ship_name)
    origin = waypoints[0].get('from', '') if waypoints else ''
    destination = waypoints[-1].get('to', '') if waypoints else ''

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ejrp_routes
                (name, ship_name, ship_class, origin_system, destination_system,
                 jdc_level, jdfe_level, total_jumps, total_distance_ly, total_fuel,
                 fuel_type, fuel_cost_isk, fuel_price_isk, status, tags, notes)
            VALUES
                (%(name)s, %(ship_name)s, %(ship_class)s, %(origin)s, %(destination)s,
                 %(jdc)s, %(jdfe)s, %(jumps)s, %(dist)s, %(fuel)s,
                 %(fuel_type)s, %(cost)s, %(price)s, 'saved', %(tags)s, %(notes)s)
            RETURNING id
        """, {
            'name': route_name,
            'ship_name': ship_name,
            'ship_class': calc.get('ship_class', ''),
            'origin': origin,
            'destination': destination,
            'jdc': jdc_level,
            'jdfe': jdfe_level,
            'jumps': calc['total_jumps'],
            'dist': calc['total_distance_ly'],
            'fuel': calc['total_fuel'],
            'fuel_type': calc.get('fuel_type', ''),
            'cost': calc['total_cost_isk'],
            'price': fuel_price_isk,
            'tags': tags or None,
            'notes': notes or None,
        })
        row = cur.fetchone()
        route_id = row['id']

        for step in calc['steps']:
            cur.execute("""
                INSERT INTO ejrp_route_steps
                    (route_id, step_number, from_system, to_system,
                     distance_ly, fuel_used, cost_isk, within_range)
                VALUES
                    (%(route_id)s, %(step)s, %(from_s)s, %(to_s)s,
                     %(dist)s, %(fuel)s, %(cost)s, %(range)s)
            """, {
                'route_id': route_id,
                'step': step['step'],
                'from_s': step['from_system'],
                'to_s': step['to_system'],
                'dist': step['distance_ly'],
                'fuel': step['fuel'],
                'cost': step['cost_isk'],
                'range': step['within_range'],
            })

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'id': route_id, 'saved': True})
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise
