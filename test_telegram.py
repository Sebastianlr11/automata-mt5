import requests

bot_token = "7585335993:AAEjKMYvYQsTPqdJTCFeRGv8g3NXSdKKtno"
chat_id = "7600273804"

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
data = {
    "chat_id": chat_id,
    "text": "🧪 Prueba de conexión - Si ves este mensaje, el bot funciona!"
}

response = requests.post(url, data=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")