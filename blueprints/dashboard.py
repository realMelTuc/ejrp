from flask import Blueprint, render_template, jsonify
from db import get_db, serialize_row

bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard/')
def dashboard():
    return render_template('partials/dashboard/index.html')


@bp.route('/api/dashboard/stats')
def stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*)                                                AS total_routes,
            COUNT(*) FILTER (WHERE status = 'active')              AS active_routes,
            COUNT(*) FILTER (WHERE status = 'completed')           AS completed_routes,
            COALESCE(SUM(total_jumps), 0)                          AS total_jumps_planned,
            COALESCE(SUM(total_fuel), 0)                           AS total_fuel_planned,
            COALESCE(SUM(fuel_cost_isk), 0)                        AS total_cost_isk,
            COALESCE(AVG(total_jumps) FILTER (WHERE total_jumps > 0), 0) AS avg_jumps_per_route,
            COALESCE(AVG(total_distance_ly) FILTER (WHERE total_distance_ly > 0), 0) AS avg_distance_ly
        FROM ejrp_routes
        WHERE status != 'archived'
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(serialize_row(row) if row else {})


@bp.route('/api/dashboard/recent-routes')
def recent_routes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.name, r.ship_name, r.ship_class,
               r.origin_system, r.destination_system,
               r.total_jumps, r.total_distance_ly, r.total_fuel,
               r.fuel_cost_isk, r.fuel_type, r.status, r.created_at
        FROM ejrp_routes r
        WHERE r.status != 'archived'
        ORDER BY r.created_at DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([serialize_row(r) for r in rows])


@bp.route('/api/dashboard/fuel-summary')
def fuel_summary():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT fuel_type, price_per_unit, source, updated_at
        FROM ejrp_fuel_prices
        ORDER BY fuel_type
    """)
    prices = cur.fetchall()

    cur.execute("""
        SELECT fuel_type,
               COUNT(*) AS route_count,
               COALESCE(SUM(total_fuel), 0) AS total_fuel,
               COALESCE(SUM(fuel_cost_isk), 0) AS total_cost_isk
        FROM ejrp_routes
        WHERE status != 'archived'
        GROUP BY fuel_type
        ORDER BY total_cost_isk DESC
    """)
    by_fuel = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({
        'prices': [serialize_row(p) for p in prices],
        'by_fuel': [serialize_row(b) for b in by_fuel],
    })


@bp.route('/api/dashboard/jump-log')
def jump_log():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, route_name, ship_name, from_system, to_system,
               total_jumps, total_fuel, total_cost_isk, executed_at, pilot_name
        FROM ejrp_jump_log
        ORDER BY executed_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([serialize_row(r) for r in rows])


@bp.route('/api/dashboard/ship-breakdown')
def ship_breakdown():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT ship_name, ship_class,
               COUNT(*) AS route_count,
               COALESCE(SUM(total_fuel), 0) AS total_fuel,
               COALESCE(SUM(fuel_cost_isk), 0) AS total_cost_isk,
               COALESCE(AVG(total_jumps), 0) AS avg_jumps
        FROM ejrp_routes
        WHERE status != 'archived'
        GROUP BY ship_name, ship_class
        ORDER BY route_count DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([serialize_row(r) for r in rows])
