from django.contrib import admin
from plag.models import Order, ProtectedResource, Invoice, ScanResult, ScanLog, Query, UserPreference, RecentBlogPosts, UserProfile

admin.site.register(UserProfile)
admin.site.register(Order)
admin.site.register(ProtectedResource)
admin.site.register(Invoice)
admin.site.register(ScanResult)
admin.site.register(ScanLog)
admin.site.register(Query)
admin.site.register(UserPreference)
admin.site.register(RecentBlogPosts)