from django.contrib import admin
from .models import Profile
from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Profile

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio']
    readonly_fields = ['profile_picture_preview']
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return mark_safe(f'<img src="{obj.profile_picture.url}" width="150" />')
        return "No picture uploaded"
    
    profile_picture_preview.short_description = 'Profile Picture Preview'

# Make sure this line appears only ONCE in your file
admin.site.register(Profile, ProfileAdmin)
