from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile
from .models import Organization

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['bio', 'profile_picture', 'role']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile', 'followers_count', 'following_count']
    
    def get_followers_count(self, obj):
        return obj.followers.count()
    
    def get_following_count(self, obj):
        return obj.profile.following.count()

class UserRegisterSerializer(serializers.ModelSerializer):
    password_confirmation = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirmation', 'profile_picture']
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate(self, data):
        if data['password'] != data.pop('password_confirmation'):
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        profile_picture = None
        if 'profile_picture' in validated_data:
            profile_picture = validated_data.pop('profile_picture')
            
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        if profile_picture:
            user.profile.profile_picture = profile_picture
            user.profile.save()
            
        return user


class OrganizationSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = ['id', 'name', 'description', 'created_at', 'created_by', 'members_count']
        read_only_fields = ['created_by', 'created_at']
    
    def get_members_count(self, obj):
        return obj.members.count()
