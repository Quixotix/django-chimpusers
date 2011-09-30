django-chimpusers
=================

Integrates users from Django's authentication system `django.contrib.auth` with
a [MailChimp][1] email marketing list. Provides a model to store opt-in data 
and a form factory to allow users to edit their [interest groups][3].


Requirements
------------

* [MailSnake][10], a Python wrapper for the [MailChimp v1.3 API][2]. You can
  install MailSnake using `git`:

        git clone https://github.com/leftium/mailsnake.git
        python setup.py install

* The API key for your MailChimp account. [Where can I find my API key?][4]
* The ID of the list you want to integrate with. [How can I find my List ID?][5]


Installation
------------

As this app is still under development, the best installation method is to clone
the git repository. 

    git clone git@github.com:Quixotix/django-chimpusers.git
    setup.py install django-chimpusers

Then, add `chimpusers` to your installed apps and sync the database:

    ./manage.py syncdb


Settings
--------

* `MAILCHIMP_API_KEY` - [required] Your MailChimp API key. 
* `MAILCHIMP_LIST_ID` - [required] The list ID of the MailChimp list you want to integrate
  with.
* `MAILCHIMP_TEST_IP` - [optional] A __public__ IP address to use with the test cases. This 
  must be a public IP for the tests to pass.


How it Works
------------

### The UserSubscription Model

A `UserSubscription` model is created each time a `User` is created. This model 
simply provides some convenience methods that wrap MailSnake calls to the 
MailChimp API. It also stores the user's subscription status, opt-in IP addresss, 
and opt-in date.

You would typically use `UserSubscription` when you register or activate new
members or in a specific view for subscribing to your email list. (You make
sure your users are opting in right? They should be physically checking a check 
box, clicking a big "subscribe" button, etc. Don't spam folks, they don't like
it)

__UserSubscription.subscribe()__

The `UserSubscription.subscribe()` calls [listSubscribe][6], automatically 
adding the list ID, the user's email, the user's first name, and the user's 
last name. All other parameters defined for [listSubscribe][6] can be passed 
to `UserSubscription.subscribe()` as keyword arguments (again, it just wraps
MailSnake).

    from chimpusers.models import UserSubscription
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    subscription.subscribe() # double_optin is True by default

If the MailChimp API returns an error (say the email is already subscribed), you
can catch the `MailChimpError` eception.

    from chimpusers.models import UserSubscription
    from chimpusers.exceptions import MailChimpError
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    try:
        subscription.subscribe() # double_optin is True by default
    except MailChimpError as e:
        # Handle exception. Message will be that returned by MailChimp.
        pass

When you subscribe a user you should save the user's IP address and a timestamp 
as opt-in "proof".

    from datetime import datetime
    from chimpusers.models import UserSubscription
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    optin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if 'HTTP_X_FORWARDED_FOR' in request.META: # IP forwarded from proxy
        optin_ip = request.META['HTTP_X_FORWARDED_FOR']
    else:
        optin_ip = request.META['REMOTE_ADDR']
    merge_vars = {'OPTIN_IP': optin_ip, 'OPTIN_TIME': optin_time}
    
    subscription.subscribe(merge_vars=merge_vars)

And just to drive home the point that the `UserSubscription.subscribe()` just
wraps a MailSnake call to [listSubscribe][6]...

    from chimpusers.models import UserSubscription
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    subscription.subscribe(email_type="text", 
                           double_optin=False, 
                           update_existing=True, 
                           replace_interests=False, 
                           send_welcome=True)


__UserSubscription.update()__

The `UserSubscription.update()` calls [listMemberUpdate][7], automatically 
adding the list ID, the user's email, the user's first name, and the user's 
last name. All other parameters defined for [listMemberUpdate][7] can be passed 
to `UserSubscription.update()` as keyword arguments.

    from chimpusers.models import UserSubscription
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    merge_vars = {"GROUPINGS": [{"name":"Interest Groups", 
                                 "groups":"Monthly Newsletter,New Products"}]}
    subscription.update(merge_vars=merge_vars)


__UserSubscription.unsubscribe()__

The `UserSubscription.unsubscribe()` calls [listUnsubscribe][8], automatically 
adding the list ID and the user's email. All other parameters defined for 
[listUnsubscribe][8] can be passed to `UserSubscription.unsubscribe()` as 
keyword arguments.

    from chimpusers.models import UserSubscription
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    subscription.unsubscribe(send_goodbye=False, send_notify=True)


__UserSubscription.sync()__
    
The `UserSubscription` model provides the `sync` method to synchronize the model
fields with the MailChimp API. Since the user or an administrator can manipulate
subscriptions from the MailChimp website and you _may_ not have any [webhooks][9]
setup yet, syncing the `UserSubscription` can come in handy.

    from chimpusers.models import UserSubscription
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    subscription.sync()
    # the following fields are now in sync with MailChimp
    # subscription.status
    # subscription.optin_ip
    # subscription.optin_time


### The groups_form_factory Form Factory

One of the great features of MailChimp is to segregate your list into various
interest [groups][3]. This allows you to maintain one list for your website's 
users and allow them to sign up for one or more groups. 

For example, an e-commerce website may have a list of all their customers, and
groups to allow their customers to recieve a monthly newsletter, another group
for new product announcements, and another group for holiday promotions.

The `groups_form_factory()` function dynamically generates a form for opting in
and out of your list's groups. This could be used in a view allowing existing
subscribers to modify their group preferences or combined with a registration
form to allow new subscribers to opt-in to specific groups at sign up.

    from chimpusers.models import UserSubscription
    from chimpusers.forms import groups_form_factory
    from datetime import datetime
    
    # ...
    
    subscription = UserSubscription.objects.get(user=request.user)
    GroupsForm = groups_form_factory(request.user.email)
    
    if request.method == 'POST':
        form = GroupsForm(request.post)
        if form.is_valid():
            merge_vars = {'GROUPINGS': [form.merge_var]}
            if subscription.is_subscribed():
                # update user's groups
                subscription.update(merge_vars=merge)
            else:
                # subscribe
                optin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if 'HTTP_X_FORWARDED_FOR' in request.META:
                    optin_ip = request.META['HTTP_X_FORWARDED_FOR']
                else:
                    optin_ip = request.META['REMOTE_ADDR']
                merge['OPTIN_IP'] = optin_ip
                merge['OPTIN_TIME'] = optin_time
                subscription.subscribe(merge_vars=merge)
    else:
        form = GroupsForm()
    
    # ...
    

[1]: http://mailchimp.com
[2]: http://apidocs.mailchimp.com/api/1.3/
[3]: http://mailchimp.com/features/groups/
[4]: http://kb.mailchimp.com/article/where-can-i-find-my-api-key/
[5]: http://kb.mailchimp.com/article/how-can-i-find-my-list-id/
[6]: http://apidocs.mailchimp.com/api/1.3/listsubscribe.func.php
[7]: http://apidocs.mailchimp.com/api/1.3/listupdatemember.func.php
[8]: http://apidocs.mailchimp.com/api/1.3/listunsubscribe.func.php
[9]: http://apidocs.mailchimp.com/webhooks/
[10]: https://github.com/leftium/mailsnake
