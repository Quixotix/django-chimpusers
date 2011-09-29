from datetime import datetime
from django.utils import unittest
from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.conf import settings
from django.forms.widgets import RadioSelect, Select, CheckboxInput
from mailsnake import MailSnake
from chimpusers.utils import get_list_id
from chimpusers.models import UserSubscription, PendingUserSubscription
from chimpusers.exceptions import MailChimpError
from chimpusers.forms import groups_form_factory

def get_admin_user():
    """ 
    Gets the first user defined in ADMINS
    """
    admins = getattr(settings, 'ADMINS', (('Micah Carrick', 'micah@quixotix.com'),))
    name = admins[0][0].split(" ", 1)
    user = User(username="admin", first_name=name[0], last_name=name[1], 
                     email=admins[0][1])
    user.save()
    return user

def delete_member(user):
    """ Completely delete the member from MailChimp's list. """
    subscription = UserSubscription.objects.get(user=user)
    try:
        subscription.unsubscribe(delete_member=True, 
                                 send_goodbye=False, 
                                 send_notify=False)
    except MailChimpError:
        pass
    
class PendingUserSubscriptionTestCase(TestCase):
    """ Test case for the PendingUserSubscription model. """  
    def test_pending_user_subscription(self):
        ms = MailSnake(settings.MAILCHIMP_API_KEY)
        user = get_admin_user()
        subscription = UserSubscription.objects.get(user=user)
        delete_member(user)
        ms.listInterestGroupingAdd(id=get_list_id(), 
                                   name="Test Interest Group",
                                   type="checkboxes",
                                   groups=["Option 1", "Option 2"])
                                            
        # when a user signs up...
        pending, c = PendingUserSubscription.objects.get_or_create(user=user)
        optin_ip = getattr(settings, 'MAILCHIMP_TEST_IP', '184.106.168.48')
        optin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        pending.merge_vars = {
            'OPTIN_IP': optin_ip,
            'OPTIN_TIME': optin_time,
        }
        pending.save()
        
        # when the user is activated, confirmed, etc.
        pending.subscribe(double_optin=False)
        subscription.sync()
        self.assertEqual(optin_ip, subscription.optin_ip)
        self.assertEqual(optin_time, subscription.optin_time)
        self.assertTrue(subscription.is_subscribed())
        pending.delete()
        
class UserSubscriptionTestCase(TestCase):
    """ Test case for the UserSubscription model. """                                   
    def setUp(self):
        self.user = get_admin_user()
        self.subscription = UserSubscription.objects.get(user=self.user)
        delete_member(self.user)
            
    def tearDown(self):
        delete_member(self.user)
        self.user.delete()
 
    def test_optin_proof(self):
        """ Test that OPTIN_TIME and OPTIN_IP gets set properly """
        subscription = self.subscription
        optin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        optin_ip = getattr(settings, 'MAILCHIMP_TEST_IP', '184.106.168.48')
        merge = {'OPTIN_TIME': optin_time, 'OPTIN_IP': optin_ip}
        subscription.subscribe(merge_vars=merge, double_optin=False)
        self.assertEqual(subscription.optin_time, optin_time)
        self.assertEqual(subscription.optin_ip, optin_ip)
        subscription.sync()
        self.assertEqual(subscription.optin_time, optin_time)
        self.assertEqual(subscription.optin_ip, optin_ip) 
        
    def test_subscriptions(self):
        """ Test basic subscribe/update/unsubscribe functionality. """
        subscription = self.subscription
        self.assertEqual(subscription.status, UserSubscription.UNKNOWN)
        
        # subscribe
        r = subscription.subscribe(double_optin=False)
        self.assertTrue(r)
        self.assertEqual(subscription.status, UserSubscription.SUBSCRIBED)
        subscription.sync()
        self.assertEqual(subscription.status, UserSubscription.SUBSCRIBED)

        # update
        subscription.update(email_type="text")
        data = subscription.sync()
        self.assertEqual(data['email_type'], "text")
        
        # unsubscribe
        r = subscription.unsubscribe(send_goodbye=False, send_notify=False)
        self.assertTrue(r)
        self.assertEqual(subscription.status, UserSubscription.UNSUBSCRIBED)
        subscription.sync()
        self.assertEqual(subscription.status, UserSubscription.UNSUBSCRIBED)
        
        # double opt-in subscribe
        r = subscription.subscribe()
        self.assertTrue(r)
        self.assertEqual(subscription.status, UserSubscription.PENDING)
        subscription.sync()
        self.assertEqual(subscription.status, UserSubscription.PENDING)


