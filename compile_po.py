import os
import polib

# Compile Swahili
po = polib.pofile('locale/sw/LC_MESSAGES/django.po')
po.save_as_mofile('locale/sw/LC_MESSAGES/django.mo')
print("Compiled Swahili")

# Compile French
po = polib.pofile('locale/fr/LC_MESSAGES/django.po')
po.save_as_mofile('locale/fr/LC_MESSAGES/django.mo')
print("Compiled French")