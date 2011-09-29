from django.conf import settings
from chimpusers.exceptions import MailChimpError

def get_list_id():
    """
    Get MAILCHIMP_LIST_ID ID as defined in the configuration settings.
    """
    if not hasattr(settings, 'MAILCHIMP_LIST_ID'):
        errstr = _("You need to specify MAILCHIMP_LIST_ID in your " \
                   "Django settings file.")
        raise ImproperlyConfigured(errstr)                               
    return settings.MAILCHIMP_LIST_ID

def raise_if_error(response):
        """
        Raises a MailChimpError exception if an error message is found in the 
        response from the API.
        """
        try:
            if 'code' in response:
                raise MailChimpError(response['error'], response['code'])
        except TypeError:
            pass
        
