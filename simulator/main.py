from simulator.traffic_generator import generate_event
from simulator.analytics import calculate_utilization, get_status


def main():

    print("=== CampusNetSim ===")
    print("Generating sample WiFi events...\n")

    for _ in range(10):

        event = generate_event()

        print(event.to_dict())

    print("\n=== Sample AP Analytics ===")

    current_users = 72
    capacity = 75

    utilization = calculate_utilization(
        current_users,
        capacity
    )

    status = get_status(utilization)

    print(f"Current Users : {current_users}")
    print(f"Capacity      : {capacity}")
    print(f"Utilization   : {utilization:.2f}%")
    print(f"Status        : {status}")


if __name__ == "__main__":
    main()