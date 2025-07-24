import httpx
from typing import Dict, Any, Optional
import logging
from core.config import settings
import base64

logger = logging.getLogger(__name__)


class SignalWireService:
    def __init__(self):
        self.project_id = settings.signalwire_project_id or ""
        self.api_token = settings.signalwire_token or ""
        self.space_url = settings.signalwire_space_url or ""
        self.from_number = settings.signalwire_from_number or ""
        
        # Create auth header
        auth_string = f"{self.project_id}:{self.api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
        
        # Base URL for API calls
        self.api_base = f"https://{self.space_url}/api/laml/2010-04-01"
        
    async def place_call(
        self,
        to_number: str,
        agent_name: str,
        listening_mode: str = "both",
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place a call using SignalWire API with live transcription"""
        
        if not webhook_url:
            webhook_url = f"{settings.public_url}/api/webhooks/transcription"
            
        # Create a SWML bin URL that will be used for this call
        swml_url = await self._create_swml_bin(to_number, webhook_url, listening_mode)
        
        # Create call parameters
        call_data = {
            "To": to_number,
            "From": self.from_number,
            "Url": swml_url,
            "Method": "POST",
            "StatusCallback": f"{settings.public_url}/api/webhooks/call-status",
            "StatusCallbackMethod": "POST",
            "StatusCallbackEvent": ["initiated", "ringing", "answered", "completed"]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/Accounts/{self.project_id}/Calls.json",
                    headers=self.headers,
                    data=call_data
                )
                
                if response.status_code != 201:
                    logger.error(f"SignalWire API error: {response.status_code} - {response.text}")
                    raise Exception(f"Failed to place call: {response.status_code}")
                
                call_info = response.json()
                logger.info(f"Call initiated successfully: {call_info['sid']}")
                
                return {
                    "signalwire_call_id": call_info["sid"],
                    "status": call_info["status"],
                    "from": call_info["from"],
                    "to": call_info["to"],
                    "direction": call_info["direction"],
                    "date_created": call_info["date_created"]
                }
                
        except Exception as e:
            logger.error(f"Error placing call: {str(e)}")
            raise
            
    async def end_call(self, call_sid: str) -> bool:
        """End an active call"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/Accounts/{self.project_id}/Calls/{call_sid}.json",
                    headers=self.headers,
                    data={"Status": "completed"}
                )
                
                if response.status_code == 200:
                    logger.info(f"Call {call_sid} ended successfully")
                    return True
                else:
                    logger.error(f"Failed to end call: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error ending call: {str(e)}")
            return False
            
    async def _create_swml_bin(self, to_number: str, webhook_url: str, listening_mode: str) -> str:
        """Create a SWML bin for the call with live transcription"""
        
        # SWML configuration
        swml_config = {
            "version": "1.0.0",
            "sections": {
                "main": [
                    {
                        "record_call": {
                            "format": "mp3",
                            "stereo": True,
                            "direction": "both",
                            "beep": False,
                            "status_url": f"{settings.public_url}/api/webhooks/recording-status"
                        }
                    },
                    {
                        "live_transcribe": {
                            "transcribe_language": "en-US",
                            "webhook_url": webhook_url
                        }
                    },
                    {
                        "connect": {
                            "to": to_number,
                            "from": self.from_number,
                            "timeout": 30,
                            "answer_on_bridge": False,
                            "call_state_events": ["created", "ringing", "answered", "ended"],
                            "call_state_url": f"{settings.public_url}/api/webhooks/call-state"
                        }
                    }
                ]
            }
        }
        
        # Create SWML bin via SignalWire API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{self.space_url}/api/relay/rest/swml-bins",
                    headers=self.headers,
                    json={
                        "name": f"LiveCall-{to_number}-{listening_mode}",
                        "swml": swml_config,
                        "description": f"Live transcription call to {to_number}"
                    }
                )
                
                if response.status_code != 201:
                    logger.error(f"Failed to create SWML bin: {response.status_code} - {response.text}")
                    # Fallback to inline SWML URL
                    return f"{settings.public_url}/api/webhooks/swml"
                
                bin_data = response.json()
                return bin_data["url"]
                
        except Exception as e:
            logger.error(f"Error creating SWML bin: {str(e)}")
            # Fallback to inline SWML URL
            return f"{settings.public_url}/api/webhooks/swml"