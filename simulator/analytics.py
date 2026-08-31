def calculate_utilization(current_users, capacity):
    if capacity <= 0:
        return 0

    return (current_users / capacity) * 100


def get_status(utilization):
    if utilization < 70:
        return "NORMAL"

    elif utilization < 90:
        return "BUSY"

    elif utilization < 100:
        return "HIGH_LOAD"

    else:
        return "CONGESTED"


def available_capacity(current_users, capacity):
    return max(capacity - current_users, 0)

def recommend_ap(state, congested_ap_id):
    """Recommend a candidate AP with spare capacity for a congested AP.

    Prefers another AP in the same building (physically nearest to the
    user); if none have room, widens the search to the whole campus.
    Picks the candidate with the most available capacity.

    This is a simple, explainable heuristic -- not an optimized/learned
    policy. See literature review gap notes: novelty is the integrated
    platform, not this algorithm.
    """
    congested_info = state.ap_info[congested_ap_id]
    building = congested_info["building"]

    def capacity_left(ap_id):
        info = state.ap_info[ap_id]
        used = len(state.connected_devices[ap_id])
        return available_capacity(used, info["capacity"])

    same_building = [
        ap_id for ap_id, info in state.ap_info.items()
        if info["building"] == building
        and ap_id != congested_ap_id
        and capacity_left(ap_id) > 0
    ]
    candidates = same_building or [
        ap_id for ap_id in state.ap_info
        if ap_id != congested_ap_id and capacity_left(ap_id) > 0
    ]

    if not candidates:
        return None

    best_ap_id = max(candidates, key=capacity_left)
    best_info = state.ap_info[best_ap_id]
    best_used = len(state.connected_devices[best_ap_id])

    return {
        "recommended_ap_id": best_ap_id,
        "building": best_info["building"],
        "available_capacity": capacity_left(best_ap_id),
        "projected_utilization": round(
            ((best_used + 1) / best_info["capacity"]) * 100, 2
        ),
    }
