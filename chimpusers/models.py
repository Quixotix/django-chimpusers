import logging
from mailsnake import MailSnake
from chimpusers.exceptions import MailChimpError
from chimpusers.utils import get_list_id, raise_if_error
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver
from django.db.models.signals import post_save
try:
    import cPickle as pickle
except:
    import pickle
import base64

class UserSubscription(models.Model):
    """
    Stores a user's MailChimp subscription status and provides some wrappers
    around the MailSnake API calls to subscribe, update, and unsubscribe the
    user.
    """
    UNKNOWN = 0
    NOT_SUBSCRIBED = 1
    UNSUBSCRIBED = 2
    SUBSCRIBED = 3
    PENDING = 4
    CLEANED = 5
    CHOICES = (
        (UNKNOWN, 'Unknown'),
        (NOT_SUBSCRIBED, 'Not Subscribed'),
        (UNSUBSCRIBED, 'Unsubscribed'), 
        (SUBSCRIBED, 'Subscribed'),
        (PENDING, 'Pending'),
        (CLEANED, 'Cleaned')
    )
    user = models.OneToOneField(User)
    status = models.PositiveIntegerField(choices=CHOICES, default=UNKNOWN)
    optin_time = models.DateTimeField(null=True, blank=True)
    optin_ip = models.IPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'mailchimp_user_subscription'
        
    def sync(self, save=True):
        """ 
        Populate the model fields from the values returned from the MailChimp  
        listMemberInfo API call for this user and list. 
        
        If 'save' is True, the save() method will be called on this
        UserSubscription instance.
        
        Returns the 'data' portion of the API response on success. Raises 
        MailChimpError if the API returned an error.
        
        See: http://apidocs.mailchimp.com/api/1.3/listmemberinfo.func.php
        """
        kwargs = {'email_address': self.user.email, 'id': get_list_id()}
        response = self.get_mailsnake_instance().listMemberInfo(**kwargs)
        if not response['success']:
            self.status = self.NOT_SUBSCRIBED
            self.optin_time = None
            self.optin_ip = None
            data = None
        else:
            data = response['data'][0]
            
            if data['status'] == 'unsubscribed':
                self.status = self.UNSUBSCRIBED
            elif data['status'] == 'pending':
                self.status = self.PENDING
            elif data['status'] == 'cleaned':
                self.status = self.CLEANED
            elif data['status'] == 'subscribed':
                self.status = self.SUBSCRIBED
            else: 
                self.status = self.UNKNOWN
            
            if data['ip_opt']:
                self.optin_ip = data['ip_opt']
            if data['timestamp']:
                self.optin_time = data['timestamp']
        
        if save:
            self.save()
        
        return data
    
    def get_mailsnake_instance(self):
        """
        Get the instance of the mailsnake.MailSnake class based on
        MAILCHIMP_API_KEY defined in the configuration settings.
        """
        try:
            return self._ms
        except AttributeError:
            if not hasattr(settings, 'MAILCHIMP_API_KEY'):
                errstr = _("You need to specify MAILCHIMP_LIST_ID in your " \
                           "Django settings file.")
                raise ImproperlyConfigured(errstr)                              
            self._ms = MailSnake(settings.MAILCHIMP_API_KEY)
            return self._ms
    
    def is_subscribed(self):
        """ Convenience to determine if user is subscribed. """
        if self.status == self.SUBSCRIBED:
            return True
        return False
        
    def subscribe(self, **kwargs):
        """ 
        Wraps the listSubscribe API call for this user and list. See
        http://apidocs.mailchimp.com/api/1.3/listsubscribe.func.php for a list
        of keyword arguments. 
        
        The following arguments will be passed to listSubscribe() automatically
        and should not be provided by the caller:
        
            id
            email_address
            FNAME (in merge_vars)
            LNAME (in merge_vars)
            
        Returns True if the user was subscribed, False if the user was not
        subscribed, or raises a MailChimpError if the API returned an error.
        """
        kwargs['email_address'] = self.user.email
        kwargs['id'] = get_list_id()
        if not 'merge_vars' in kwargs:
            kwargs['merge_vars'] = {}
        kwargs['merge_vars']['FNAME'] = self.user.first_name
        kwargs['merge_vars']['LNAME'] = self.user.last_name
        
        response = self.get_mailsnake_instance().listSubscribe(**kwargs)
        raise_if_error(response)
        if response:
            if 'merge_vars' in kwargs:
                merge_vars = kwargs['merge_vars']
                if 'OPTIN_IP' in merge_vars:
                    self.optin_ip = merge_vars['OPTIN_IP']
                if 'OPTIN_TIME' in merge_vars:
                    self.optin_time = merge_vars['OPTIN_TIME']
            if 'double_optin' in kwargs and not kwargs['double_optin']:
                self.status = self.SUBSCRIBED
            else:
                self.status = self.PENDING
            self.save()
            
        return response

    def update(self, **kwargs):
        """ 
        Wraps the listUpdateMember API call for this user and list. See
        http://apidocs.mailchimp.com/api/1.3/listupdatemember.func.php for a 
        list of keyword arguments.
        
        The following arguments will be passed to listUnsubscribe()
        automatically and should not be provided by the caller.
        
            id
            email_address
            FNAME (in merge_vars)
            LNAME (in merge_vars)
            
        Returns True if the user was udpated, False if the user was not
        unsubscribed, or raises a MailChimpError if the API returned an error.
        """
        kwargs['email_address'] = self.user.email
        kwargs['id'] = get_list_id()
        if not 'merge_vars' in kwargs:
            kwargs['merge_vars'] = {}
        kwargs['merge_vars']['FNAME'] = self.user.first_name
        kwargs['merge_vars']['LNAME'] = self.user.last_name
        
        response = self.get_mailsnake_instance().listUpdateMember(**kwargs)
        raise_if_error(response)
        
        return response
    
    def unsubscribe(self, **kwargs):
        """ 
        Wraps the listUnsubscribe API call for this user and list. See
        http://apidocs.mailchimp.com/api/1.3/listunsubscribe.func.php for a list
        of keyword arguments.
        
        The following arguments will be passed to listUnsubscribe()
        automatically and should not be provided by the caller.
        
            id
            email_address
            
        Returns True if the user was unsubscribed, False if the user was not
        unsubscribed, or raises a MailChimpError if the API returned an error.
        """
        kwargs['email_address'] = self.user.email
        kwargs['id'] = get_list_id()
        response = self.get_mailsnake_instance().listUnsubscribe(**kwargs)
        raise_if_error(response)
        if response:
            if 'delete_member' in kwargs and kwargs['delete_member']:
                self.status = self.NOT_SUBSCRIBED
            else:
                self.status = self.UNSUBSCRIBED
            self.save()
        return response
    
    def __unicode__(self):
        return self.user.email


