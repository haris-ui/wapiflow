import hashlib
import hmac
import json
import httpx

url = "http://localhost:8000/api/v1/webhooks/whatsapp"

payload = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "100652245",
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550234567",
                            "phone_number_id": "100652245"
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Customer John Doe"},
                                "wa_id": "15558901234"
                            }
                        ],
                        "messages": [
                            {
                                "from": "15558901234",
                                "id": "wamid.TEST_MESSAGE_001_INBOUND",
                                "timestamp": "1710684000",
                                "text": {"body": "Hi, I would like to order 2 bags of Ethiopian Yirgacheffe coffee!"},
                                "type": "text"
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

body_bytes = json.dumps(payload).encode("utf-8")
headers = {
    "Content-Type": "application/json",
    "X-Hub-Signature-256": "sha256=test_signature"
}

r = httpx.post(url, headers=headers, content=body_bytes)
print("Webhook POST status:", r.status_code)
print("Webhook POST response:", r.json())
