"""
Mock data generator for e-commerce API with realistic distributions.
"""
import json
import random
import time
from typing import Any, List, Dict
import numpy as np

# Python 3.8 compatibility
try:
    from numpy.typing import NDArray
except ImportError:
    NDArray = np.ndarray  # type: ignore


class DataGenerator:
    def __init__(self, seed: int = 42) -> None:
        random.seed(seed)
        np.random.seed(seed)

        # Configuration
        self.num_products = 10000
        self.num_users = 50000

        # Zipfian distribution for product popularity
        self.zipf_products: NDArray[np.floating[Any]] = self._generate_zipfian(self.num_products, 1.2)

        # Common search queries with Zipfian distribution
        self.search_queries = [
            "laptop", "phone", "headphones", "shoes", "watch", "bag",
            "keyboard", "mouse", "monitor", "desk", "chair", "camera",
            "tablet", "speaker", "charger", "cable", "case", "stand",
            "backpack", "wallet", "sunglasses", "jacket", "shirt", "pants"
        ] * 100  # Extend for variety

        self.countries = ["USA", "UK", "Canada", "Germany", "France", "Japan", "Australia"]
        self.cities = {
            "USA": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
            "UK": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow"],
            "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
            "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
            "France": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice"],
            "Japan": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Kyoto"],
            "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"]
        }

        self.payment_methods = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]
        self.device_types = ["desktop", "mobile", "tablet"]
        self.referrers = ["google", "facebook", "direct", "instagram", "email", "twitter"]
        self.filters = ["price_low_to_high", "price_high_to_low", "newest", "popular", "rating"]

        # Start timestamp (Jan 1, 2024)
        self.base_timestamp = int(time.mktime(time.strptime("2024-01-01", "%Y-%m-%d")))

    def _generate_zipfian(self, n: int, alpha: float) -> NDArray:  # type: ignore[type-arg]
        """Generate Zipfian distribution for realistic product popularity."""
        ranks = np.arange(1, n + 1)
        probabilities = 1.0 / (ranks ** alpha)
        probabilities /= probabilities.sum()
        return probabilities

    def _get_popular_product(self) -> int:
        """Get a product ID following Zipfian distribution."""
        return int(np.random.choice(self.num_products, p=self.zipf_products))

    def _random_timestamp(self) -> int:
        """Generate random timestamp within 2024."""
        return self.base_timestamp + random.randint(0, 365 * 24 * 3600)

    def generate_order(self) -> Dict[str, Any]:
        """Generate a single order."""
        country = random.choice(self.countries)
        city = random.choice(self.cities[country])

        num_items = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
        items = []
        total = 0.0

        for _ in range(num_items):
            product_id = self._get_popular_product()
            quantity = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
            price = round(random.uniform(10.0, 500.0), 2)
            items.append({
                "product_id": product_id,
                "quantity": quantity,
                "price": price
            })
            total += price * quantity

        return {
            "order_id": f"ORD-{random.randint(1000000, 9999999)}",
            "user_id": random.randint(1, self.num_users),
            "timestamp": self._random_timestamp(),
            "items": items,
            "shipping_address": {
                "street": f"{random.randint(1, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Cedar', 'Park'])} St",
                "city": city,
                "postal_code": f"{random.randint(10000, 99999)}",
                "country": country
            },
            "payment_method": random.choice(self.payment_methods),
            "total_amount": round(total, 2)
        }

    def generate_product_view(self) -> Dict[str, Any]:
        """Generate a single product view event."""
        return {
            "user_id": random.randint(1, self.num_users),
            "product_id": self._get_popular_product(),
            "timestamp": self._random_timestamp(),
            "referrer": random.choice(self.referrers),
            "device_type": random.choice(self.device_types)
        }

    def generate_search_request(self) -> Dict[str, Any]:
        """Generate a single search request."""
        return {
            "user_id": random.randint(1, self.num_users),
            "query": random.choice(self.search_queries),
            "timestamp": self._random_timestamp(),
            "page": random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 5, 5])[0],
            "limit": random.choice([20, 50, 100]),
            "filters": random.sample(self.filters, k=random.randint(0, 3))
        }

    def generate_batch(self, data_type: str, count: int) -> List[Dict[str, Any]]:
        """Generate a batch of data."""
        generators = {
            "order": self.generate_order,
            "product_view": self.generate_product_view,
            "search": self.generate_search_request
        }

        generator = generators[data_type]
        return [generator() for _ in range(count)]


if __name__ == "__main__":
    # Quick test
    gen = DataGenerator()

    print("Sample Order:")
    print(json.dumps(gen.generate_order(), indent=2))

    print("\nSample Product View:")
    print(json.dumps(gen.generate_product_view(), indent=2))

    print("\nSample Search Request:")
    print(json.dumps(gen.generate_search_request(), indent=2))
