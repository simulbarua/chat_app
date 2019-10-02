import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async

from .models import Thread, ChatMessage


class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print("connected", event)
        # # To accept Websocket Connection
        # await self.send({
        #     "type": "websocket.accept"
        # })
        # # To send message to websocket
        # await self.send({
        #     "type": "websocket.send",
        #     "text": "Hello World"
        # })
        # await asyncio.sleep(10)
        # # To close websocket connection
        # await self.send({
        #     "type": "websocket.close"
        # })

        other_user = self.scope['url_route']['kwargs']['username']
        me = self.scope['user']
        thread_obj = await self.get_thread(me, other_user)
        self.thread_obj = thread_obj
        chat_room = f"thread_{thread_obj.id}"
        self.chat_room = chat_room
        await self.channel_layer.group_add(
            chat_room, self.channel_name
        )

        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_receive(self, event):
        # When message is received from the websocket
        print("received", event)
        front_text = event.get('text', None)
        if front_text is not None:
            loaded_dict_data = json.loads(front_text)
            msg = loaded_dict_data.get('message')
            user = self.scope['user']
            await self.create_chat_message(user, msg)
            myResponse = {
                'message': msg,
                'username': user.username
            }
            # new_event = {
            #     "type": "websocket.send",
            #     "text": json.dumps(myResponse)
            # }
            # Broadcasts the message event to be sent
            await self.channel_layer.group_send(
                self.chat_room,
                {
                    "type": "chat_message",
                    "text": json.dumps(myResponse)
                }
            )

    async def chat_message(self, event):
        # Send The Actual Message
        await self.send({
            "type": "websocket.send",
            "text": event['text']
        })

    async def websocket_disconnect(self, event):
        # when the socket disconnect
        print("disconnected", event)
        await self.channel_layer.group_discard(
            self.chat_room, self.channel_name
        )

    @database_sync_to_async
    def get_thread(self, user, other_username):
        return Thread.objects.get_or_new(user, other_username)[0]

    @database_sync_to_async
    def create_chat_message(self, me, message):
        thread_obj = self.thread_obj
        return ChatMessage.objects.create(thread=thread_obj, user=me, message=message)


class NotificationConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        user = self.scope['user']
        self.group_name = f"ntf_{user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_disconnect(self, event):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def notification_send(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event['text']})
