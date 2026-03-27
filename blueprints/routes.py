from flask import Blueprint, render_template, jsonify, request
from db import get_db, serialize_row

bp = Blueprint('routes', __name__)


@bp.route('/routes/')
def routes_list():
    return render_template('partials/routes/index.html')


@bp.route('/routes/<int:route_id>/')
def route_detail(route_id):
    return render_template('partials/routes/detail.html', route_id=route_id)


@bp.route('/api/routes')
def api_routes():
    ship_filter = request.args.get('ship', '')
    status_filter = request.args.get('status', '')
    search = request.args.get('q', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 25

    conditions = ["status != 'archived'"]
    params = {}

    if ship_filter:
        conditions.append('ship_name = %(ship)s')
        params['ship'] = ship_filter
    if status_filter:
        conditions.append('status = %(status)s')
        params['status'] = status_filter
    if search:
        conditions.append("(name ILIKE %(q)s OR origin_system ILIKE %(q)s OR destination_system ILIKE %(q)s)")
        params['q'] = f'%{search}%'

    where = ' AND '.join(conditions)
    params['limit'] = per_page
    params['offset'] = (page - 1) * per_page

    conn = get_db()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) AS total FROM ejrp_routes WHERE {where}",
                {k: v for k, v in params.items() if k not in ('limit', 'offset')})
    total = cur.fetchone()['total']

    cur.execute(f"""
        SELECT id, name, ship_name, ship_class, origin_system, destination_system,
               jdc_level, jdfe_level, total_jumps, total_distance_ly, total_fuel,
               fuel_type, fuel_cost_isk, status, tags, created_at, updated_at
        FROM ejrp_routes
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        'routes': [serialize_row(r) for r in rows],
        'total': total,
        'page': page,
        'pages': max(1, -(-total // per_page)),
    })


@bp.route('/api/routes/<int:route_id>')
def api_route_detail(route_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.name, r.ship_name, r.ship_class,
               r.origin_system, r.destination_system,
               r.jdc_level, r.jdfe_level,
               r.total_jumps, r.total_distance_ly, r.total_fuel,
               r.fuel_type, r.fuel_cost_isk, r.fuel_price_isk,
               r.status, r.tags, r.notes,
               r.created_at, r.updated_at
        FROM ejrp_routes r
        WHERE r.id = %(id)s
    """, {'id': route_id})
    route = cur.fetchone()
    if not route:
        cur.close()
        conn.close()
        return jsonify({'error': 'Route not found'}), 404

    cur.execute("""
        SELECT step_number, from_system, to_system, distance_ly,
               fuel_used, cost_isk, within_range, jump_type, notes
        FROM ejrp_route_steps
        WHERE route_id = %(id)s
        ORDER BY step_number
    """, {'id': route_id})
    steps = cur.fetchall()
    cur.close()
    conn.close()

    result = serialize_row(route)
    result['steps'] = [serialize_row(s) for s in steps]
    return jsonify(result)


@bp.route('/api/routes/<int:route_id>/status', methods=['POST'])
def update_status(route_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '')
    valid = ('saved', 'active', 'completed', 'archived')
    if new_status not in valid:
        return jsonify({'error': f'Invalid status. Must be one of: {valid}'}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ejrp_routes
        SET status = %(status)s, updated_at = NOW()
        WHERE id = %(id)s
        RETURNING id
    """, {'status': new_status, 'id': route_id})
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return jsonify({'error': 'Route not found'}), 404
    return jsonify({'updated': True, 'status': new_status})


@bp.route('/api/routes/<int:route_id>/log', methods=['POST'])
def log_execution(route_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM ejrp_routes WHERE id = %(id)s", {'id': route_id})
    route = cur.fetchone()
    if not route:
        cur.close()
        conn.close()
        return jsonify({'error': 'Route not found'}), 404

    cur.execute("""
        INSERT INTO ejrp_jump_log
            (route_id, route_name, ship_name, from_system, to_system,
             total_jumps, total_distance_ly, total_fuel, total_cost_isk,
             pilot_name, notes)
        VALUES
            (%(rid)s, %(name)s, %(ship)s, %(from_s)s, %(to_s)s,
             %(jumps)s, %(dist)s, %(fuel)s, %(cost)s,
             %(pilot)s, %(notes)s)
        RETURNING id
    """, {
        'rid': route_id,
        'name': route['name'],
        'ship': route['ship_name'],
        'from_s': route['origin_system'],
        'to_s': route['destination_system'],
        'jumps': route['total_jumps'],
        'dist': route['total_distance_ly'],
        'fuel': route['total_fuel'],
        'cost': route['fuel_cost_isk'],
        'pilot': data.get('pilot_name', ''),
        'notes': data.get('notes', ''),
    })
    row = cur.fetchone()

    cur.execute("""
        UPDATE ejrp_routes SET status = 'completed', updated_at = NOW()
        WHERE id = %(id)s
    """, {'id': route_id})

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'log_id': row['id'], 'logged': True})


@bp.route('/api/routes/<int:route_id>/delete', methods=['POST'])
def delete_route(route_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ejrp_routes SET status = 'archived', updated_at = NOW()
        WHERE id = %(id)s RETURNING id
    """, {'id': route_id})
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not row:
        return jsonify({'error': 'Route not found'}), 404
    return jsonify({'deleted': True})
