from django.contrib import admin
from models import UserSubscription, PendingUserSubscription

class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'status', 'optin_time', 'optin_ip',)
    search_fields = ['user__email']
    list_filter = ('status',)
    actions = ['sync', 'subscribe', 'force_subscribe', 'unsubscribe', 'delete_member']
    # TODO: use confirmation views
    def user_email(self, model):
        return model.user.email
    
    def delete_member(self, request, queryset):
        for model in queryset:
            model.unsubscribe(delete_member=True, send_goodbye=False, 
                              send_notify=False)
            
    def force_subscribe(self, request, queryset):
        for model in queryset:
            model.subscribe(double_optin=False)
            
    def sync(self, request, queryset):
        for model in queryset:
            model.sync()
            
    def subscribe(self, request, queryset):
        for model in queryset:
            model.subscribe()
    
    def subscribe(self, request, queryset):
        for model in queryset:
            model.subscribe()
   
    def unsubscribe(self, request, queryset):
        for model in queryset:
            model.unsubscribe()

admin.site.register(UserSubscription, UserSubscriptionAdmin)
admin.site.register(PendingUserSubscription)
