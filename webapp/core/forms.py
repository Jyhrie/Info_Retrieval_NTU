from django import forms


class TextForm(forms.Form):
    text = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={"placeholder": "Enter text..."})
    )
