import requests

resp = requests.get(
    "https://api.flightapi.io/airline/671fcadaae9dba662864b01a?num=33&name=DL&date=20231024"
)
print(resp.json())
