import requests

# Your deployed Replit API URL
url = "https://mbti-pdf-api.jeralyntrose.repl.co/upload"

# Replace this with the actual filename you uploaded to Replit
file_path = "example.pdf"

with open(file_path, "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

print("Status Code:", response.status_code)
print("Response:", response.json())