class FormsTestCase(TestCase):
    """ Test case for the form factory. """
    @classmethod
    def setUpClass(cls):
        # create test groups
        cls.ms = MailSnake(settings.MAILCHIMP_API_KEY)
        cls.list_id = get_list_id()
        cls.checkboxes_name = "Test Checkboxes"
        r = cls.ms.listInterestGroupingAdd(id=cls.list_id, 
                                            name=cls.checkboxes_name,
                                            type="checkboxes",
                                            groups=["Option 1", "Option 2"])
        cls.checkboxes_id = r
        
        cls.radio_name = "Test Radio"
        r = cls.ms.listInterestGroupingAdd(id=cls.list_id, 
                                            name=cls.radio_name,
                                            type="radio",
                                            groups=["Option 1", "Option 2"])
        cls.radio_id = r
        
        cls.select_name = "Test Select"
        r = cls.ms.listInterestGroupingAdd(id=cls.list_id, 
                                            name=cls.select_name,
                                            type="dropdown",
                                            groups=["Option 1", "Option 2"])
        cls.select_id = r
    
    @classmethod
    def tearDownClass(cls):
        # remove test groups
        cls.ms.listInterestGroupingDel(grouping_id=cls.checkboxes_id)
        cls.ms.listInterestGroupingDel(grouping_id=cls.radio_id)
        cls.ms.listInterestGroupingDel(grouping_id=cls.select_id)
        
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def test_form_factory_default(self):
        """ Test calling form factory without arguments. """
        # Can't be sure what "first" group is. Just make sure it instantiates.
        GroupsForm = groups_form_factory()
        form = GroupsForm()

    def test_form_factory_for_user(self):
        """ Test the form factory for a given user. """
        self.user = get_admin_user()
        self.subscription = UserSubscription.objects.get(user=self.user)
        merge = {'GROUPINGS':[{'name':self.checkboxes_name, 
                               'groups':'Option 1,Option 2'}]}
        r = self.subscription.subscribe(double_optin=False, 
                                        update_existing=True,
                                        merge_vars=merge)
        GroupsForm = groups_form_factory(self.user.email, self.checkboxes_name)
        form = GroupsForm()
        post = {}
        for field in form:
            post[field.name] = True
            self.assertIn('checked="checked"', str(field), 
                          "Should be checked initially for this user.")
        form = GroupsForm(post)
        self.assertTrue(form.is_valid())
        self.assertIn("Option 1", form.selected_groups)
        self.assertIn("Option 2", form.selected_groups)
        
    def test_form_factory_widgets(self):
        """ Test widgets generated by the form factory. """
        GroupsForm = groups_form_factory(grouping_name=self.checkboxes_name)
        form = GroupsForm()
        for field in form:
            self.assertTrue(isinstance(field.field.widget, CheckboxInput), 
                            "Field should be represented by a checkbox.")
        
        GroupsForm = groups_form_factory(grouping_name=self.radio_name)
        form = GroupsForm()
        for field in form:
            self.assertTrue(isinstance(field.field.widget, RadioSelect), 
                            "Field should be represented by a radio option.")
        
        GroupsForm = groups_form_factory(grouping_name=self.select_name)
        form = GroupsForm()
        for field in form:
            self.assertTrue(isinstance(field.field.widget, Select), 
                            "Field should be represented by a select box.")
            
        
        
        
        
