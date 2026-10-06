import os

from fastapi import HTTPException
from livekit import api

class LiveKitManager:
    def __init__(self):
        self.url = os.getenv("LIVEKIT_URL")
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")

    def get_room_token(self, 
                       room_name: str, 
                       participant_identity: str, 
                       participant_name: str, 
                       participant_metadata: str = None, 
                       participant_attributes: dict = None, 
                       room_config: dict = None
    ):
        try:
            if not all([self.api_key, self.api_secret, self.url]):
                raise HTTPException(
                    status_code=500,
                    detail='Server configuration error'
                )

            if not all([room_name, participant_identity, participant_name]):
                raise HTTPException(
                    status_code=400,
                    detail='Missing required parameters'
                )
       
            room_token = (
                api.AccessToken(self.api_key, self.api_secret)
                .with_identity(participant_identity)
                .with_name(participant_name)
                .with_grants(api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=False,
                    can_publish_sources=["microphone"],
                ))
            )

            if participant_metadata:
                room_token = room_token.with_metadata(participant_metadata)
            if participant_attributes:
                room_token = room_token.with_attributes(participant_attributes)
            if room_config:
                room_token = room_token.with_room_config(room_config)

            participant_token = room_token.to_jwt()

            return participant_token
        
        except Exception as e:
            print(f'Token generation error: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail='Failed to generate token'
            )
