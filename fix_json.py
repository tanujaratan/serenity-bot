import json

# 🔒 Replace this path with your actual Firebase JSON file path
firebase_file = r"D:\gen-ai-hackthon\serenity_bot\serenity-bot-430b8-firebase-adminsdk-fbsvc-d4d78587a9.json"

with open(firebase_file, "r") as f:
    data = json.load(f)

escaped = json.dumps(data)

print("\n✅ Copy the line below and paste it into your .env file:\n")
print("FIREBASE_SERVICE_ACCOUNT_JSON=" + escaped)

