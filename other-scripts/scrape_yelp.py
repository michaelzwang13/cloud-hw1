import requests
import json
import time

YELP_API_KEY = 'MrpZvwd1FixrrW6dRVG88ETc-GNsgFEtK9FigKYTjg5O2x0bbfKkE0OPkv22ALUk6_pOowArt7moK5NVIbMRD6CINeziPHGX5-e6YeUyPBCnZnyO_GwIHTmri4mgaXYx'
HEADERS = {'Authorization': f'Bearer {YELP_API_KEY}'}
ENDPOINT = 'https://api.yelp.com/v3/businesses/search'

CUISINES = {
    'chinese': 'chinese',
    'indian': 'indpak',
    'mexican': 'mexican',
    'japanese': 'japanese',
    'italian': 'italian',
}

LOCATION = 'Manhattan, NY'
LIMIT = 50        
TARGET = 200     

def fetch_restaurants(cuisine_label, yelp_category):
    results = []
    offset = 0

    while len(results) < TARGET:
        params = {
            'location': LOCATION,
            'categories': yelp_category,
            'limit': LIMIT,
            'offset': offset,
        }
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        data = response.json()

        businesses = data.get('businesses', [])
        if not businesses:
            print(f'  No more results at offset {offset}')
            break

        for b in businesses:
            results.append({
                'id': b['id'],
                'name': b['name'],
                'cuisine': cuisine_label,
                'rating': b.get('rating'),
                'review_count': b.get('review_count'),
                'address': ', '.join(b['location']['display_address']),
                'zip_code': b['location'].get('zip_code'),
                'phone': b.get('display_phone'),
                'latitude': b['coordinates'].get('latitude'),
                'longitude': b['coordinates'].get('longitude'),
                'price': b.get('price'),
                'url': b.get('url'),
            })

        offset += LIMIT
        time.sleep(0.5)  

    return results[:TARGET]

all_restaurants = {}

for label, category in CUISINES.items():
    print(f'Fetching {label}...')
    restaurants = fetch_restaurants(label, category)
    all_restaurants[label] = restaurants
    print(f'  Got {len(restaurants)} restaurants')

with open('restaurants.json', 'w') as f:
    json.dump(all_restaurants, f, indent=2)

total = sum(len(v) for v in all_restaurants.values())
print(f'\nDone. {total} restaurants saved to restaurants.json')
