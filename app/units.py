KG_TO_LB = 2.2046226218
CM_TO_IN = 0.3937007874


def weight_unit(unit_system):
    return "lb" if unit_system == "imperial" else "kg"


def height_unit(unit_system):
    return "in" if unit_system == "imperial" else "cm"


def display_weight(value_kg, unit_system):
    if value_kg is None:
        return None
    value = value_kg * KG_TO_LB if unit_system == "imperial" else value_kg
    return round(value, 1)


def stored_weight(value, unit_system):
    if value is None:
        return None
    return value / KG_TO_LB if unit_system == "imperial" else value


def display_height(value_cm, unit_system):
    if value_cm is None:
        return None
    value = value_cm * CM_TO_IN if unit_system == "imperial" else value_cm
    return round(value, 1)


def stored_height(value, unit_system):
    if value is None:
        return None
    return value / CM_TO_IN if unit_system == "imperial" else value
