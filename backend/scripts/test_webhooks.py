#!/usr/bin/env python3
"""Test script for webhook endpoints"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Sample webhook payloads based on actual SignalWire formats
TRANSCRIPTION_WEBHOOK = {
    "event_type": "live_transcribe.utterance",
    "event_channel": "relay.1234",
    "timestamp": int(datetime.now().timestamp() * 1000),
    "project_id": "test-project",
    "space_id": "test-space",
    "utterance": {
        "role": "remote-caller",
        "content": "Hello, I need help with my account",
        "lang": "en",
        "tokens": ["Hello", ",", "I", "need", "help", "with", "my", "account"],
        "timestamp": 1234567890,
        "confidence": 0.95
    },
    "call_info": {
        "call_id": "test-call-123",
        "node_id": "node-123",
        "tag": "test-tag"
    },
    "channel_data": {
        "SWMLVars": {
            "userVariables": {
                "destination_number": "+19184238080",
                "from_number": "+12544645483"
            }
        }
    }
}

CALL_STATE_WEBHOOK = {
    "event_type": "calling.call.state",
    "event_channel": "relay.1234",
    "timestamp": int(datetime.now().timestamp() * 1000),
    "project_id": "test-project",
    "space_id": "test-space",
    "params": {
        "call_id": "test-call-123",
        "node_id": "node-123",
        "segment_id": "segment-123",
        "call_state": "answered",
        "direction": "outbound",
        "device": {
            "type": "phone",
            "params": {
                "from_number": "+12544645483",
                "to_number": "+19184238080",
                "headers": []
            }
        },
        "start_time": int((datetime.now().timestamp() - 30) * 1000),
        "answer_time": int((datetime.now().timestamp() - 25) * 1000)
    }
}

RECORDING_STATUS_WEBHOOK = {
    "event_type": "calling.call.record",
    "event_channel": "relay.1234",
    "timestamp": int(datetime.now().timestamp() * 1000),
    "project_id": "test-project",
    "space_id": "test-space",
    "params": {
        "recording_id": "rec-123",
        "call_id": "test-call-123",
        "state": "completed",
        "url": "https://example.signalwire.com/recordings/rec-123.mp3",
        "record": {
            "audio": {
                "format": "mp3",
                "sample_rate": 8000,
                "channels": 2,
                "duration": 120.5,
                "size": 2048000,
                "bitrate": 128000,
                "codec": "mp3"
            }
        }
    }
}


async def test_webhook(endpoint: str, payload: dict, name: str):
    """Test a webhook endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/api/webhooks/{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                print(f"Status: {response.status}")
                print(f"Response: {json.dumps(result, indent=2)}")
                
                if response.status != 200:
                    print(f"ERROR: Expected 200, got {response.status}")
                else:
                    print("SUCCESS!")
                    
        except Exception as e:
            print(f"ERROR: {str(e)}")


async def main():
    """Run all webhook tests"""
    print("Starting webhook tests...")
    
    # Test transcription webhook
    await test_webhook("transcription", TRANSCRIPTION_WEBHOOK, "Transcription Webhook")
    
    # Test call state webhook
    await test_webhook("call-state", CALL_STATE_WEBHOOK, "Call State Webhook")
    
    # Test recording status webhook
    await test_webhook("recording-status", RECORDING_STATUS_WEBHOOK, "Recording Status Webhook")
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())