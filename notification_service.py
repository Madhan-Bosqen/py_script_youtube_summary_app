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

def send_new_video_notification(title: str, channel_name: str, video_id: str):
    """
    Broadcasts a push notification to all users subscribed to the channel's topic.
    """
    # 1. Format the topic name EXACTLY how Flutter formatted it!
    # Flutter did: 'channel_${channelName.replaceAll(' ', '')}'
    safe_topic_name = f"channel_{channel_name.replace(' ', '')}"
    
    try:
        # 2. Build the Message using 'topic=' instead of 'token='
        message = messaging.Message(
            notification=messaging.Notification(
                title=f"🔥 New Video: {channel_name}",
                body=f"Summary ready for: {title}",
            ),
            data={
                "video_id": video_id,
                "channel_name": channel_name,
                "click_action": "FLUTTER_NOTIFICATION_CLICK" # Helps Flutter handle taps later
            },
            topic=safe_topic_name  # <-- THE MAGIC HAPPENS HERE
        )

        # 3. Send the broadcast!
        response = messaging.send(message)
        print(f"📲 Successfully broadcasted to topic '{safe_topic_name}'!")
        print(f"Firebase Message ID: {response}")
        return True
    
    except Exception as e:
        print(f"❌ Error sending topic notification: {e}")
        return False