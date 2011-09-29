import logging
from datetime import datetime
from mailsnake import MailSnake
from chimpusers.utils import get_list_id, raise_if_error
from chimpusers.exceptions import *
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.forms.widgets import RadioSelect, Select

  
class _GroupsForm(forms.BaseForm):
    """
    A dynamically-generated form based on the interest groups for a given 
    MailChimp list. Use groups_form_factory() to create a the form class.
    """
    def clean(self):
        """
        Creates two properties useful to the view:
        
        Sets the 'selected_groups' property to a list of the names of the 
        selected groups.
    
        Sets the 'merge_var' property to a dict representation of the selected
        groups prepared for passing to the 'GROUPINGS' merge var for the 
        MailChimp API. Eg.
        
            {'name':'My Grouping Name', 'groups':'Option One, Option Two'}
        """
        if self._grouping['form_field'] == 'checkboxes':
            self.selected_groups = self._get_checkboxes_groups()
        else:
            self.selected_groups = [self._get_choices_group()]
        escaped = [group.replace(',','\,') for group in self.selected_groups]
        group_string = ",".join(escaped)
        self.merge_var = {'name':self._grouping['name'], 'groups':group_string} 
        
        return super(_GroupsForm, self).clean()
    
    def _get_choices_group(self):
        """ Return the selected group as a string. """
        if 'mailchimp_group' in self.cleaned_data:
            selected_value = self.cleaned_data['mailchimp_group']
            for value, choice in self.fields['mailchimp_group'].choices:
                if value == selected_value:
                    return choice
    
    def _get_checkboxes_groups(self):
        """ Return list of checked groups. """
        groups = []
        for key, value in self.cleaned_data.items():
            if value:
                #logging.debug("%s = %s" % (key, value))
                for field in self:
                    if field.name == key:
                        groups.append(field.label)
        return groups
        
def groups_form_factory(email=None, grouping_name=None, list_id=None):
    """
    Form factory for selecting the interest groups.
    
    email           An email address of a list member from which to set the
                    initial values for the form.
    grouping_name   The grouping name as defined in MailChimp. If not provided
                    then the first grouping will be used.
    list_id         The MailChimp list ID. If not provided, the value defined in 
                    the config settings will be used.
    """
    if not hasattr(settings, 'MAILCHIMP_API_KEY'):
        raise ImproperlyConfigured(_("You need to specify MAILCHIMP_API_KEY" \
                                     "in your Django settings file."))                               
    ms = MailSnake(settings.MAILCHIMP_API_KEY)
    
    if not list_id:
        list_id = get_list_id()
        
    # get all groupings for the list
    grouping = None
    response = ms.listInterestGroupings(id=list_id)
    raise_if_error(response)
    
    # get the correct grouping
    if not grouping_name:
        grouping = response[0]
        grouping_name = grouping['name']
    else:
        for try_grouping in response:
            if try_grouping['name'] == grouping_name:
                grouping = try_grouping
    if not grouping:
        errmsg = _("Grouping not found: '%s'") % grouping_name
        raise MailChimpGroupingNotFound(errmsg)
    

    if email:
        # get the user's group subscription to set initial field values
        response = ms.listMemberInfo(id=list_id, email_address=[email])
        if not response['success']:
            raise MailChimpEmailNotFound
        user_groupings = response['data'][0]['merges']['GROUPINGS']
        for try_grouping in user_groupings:
            if try_grouping['name'] == grouping_name:
                user_grouping = try_grouping   
    
    # create the appropriate type of fields
    if grouping['form_field'] == 'checkboxes':
        fields = SortedDict()
        for i, group in enumerate(grouping['groups']):
            key = 'mailchimp_group_'+group['bit']
            if email:
                initial=bool(user_grouping['groups'].find(group['name'])+1)
            else:
                initial=False
            fields.insert(i, key, forms.BooleanField(label=group['name'], 
                                                     required=False, 
                                                     initial=initial))
    else: # radio or select
        fields = {}
        CHOICES = tuple((group['bit'], group['name']) for group in grouping['groups'])
        for group in grouping['groups']:
            initial=None
            if email:
                if bool(user_grouping['groups'].find(group['name'])+1):
                    initial = group['bit']
            else:
                initial = None
        if grouping['form_field'] == 'radio': 
            widget = RadioSelect
        else:
            widget = Select
        fields['mailchimp_group'] = forms.ChoiceField(choices=CHOICES, 
                                                      label=grouping['name'], 
                                                      widget=widget, 
                                                      initial=initial)
    
    form = type('GroupsForm', (_GroupsForm,), {'base_fields': fields})
    form._grouping = grouping

    return form

