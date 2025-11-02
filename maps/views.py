import os
from django.conf import settings
from django.http import JsonResponse

def map_view(request):
    try:
        import googlemaps
    except ModuleNotFoundError:
        return JsonResponse({'error': 'googlemaps package not installed'}, status=500)
    key = getattr(settings, 'GOOGLE_MAPS_API_KEY', os.environ.get('GOOGLE_MAPS_API_KEY'))
    if not key:
        return JsonResponse({'error': 'Google Maps API key not configured'}, status=500)
    client = googlemaps.Client(key=key)
    try:
        from_loc = client.geocode('Mohakhali, Dhaka')
        to_loc = client.geocode('Dhanmondi, Dhaka')
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    lat_from = from_loc[0]['geometry']['location']['lat']
    lng_from = from_loc[0]['geometry']['location']['lng']

    lat_to = to_loc[0]['geometry']['location']['lat']
    lng_to = to_loc[0]['geometry']['location']['lng']

    distance = client.distance_matrix(
        origins=[(lat_from, lng_from)],
        destinations=[(lat_to, lng_to)],
        mode='driving',
        units='metric'
    )

    distance_km = distance['rows'][0]['elements'][0]['distance']['value'] / 1000.0

    return JsonResponse({'Distance': f'From ({lat_from}, {lng_from}) to ({lat_to}, {lng_to})', 'Duration': distance['rows'][0]['elements'][0]['duration']['text'], 'Distance (km)': f"{distance_km:.1f}"})