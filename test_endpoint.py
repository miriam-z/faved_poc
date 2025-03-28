import requests
import json


def test_text_submission():
    url = "http://localhost:8000/text/"
    payload = {"text": "This is a test submission for evaluation"}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    test_text_submission()
