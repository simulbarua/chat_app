from django.db import models

from django.conf import settings
from django.db import models
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json


class ThreadManager(models.Manager):
    def by_user(self, user):
        qlookup = Q(first=user) | Q(second=user)
        qlookup2 = Q(first=user) & Q(second=user)
        qs = self.get_queryset().filter(qlookup).exclude(qlookup2).distinct()
        return qs

    def get_or_new(self, user, other_username):  # get_or_create
        username = user.username
        if username == other_username:
            return None
        qlookup1 = Q(first__username=username) & Q(
            second__username=other_username)
        qlookup2 = Q(first__username=other_username) & Q(
            second__username=username)
        qs = self.get_queryset().filter(qlookup1 | qlookup2).distinct()
        if qs.count() == 1:
            return qs.first(), False
        elif qs.count() > 1:
            return qs.order_by('timestamp').first(), False
        else:
            Klass = user.__class__
            user2 = Klass.objects.get(username=other_username)
            if user != user2:
                obj = self.model(
                    first=user,
                    second=user2
                )
                obj.save()
                return obj, True
            return None, False


class Thread(models.Model):
    first = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_thread_first')
    second = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_thread_second')
    updated = models.DateTimeField(auto_now=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = ThreadManager()

    @property
    def room_group_name(self):
        return f'chat_{self.id}'

    def broadcast(self, msg=None):
        if msg is not None:
            broadcast_msg_to_chat(
                msg, group_name=self.room_group_name, user='admin')
            return True
        return False


class ChatMessage(models.Model):
    thread = models.ForeignKey(
        Thread, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name='sender', on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, **kwargs):
        channel_layer = get_channel_layer()
        if self.user == self.thread.first:
            other = self.thread.second
        else:
            other = self.thread.first
        group = f"ntf_{other.id}"
        ntf_msg = {
            "message": "You received a message from",
            "username": self.user.username
        }
        async_to_sync(channel_layer.group_send)(
            group, {"type": "notification.send",
                    "text": json.dumps(ntf_msg)
                    }
        )

    # async def chat_message(self, event):
    #     # Send The Actual Message
    #     await self.send({
    #         "type": "websocket.send",
    #         "text": event['text']
    #     })
