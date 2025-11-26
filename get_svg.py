import requests
import json

response = requests.post('http://localhost:8000/generate_svg', json={})
data = response.json()
print(data['svg'])