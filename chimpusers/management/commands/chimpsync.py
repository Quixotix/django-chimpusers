from mailsnake import MailSnake
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from chimpusers.models import UserSubscription

# TODO: command line args and verbosity

class Command(BaseCommand):
    help = 'Syncs every user\'s subscription status with the MailChimp API'
    
    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)
        for user in users:
            subscription, created = UserSubscription.objects.get_or_create(user=user)
            subscription.sync(True)
            self.stdout.write("%s\t\t%s\n" % (user.email, 
                                            subscription.get_status_display()))
        
