import requests
import json

# Probar la búsqueda de cliente directamente
url = "http://127.0.0.1:5000/buscar-cliente"

data = {
    "search": "31223801"
}

try:
    print(f"🔍 Probando búsqueda de cliente: {data['search']}")
    print(f"URL: {url}")
    
    response = requests.post(url, json=data)
    
    print(f"\n📊 Respuesta HTTP:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Respuesta JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n❌ Error HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Error: No se puede conectar al servidor Flask")
    print("   ¿Está ejecutándose la aplicación?")
except Exception as e:
    print(f"❌ Error: {e}")