# http://justcramer.com/2008/08/08/custom-fields-in-django/
class SerializedDataField(models.TextField):
    """Because Django for some reason feels its needed to repeatedly call
    to_python even after it's been converted this does not support strings."""
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if value is None: return
        if not isinstance(value, basestring): return value
        value = pickle.loads(base64.b64decode(value))
        return value

    def get_db_prep_save(self, value, connection=None):
        if value is None: return
        return base64.b64encode(pickle.dumps(value))
        
        
class PendingUserSubscription(models.Model):
    """
    Can be used as temporary storage for a user's subscription while the user is
    pending internal (not MailChimp) activation or confirmaion.
    """
    user = models.OneToOneField(User)
    merge_vars = SerializedDataField(null=True, blank=True)
    
    class Meta:
        db_table = 'mailchimp_pending_user_subscription'

    def subscribe(self, **kwargs):
        """ Send the subscription to the MailChimp API. """
        subscription, c = UserSubscription.objects.get_or_create(user=self.user)
        if self.merge_vars:
            kwargs['merge_vars'] = self.merge_vars
        subscription.subscribe(**kwargs)
        
    def __unicode__(self):
        return self.user.email
        
@receiver(post_save, sender=User)
def user_save_handler(sender, **kwargs):
    """ 
    Create a UserSubscription object when a new User object is created.
    """
    user = kwargs['instance']
    if kwargs['created']:
        UserSubscription(user=user).save()
    
