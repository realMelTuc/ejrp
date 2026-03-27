"""
EJRP Jump Calculation Engine
EVE Online jump drive mechanics for route planning.

Jump Drive Calibration (JDC): +25% max range per skill level (x1 to x2.25 at L5)
Jump Drive Fuel Economy (JDFE): -10% fuel per skill level (x1 to x0.50 at L5)
"""
import math

# ── Ship Data ──────────────────────────────────────────────────────────────────
# base_range_ly: range at skill 0 (JDC0)
# base_fuel_per_ly: isotopes per LY at JDFE0

SHIPS = {
    # ── Jump Freighters ────────────────────────────────────────────────────────
    'Ark': {
        'class': 'jump_freighter', 'race': 'Amarr',
        'base_range_ly': 3.5, 'fuel_type': 'Oxygen Isotopes',
        'base_fuel_per_ly': 1000, 'cargo_m3': 362500,
    },
    'Anshar': {
        'class': 'jump_freighter', 'race': 'Gallente',
        'base_range_ly': 3.5, 'fuel_type': 'Hydrogen Isotopes',
        'base_fuel_per_ly': 1000, 'cargo_m3': 375000,
    },
    'Rhea': {
        'class': 'jump_freighter', 'race': 'Caldari',
        'base_range_ly': 3.5, 'fuel_type': 'Nitrogen Isotopes',
        'base_fuel_per_ly': 1000, 'cargo_m3': 362500,
    },
    'Nomad': {
        'class': 'jump_freighter', 'race': 'Minmatar',
        'base_range_ly': 3.5, 'fuel_type': 'Helium Isotopes',
        'base_fuel_per_ly': 1000, 'cargo_m3': 337500,
    },
    # ── Carriers ──────────────────────────────────────────────────────────────
    'Archon': {
        'class': 'carrier', 'race': 'Amarr',
        'base_range_ly': 3.5, 'fuel_type': 'Oxygen Isotopes',
        'base_fuel_per_ly': 2500,
    },
    'Chimera': {
        'class': 'carrier', 'race': 'Caldari',
        'base_range_ly': 3.5, 'fuel_type': 'Nitrogen Isotopes',
        'base_fuel_per_ly': 2500,
    },
    'Thanatos': {
        'class': 'carrier', 'race': 'Gallente',
        'base_range_ly': 3.5, 'fuel_type': 'Hydrogen Isotopes',
        'base_fuel_per_ly': 2500,
    },
    'Nidhoggur': {
        'class': 'carrier', 'race': 'Minmatar',
        'base_range_ly': 3.5, 'fuel_type': 'Helium Isotopes',
        'base_fuel_per_ly': 2500,
    },
    # ── Dreadnoughts ──────────────────────────────────────────────────────────
    'Revelation': {
        'class': 'dreadnought', 'race': 'Amarr',
        'base_range_ly': 3.5, 'fuel_type': 'Oxygen Isotopes',
        'base_fuel_per_ly': 2000,
    },
    'Phoenix': {
        'class': 'dreadnought', 'race': 'Caldari',
        'base_range_ly': 3.5, 'fuel_type': 'Nitrogen Isotopes',
        'base_fuel_per_ly': 2000,
    },
    'Moros': {
        'class': 'dreadnought', 'race': 'Gallente',
        'base_range_ly': 3.5, 'fuel_type': 'Hydrogen Isotopes',
        'base_fuel_per_ly': 2000,
    },
    'Naglfar': {
        'class': 'dreadnought', 'race': 'Minmatar',
        'base_range_ly': 3.5, 'fuel_type': 'Helium Isotopes',
        'base_fuel_per_ly': 2000,
    },
    # ── Supercarriers ─────────────────────────────────────────────────────────
    'Aeon': {
        'class': 'supercarrier', 'race': 'Amarr',
        'base_range_ly': 3.5, 'fuel_type': 'Oxygen Isotopes',
        'base_fuel_per_ly': 3500,
    },
    'Wyvern': {
        'class': 'supercarrier', 'race': 'Caldari',
        'base_range_ly': 3.5, 'fuel_type': 'Nitrogen Isotopes',
        'base_fuel_per_ly': 3500,
    },
    'Nyx': {
        'class': 'supercarrier', 'race': 'Gallente',
        'base_range_ly': 3.5, 'fuel_type': 'Hydrogen Isotopes',
        'base_fuel_per_ly': 3500,
    },
    'Hel': {
        'class': 'supercarrier', 'race': 'Minmatar',
        'base_range_ly': 3.5, 'fuel_type': 'Helium Isotopes',
        'base_fuel_per_ly': 3500,
    },
    # ── Titans ────────────────────────────────────────────────────────────────
    'Avatar': {
        'class': 'titan', 'race': 'Amarr',
        'base_range_ly': 3.5, 'fuel_type': 'Oxygen Isotopes',
        'base_fuel_per_ly': 5000,
    },
    'Leviathan': {
        'class': 'titan', 'race': 'Caldari',
        'base_range_ly': 3.5, 'fuel_type': 'Nitrogen Isotopes',
        'base_fuel_per_ly': 5000,
    },
    'Erebus': {
        'class': 'titan', 'race': 'Gallente',
        'base_range_ly': 3.5, 'fuel_type': 'Hydrogen Isotopes',
        'base_fuel_per_ly': 5000,
    },
    'Ragnarok': {
        'class': 'titan', 'race': 'Minmatar',
        'base_range_ly': 3.5, 'fuel_type': 'Helium Isotopes',
        'base_fuel_per_ly': 5000,
    },
    # ── Black Ops Battleships ─────────────────────────────────────────────────
    'Redeemer': {
        'class': 'black_ops', 'race': 'Amarr',
        'base_range_ly': 2.5, 'fuel_type': 'Oxygen Isotopes',
        'base_fuel_per_ly': 500,
    },
    'Widow': {
        'class': 'black_ops', 'race': 'Caldari',
        'base_range_ly': 2.5, 'fuel_type': 'Nitrogen Isotopes',
        'base_fuel_per_ly': 500,
    },
    'Sin': {
        'class': 'black_ops', 'race': 'Gallente',
        'base_range_ly': 2.5, 'fuel_type': 'Hydrogen Isotopes',
        'base_fuel_per_ly': 500,
    },
    'Panther': {
        'class': 'black_ops', 'race': 'Minmatar',
        'base_range_ly': 2.5, 'fuel_type': 'Helium Isotopes',
        'base_fuel_per_ly': 500,
    },
}

