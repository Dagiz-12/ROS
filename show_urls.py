# show_urls.py
from django.urls import get_resolver
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ROS.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()


def show_all_urls():
    """Show all registered URLs"""
    print("=" * 80)
    print("CURRENT URL CONFIGURATION")
    print("=" * 80)

    resolver = get_resolver()
    urls = []

    def extract_urls(url_patterns, prefix=''):
        for pattern in url_patterns:
            if hasattr(pattern, 'url_patterns'):
                # This is an include
                extract_urls(pattern.url_patterns,
                             prefix + str(pattern.pattern))
            else:
                # This is a path
                url_pattern = prefix + str(pattern.pattern)
                url_name = pattern.name if hasattr(
                    pattern, 'name') else 'No name'
                urls.append((url_pattern, url_name))

    extract_urls(resolver.url_patterns)

    # Sort and display
    urls.sort(key=lambda x: x[0])
    for url_pattern, url_name in urls:
        print(f"{url_pattern:<60} {url_name}")

    print("\n" + "=" * 80)
    print("URLS TO TEST:")
    print("=" * 80)
    test_urls = [
        '/',
        '/login/',
        '/waiter/dashboard/',
        '/chef/dashboard/',
        '/cashier/dashboard/',
        '/qr-menu/1/1/',
        '/api/auth/login/',
        '/api/restaurants/restaurants/1/',
        '/api/menu/public/1/',
    ]

    for url in test_urls:
        try:
            match = resolver.resolve(url)
            print(f"✅ {url} -> {match.func.__name__}")
        except:
            print(f"❌ {url} -> NOT FOUND")


if __name__ == "__main__":
    show_all_urls()
