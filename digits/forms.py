from django import forms

class InputNumberForm(forms.Form):
    user_number = forms.CharField(max_length=5, min_length=5, strip=True,
                                  widget=forms.TextInput(attrs={"placeholder":"5 digits"}))

    def clean_user_number(self):
        v = self.cleaned_data['user_number']
        if not v.isdigit() or len(v) != 5:
            raise forms.ValidationError("Enter exactly 5 digits (0-9).")
