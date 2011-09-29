class MailChimpBaseException(Exception):
    pass

class MailChimpError(MailChimpBaseException):
    """ Represents an error returned from the MailChimp API. """
    def __init__(self, message, code):
        MailChimpBaseException.__init__(self, message)
        self.code = code

class MailChimpGroupingNotFound(MailChimpBaseException):
    """ A specified grouping name was not found in the mailchimp list. """
    pass
    
class MailChimpEmailNotFound(MailChimpBaseException):
    """ A specified email address was not found in the mailchimp list. """
    pass

class MailChimpEmailUnsubscribed(MailChimpBaseException):
    pass
    

