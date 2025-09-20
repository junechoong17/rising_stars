import boto3
import json

# Initialize Bedrock Runtime client
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def ask_ai(question):
    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"text": question}   # <-- must be object with "text"
                ]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 512,
            "temperature": 0.7
        }
    }

    response = bedrock.invoke_model(
        modelId="amazon.nova-pro-v1:0",
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    return result["output"]["message"]["content"][0]["text"]

if __name__ == "__main__":
    q = input("Ask a question: ")
    answer = ask_ai(q)
    print("\nAI Answer:", answer)