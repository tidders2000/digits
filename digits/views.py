import json
import secrets
import string
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # we will not use csrf_exempt; use csrf token in JS
from .forms import InputNumberForm
from .models import Entry

SIGNER_SALT = 'digits-commit-salt'
SIGNATURE_MAX_AGE = 30  # seconds (token only valid for short time)



@login_required

def index(request):
    form = InputNumberForm()
    return render(request, 'digits/index.html', {"form": form})

def _generate_random_5digit():
    # Avoid leading zeros? If allowed, keep them. We'll allow leading zeros.
    return ''.join(secrets.choice(string.digits) for _ in range(5))



@login_required

def start_display(request):
    """Handles the POST from index: validates user input, generates a random number,
    returns a page showing the random number and a short-lived signed token for commit."""
    if request.method != 'POST':
        return redirect('digits:index')
    form = InputNumberForm(request.POST)
    test = request.POST.get('user_number')
    if not form.is_valid():
        return render(request, 'digits/index.html', {"form": form})
    user_number = test
  
    random_number = _generate_random_5digit()

    # Create a signed payload so the later commit cannot be forged
    payload = {"user_number": user_number, "random_number": random_number}
    signed = signing.dumps(payload, salt=SIGNER_SALT)

    # Render page that displays random_number and uses JS to POST to /commit/ after 10 seconds
    return render(request, 'digits/show_random.html', {
        "user_number": user_number,
        "payload" :payload,
        "random_number": random_number,
        "signed_payload": signed,
        "commit_url": reverse('digits:commit_entry'),
        "commit_delay_seconds": 10,
    })

@login_required

@require_POST
def commit_entry(request):
    """Called by client JS after the 10s display. Verifies signed token and age, stores entry and sends email."""
    signed_payload = request.POST.get('signed_payload')
    un= request.POST.get('user_number')

    if not signed_payload:
        return HttpResponseBadRequest("Missing token.")
    try:
        payload = signing.loads(signed_payload, salt=SIGNER_SALT, max_age=SIGNATURE_MAX_AGE)
      
    except signing.SignatureExpired:
        return HttpResponseForbidden("Token expired.")
    except signing.BadSignature:
        return HttpResponseForbidden("Invalid token.")

    user_number = payload.get('user_number')
    print(user_number)
    random_number = payload.get('random_number')
    print(random_number)
    # create security string inside model default or explicitly:
    entry = Entry.objects.create(
        user_number=user_number,
        random_number=random_number,
    )

    # Send email to fixed recipient
    # recipient = getattr(settings, 'FIXED_RECIPIENT_EMAIL', None)
    # if not recipient:
    #     # In production you'd log and maybe retry. For now, respond error.
    #     entry.delete()
    #     return JsonResponse({"status":"error", "message":"Recipient not configured."}, status=500)

    # subject = f"New 5-digit numbers stored (Entry {entry.id})"
    # message = f"User number: {user_number}\nRandom number: {random_number}\nSecurity string: {entry.security_string}\nEntry ID: {entry.id}\n"
    # send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL'), [recipient], fail_silently=False)

    return JsonResponse({"status":"ok", "entry_id": str(entry.id)})
@login_required

def entry_list(request):
    entries = Entry.objects.order_by('-created_at')[:50]
    return render(request, 'digits/list.html', {"entries": entries})
@login_required
def reveal_request(request, entry_id):
    """User requests to retrieve the stored random number -> we create a challenge (3 random positions) and store them."""
    entry = get_object_or_404(Entry, id=entry_id)
    if entry.revealed:
        # If already revealed, we can still show a page that asks for confirmation to delete or re-show
        return render(request, 'digits/reveal_already.html', {"entry": entry})

    # pick 3 unique positions from 1..40 (1-based)
    positions = sorted(secrets.choice(range(1, 41)) for _ in range(3))
    # ensure uniqueness: regenerate if duplicates (simple loop)
    while len(set(positions)) < 3:
        positions = sorted(secrets.choice(range(1, 41)) for _ in range(3))
    # store as comma-separated positions
    entry.challenge_indices = ",".join(str(p) for p in positions)
    entry.challenge_created_at = timezone.now()
    entry.save(update_fields=['challenge_indices', 'challenge_created_at'])

    return render(request, 'digits/reveal_challenge.html', {
        "entry": entry,
        "positions": positions  # show them in UI like "characters 2, 5, 10"
    })
@login_required
@require_POST
def verify_challenge(request, entry_id):
    """Verifies submitted characters match the security string at the requested positions."""
    entry = get_object_or_404(Entry, id=entry_id)
    if not entry.challenge_indices:
        return HttpResponseBadRequest("No challenge found. Request a reveal first.")
    # Optional: expire challenges after e.g. 10 minutes
    if entry.challenge_created_at and timezone.now() - entry.challenge_created_at > timedelta(minutes=10):
        entry.challenge_indices = ""
        entry.challenge_created_at = None
        entry.save(update_fields=['challenge_indices', 'challenge_created_at'])
        return HttpResponseForbidden("Challenge expired. Please request reveal again.")

    positions = [int(x) for x in entry.challenge_indices.split(",")]
    # Expect POST fields char1, char2, char3
    chars = [request.POST.get(f'char{i}', '') for i in range(1,4)]
    if any(len(c) != 1 for c in chars):
        return HttpResponseBadRequest("Each input must be a single character.")

    # Build expected characters (positions are 1-based)
    expected = []
    sec = entry.security_string
    for pos in positions:
        # positions beyond length: fail
        if pos < 1 or pos > len(sec):
            return HttpResponseBadRequest("Invalid challenge positions.")
        expected.append(sec[pos-1])

    # Compare exactly (case-sensitive). You can adjust to .lower() if desired.
    if chars == expected:
        entry.revealed = True
        entry.save(update_fields=['revealed'])
        # Show both numbers and offer deletion
        return render(request, 'digits/reveal_result.html', {"entry": entry})
    else:
        return render(request, 'digits/reveal_challenge.html', {
            "entry": entry,
            "positions": positions,
            "error": "Characters did not match. Try again."
        })
@login_required
@require_POST
def delete_entry(request, entry_id):
    entry = get_object_or_404(Entry, id=entry_id)
    # In production you'd require extra confirmation/auth; here we just delete if exists
    entry.delete()
    return redirect('digits:entry_list')
