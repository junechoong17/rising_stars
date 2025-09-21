import requests

url = "http://127.0.0.1:8000/upload_documents/"

files = {"files": open(r"C:/Users/Laura Chang/Downloads/Visa.txt", "rb")}

response = requests.post(url, files=files)
print(response.json())

