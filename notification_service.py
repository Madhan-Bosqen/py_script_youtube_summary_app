import os
import firebase_admin
from firebase_admin import credentials, messaging

# 1. Get the exact folder where this Python script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Build the exact path to the JSON file
cred_path = os.path.join(BASE_DIR, "firebase-credentials.json")

# 3. Check if the file actually exists before crashing!
if not os.path.exists(cred_path):
    print(f"\n🚨 CRITICAL ERROR: Could not find Firebase credentials at:")
    print(f"🚨 {cred_path}")
    print("🚨 Please make sure the JSON file is downloaded and placed in that exact location.\n")
else:
    # Initialize Firebase Admin only if the file exists
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

def send_new_video_notification(title: str, channel_name: str):
    """
    Sends a push notification to your specific device.
    """
    # ... (Keep the rest of your function exactly the same) ...
    # Your hardcoded Flutter device token for testing!
    my_phone_token = "fww1pO-gRi27MLhO_vupYj:APA91bFzl0_QpRTm2P9Xd_YATPRvuNpntauLp20Xo9qVgLg4xywxdysNvUjMwMGu-k5wcIoBRv10swimLsg8CV4xoshj1SHVE1k4wgfa2Al--lCQx-tTrX8"
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=f"New Video: {channel_name} 🚀",
                body=f"Summary ready for: {title}",
            ),
            token=my_phone_token,
        )

        response = messaging.send(message)
        print(f"📲 Successfully sent notification to your phone! Firebase ID: {response}")
        return True
    
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        return False