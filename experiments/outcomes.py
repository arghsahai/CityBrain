"""SUMO disappearance is not evidence of a successful emergency trip."""
def classify_step(vehicle_id, present, arrived, starting_teleports, teleported=False):
    if teleported or vehicle_id in starting_teleports:
        return "TELEPORTED"
    if vehicle_id in arrived:
        return "SUCCESS"
    if vehicle_id not in present:
        return "FAILED_BLOCKED"
    return None
