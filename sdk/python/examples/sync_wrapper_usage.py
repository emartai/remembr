"""Synchronous wrapper example for the Remembr SDK."""

from remembr import RemembrClient


def main() -> None:
    client = RemembrClient()
    health = client.request("GET", "/health")
    print(health)


if __name__ == "__main__":
    main()
