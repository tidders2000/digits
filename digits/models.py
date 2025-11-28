import uuid
import secrets
import string
from django.db import models

def make_security_string(length=20):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class Entry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_number = models.CharField(max_length=5)     # user-supplied 5-digit
    random_number = models.CharField(max_length=5)   # system-generated 5-digit
    security_string = models.CharField(max_length=40, default='abcdefghijklmnopqrstabcdefghijklmnopqrst')
    created_at = models.DateTimeField(auto_now_add=True)
    revealed = models.BooleanField(default=False)    # whether the reveal flow has happened
    # store challenge indices as comma separated "1,5,9" (1-based positions)
    challenge_indices = models.CharField(max_length=32, blank=True)
    challenge_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Entry {self.id} ({self.created_at})"