CLASS_LABELS = {
    'jump_freighter': 'Jump Freighter',
    'carrier': 'Carrier',
    'dreadnought': 'Dreadnought',
    'supercarrier': 'Supercarrier',
    'titan': 'Titan',
    'black_ops': 'Black Ops',
}

SHIPS_BY_CLASS = {}
for name, data in SHIPS.items():
    cls = data['class']
    if cls not in SHIPS_BY_CLASS:
        SHIPS_BY_CLASS[cls] = []
    SHIPS_BY_CLASS[cls].append(name)

FUEL_TYPES = ['Oxygen Isotopes', 'Hydrogen Isotopes', 'Nitrogen Isotopes', 'Helium Isotopes']


def get_ship(name: str) -> dict | None:
    return SHIPS.get(name)


def effective_range(base_range_ly: float, jdc_level: int) -> float:
    jdc_level = max(0, min(5, jdc_level))
    return round(base_range_ly * (1.0 + 0.25 * jdc_level), 4)


def fuel_for_jump(base_fuel_per_ly: int, distance_ly: float, jdfe_level: int) -> int:
    jdfe_level = max(0, min(5, jdfe_level))
    multiplier = max(0.01, 1.0 - 0.10 * jdfe_level)
    return max(1, math.ceil(distance_ly * base_fuel_per_ly * multiplier))


def calculate_route(
    ship_name: str,
    waypoints: list,
    jdc_level: int,
    jdfe_level: int,
    fuel_price_isk: float,
) -> dict:
    ship = get_ship(ship_name)
    if not ship:
        return {'error': f'Unknown ship: {ship_name}', 'valid': False}

    max_range = effective_range(ship['base_range_ly'], jdc_level)
    steps = []
    total_fuel = 0
    total_distance = 0.0
    has_out_of_range = False

    for i, wp in enumerate(waypoints):
        try:
            dist = float(wp.get('distance_ly', 0))
        except (TypeError, ValueError):
            dist = 0.0

        fuel = fuel_for_jump(ship['base_fuel_per_ly'], dist, jdfe_level)
        within_range = dist <= max_range
        if not within_range:
            has_out_of_range = True

        cost_isk = fuel * fuel_price_isk
        total_fuel += fuel
        total_distance += dist

        steps.append({
            'step': i + 1,
            'from_system': wp.get('from', ''),
            'to_system': wp.get('to', ''),
            'distance_ly': round(dist, 4),
            'fuel': fuel,
            'cost_isk': round(cost_isk, 2),
            'within_range': within_range,
            'max_range': round(max_range, 2),
        })

    total_cost_isk = total_fuel * fuel_price_isk

    return {
        'valid': not has_out_of_range,
        'has_out_of_range': has_out_of_range,
        'ship_name': ship_name,
        'ship_class': CLASS_LABELS.get(ship['class'], ship['class']),
        'fuel_type': ship['fuel_type'],
        'max_range_ly': round(max_range, 2),
        'jdc_level': jdc_level,
        'jdfe_level': jdfe_level,
        'total_jumps': len(steps),
        'total_distance_ly': round(total_distance, 4),
        'total_fuel': total_fuel,
        'total_cost_isk': round(total_cost_isk, 2),
        'fuel_price_isk': fuel_price_isk,
        'steps': steps,
    }
