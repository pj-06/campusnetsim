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