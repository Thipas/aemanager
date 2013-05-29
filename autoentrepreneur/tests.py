from django.test import TestCase
from django.contrib.auth.models import User
from autoentrepreneur.models import Subscription, SUBSCRIPTION_STATE_NOT_PAID, \
    SUBSCRIPTION_STATE_TRIAL, SUBSCRIPTION_STATE_PAID, SUBSCRIPTION_STATE_FREE, \
    UserProfile, AUTOENTREPRENEUR_PROFESSIONAL_CATEGORY_TRADER, \
    AUTOENTREPRENEUR_PROFESSIONAL_CATEGORY_CRAFTSMAN, \
    AUTOENTREPRENEUR_PROFESSIONAL_CATEGORY_LIBERAL, SalesLimit
from django.db.utils import IntegrityError
from contact.models import Contact, Address, CONTACT_TYPE_COMPANY
from project.models import Project, PROJECT_STATE_PROSPECT, Proposal, \
    PROPOSAL_STATE_DRAFT, ROW_CATEGORY_SERVICE, ProposalRow
from accounts.models import Invoice, INVOICE_STATE_PAID, PAYMENT_TYPE_CHECK, \
    InvoiceRow, Expense
from bugtracker.models import ISSUE_CATEGORY_BUG, ISSUE_STATE_OPEN, Issue, \
    Comment, Vote
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib.sites.models import Site
from django.utils.translation import ugettext
from django.conf import settings
from django.core.management import call_command
import datetime
from autoentrepreneur.models import AUTOENTREPRENEUR_PAYMENT_OPTION_QUATERLY, \
    AUTOENTREPRENEUR_PAYMENT_OPTION_MONTHLY, \
    AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC, \
    AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC, AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC, \
    AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
import datetimestub
import autoentrepreneur
from django.contrib.auth import authenticate
from registration.models import RegistrationProfile
from backup.models import mkdir_p
import os

class SubscriptionTest(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        settings.FREE_SUBSCRIPTION = False
        Subscription.objects.all().delete()
        today = datetime.date.today()

        limit_defined = SalesLimit.objects.filter(year=today.year).count()
        if not limit_defined:
            sale_limits = SalesLimit.objects.filter(year=2011)
            for sl in sale_limits:
                SalesLimit.objects.create(year=today.year,
                                          activity=sl.activity,
                                          limit=sl.limit,
                                          limit2=sl.limit2)

        # generate limit for next year
        sale_limits = SalesLimit.objects.filter(year=today.year)
        for sl in sale_limits:
            SalesLimit.objects.create(year=sl.year + 1,
                                      activity=sl.activity,
                                      limit=sl.limit,
                                      limit2=sl.limit2)

    def testNotAllowedIfNoSubscription(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        self.assertFalse(profile.is_allowed())

    def testNotAllowedIfSubscriptionNotPaid(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_NOT_PAID,
                                    expiration_date=datetime.date.today() - datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertFalse(profile.is_allowed())

    def testNotAllowedIfSubscriptionNotPaidWithFutureDate(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_NOT_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertFalse(profile.is_allowed())

    def testNotAllowedIfTrialFinished(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=datetime.date.today() - datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertFalse(profile.is_allowed())

    def testNotAllowedIfPaidFinished(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() - datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertFalse(profile.is_allowed())

    def testAllowedIfPaidNotFinished(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() - datetime.timedelta(1),
                                    transaction_id='XXX')
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(1),
                                    transaction_id='XXY')
        self.assertTrue(profile.is_allowed())

    def testAllowedIfTrialNotFinished(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=datetime.date.today() + datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertTrue(profile.is_allowed())

    def testAllowedIfFreeAccount(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_FREE,
                                    expiration_date=datetime.date.today() + datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertTrue(profile.is_allowed())

    def testAllowedIfFreeAccountWithFinishedDate(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_FREE,
                                    expiration_date=datetime.date.today() - datetime.timedelta(1),
                                    transaction_id='XXX')

        self.assertTrue(profile.is_allowed())

    def testNextDateBeforeExpiration(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        expiration_date = datetime.date.today() + datetime.timedelta(10)
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=expiration_date,
                                    transaction_id='XXX')

        next_date = profile.get_next_expiration_date()
        try:
            computed_next_date = datetime.date(expiration_date.year + 1, expiration_date.month, expiration_date.day)
        except:
            # case of February 29th
            computed_next_date = datetime.date(expiration_date.year + 1, 3, 1)
        self.assertEquals(next_date, computed_next_date)

    def testNextDateAfterExpiration(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=datetime.date.today() - datetime.timedelta(10),
                                    transaction_id='XXX')

        expiration_date = datetime.date.today()
        try:
            computed_next_date = datetime.date(expiration_date.year + 1, expiration_date.month, expiration_date.day)
        except:
            # case of February 29th
            computed_next_date = datetime.date(expiration_date.year + 1, 3, 1)
        next_date = profile.get_next_expiration_date()
        self.assertEquals(next_date, computed_next_date)

    def testNextDateWhenPaymentFails(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_NOT_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(365),
                                    transaction_id='XXX')

        expiration_date = datetime.date.today()
        try:
            computed_next_date = datetime.date(expiration_date.year + 1, expiration_date.month, expiration_date.day)
        except:
            # case of February 29th
            computed_next_date = datetime.date(expiration_date.year + 1, 3, 1)
        next_date = profile.get_next_expiration_date()
        self.assertEquals(next_date, computed_next_date)

    def testNextDateWhenPaymentFailsWithRunningSubscription(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        expiration_date = datetime.date.today() + datetime.timedelta(10)
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=expiration_date,
                                    transaction_id='XXX')

        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_NOT_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(375),
                                    transaction_id='XXY')

        next_date = profile.get_next_expiration_date()

        try:
            computed_next_date = datetime.date(expiration_date.year + 1, expiration_date.month, expiration_date.day)
        except:
            # case of February 29th
            computed_next_date = datetime.date(expiration_date.year + 1, 3, 1)
        self.assertEquals(next_date, computed_next_date)

    def testTransactionIdIsUnique(self):
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='XXX')

        s = Subscription(owner=user,
                         state=SUBSCRIPTION_STATE_NOT_PAID,
                         expiration_date=datetime.date.today() + datetime.timedelta(375),
                         transaction_id='XXX')

        self.assertRaises(IntegrityError, s.save)

    def testBug62(self):
        """
        When several subscriptions are valid, is_allowed returns false
        """
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_TRIAL,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='XXX')

        Subscription.objects.create(owner=user,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(375),
                                    transaction_id='XXY')

        self.assertTrue(profile.is_allowed())

    def testExpirationAlertForTrial(self):
        self.client.login(username='test', password='test')
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        sub = Subscription.objects.create(owner=user,
                                          state=SUBSCRIPTION_STATE_TRIAL,
                                          expiration_date=datetime.date.today() + datetime.timedelta(31),
                                          transaction_id='XXX')

        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'Your trial ends')
        self.assertNotContains(response, 'Your subscription ends')

        sub.expiration_date = datetime.date.today() + datetime.timedelta(30)
        sub.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, "Your trial ends in %(days)d days, if you want to keep using %(site_name)s don&#39;t forget to subscribe" % {'days': 30,
                                                                                                                                                   'site_name': Site.objects.get_current().name})
        sub.expiration_date = datetime.date.today() + datetime.timedelta(1)
        sub.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, "Your trial ends in %(days)d days, if you want to keep using %(site_name)s don&#39;t forget to subscribe" % {'days': 1,
                                                                                                                                                   'site_name': Site.objects.get_current().name})
        sub.expiration_date = datetime.date.today() + datetime.timedelta(0)
        sub.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, "Your trial ends in %(days)d days, if you want to keep using %(site_name)s don&#39;t forget to subscribe" % {'days': 0,
                                                                                                                                                   'site_name': Site.objects.get_current().name})

    def testExpirationAlertForPaid(self):
        self.client.login(username='test', password='test')
        user = User.objects.get(pk=1)
        profile = user.get_profile()
        sub = Subscription.objects.create(owner=user,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(31),
                                          transaction_id='XXX')

        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'Your trial ends')
        self.assertNotContains(response, 'Your subscription ends')

        sub.expiration_date = datetime.date.today() + datetime.timedelta(30)
        sub.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, "Your subscription ends in %(days)d days, if you want to keep using %(site_name)s don&#39;t forget to renew it" % {'days': 30,
                                                                                                                                                         'site_name': Site.objects.get_current().name})
        sub.expiration_date = datetime.date.today() + datetime.timedelta(1)
        sub.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, "Your subscription ends in %(days)d days, if you want to keep using %(site_name)s don&#39;t forget to renew it" % {'days': 1,
                                                                                                                                                         'site_name': Site.objects.get_current().name})
        sub.expiration_date = datetime.date.today() + datetime.timedelta(0)
        sub.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, "Your subscription ends in %(days)d days, if you want to keep using %(site_name)s don&#39;t forget to renew it" % {'days': 0,
                                                                                                                                                         'site_name': Site.objects.get_current().name})

    def testExpirationEmailAlert(self):
        # trial with more than 7 days remaining (no alert)
        user1 = User.objects.get(pk=1)
        sub = Subscription.objects.create(owner=user1,
                                          state=SUBSCRIPTION_STATE_TRIAL,
                                          expiration_date=datetime.date.today() + datetime.timedelta(8),
                                          transaction_id='XX1')

        # trial with 7 days remaining (alert)
        user2 = User.objects.get(pk=2)
        sub = Subscription.objects.create(owner=user2,
                                          state=SUBSCRIPTION_STATE_TRIAL,
                                          expiration_date=datetime.date.today() + datetime.timedelta(7),
                                          transaction_id='XX2')

        # trial with 6 days remaining (no alert)
        user3 = User.objects.create_user('user3', 'user3@example.com', 'test')
        user3.first_name = 'User 3'
        user3.last_name = 'User 3'
        user3.save()
        sub = Subscription.objects.get(owner=user3)
        sub.expiration_date = datetime.date.today() + datetime.timedelta(6)
        sub.save()

        # trial with 2 days remaining (no alert)
        user4 = User.objects.create_user('user4', 'user3@example.com', 'test')
        user4.first_name = 'User 4'
        user4.last_name = 'User 4'
        user4.save()
        sub = Subscription.objects.get(owner=user4)
        sub.expiration_date = datetime.date.today() + datetime.timedelta(2)
        sub.save()

        # trial with 1 day remaining (alert)
        user5 = User.objects.create_user('user5', 'user5@example.com', 'test')
        user5.first_name = 'User 5'
        user5.last_name = 'User 5'
        user5.save()
        sub = Subscription.objects.get(owner=user5)
        sub.expiration_date = datetime.date.today() + datetime.timedelta(1)
        sub.save()
        user51 = User.objects.create_user('user51', 'user51@example.com', 'test')
        user51.first_name = 'User 51'
        user51.last_name = 'User 51'
        user51.save()
        sub = Subscription.objects.get(owner=user51)
        sub.expiration_date = datetime.date.today() + datetime.timedelta(1)
        sub.save()

        # trial with 0 days remaining (no alert)
        user6 = User.objects.create_user('user6', 'user6@example.com', 'test')
        user6.first_name = 'User 6'
        user6.last_name = 'User 6'
        user6.save()
        sub = Subscription.objects.get(owner=user6)
        sub.expiration_date = datetime.date.today()
        sub.save()

        # trial expired for 1 day (no alert)
        user7 = User.objects.create_user('user7', 'user7@example.com', 'test')
        user7.first_name = 'User 7'
        user7.last_name = 'User 7'
        user7.save()
        sub = Subscription.objects.get(owner=user7)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(1)
        sub.save()

        # paid with more than 7 days remaining (no alert)
        user8 = User.objects.create_user('user8', 'user8@example.com', 'test')
        user8.first_name = 'User 8'
        user8.last_name = 'User 8'
        user8.save()
        sub = Subscription.objects.get(owner=user8)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user8,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(8),
                                          transaction_id='XX8')

        # paid with 7 days remaining (alert)
        user9 = User.objects.create_user('user9', 'user9@example.com', 'test')
        user9.first_name = 'User 9'
        user9.last_name = 'User 9'
        user9.save()
        sub = Subscription.objects.get(owner=user9)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user9,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(7),
                                          transaction_id='XX9')

        # paid with 6 days remaining (no alert)
        user10 = User.objects.create_user('user10', 'user10@example.com', 'test')
        user10.first_name = 'User 10'
        user10.last_name = 'User 10'
        user10.save()
        sub = Subscription.objects.get(owner=user10)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user10,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(6),
                                          transaction_id='XX10')

        # paid with 2 days remaining (no alert)
        user11 = User.objects.create_user('user11', 'user11@example.com', 'test')
        user11.first_name = 'User 11'
        user11.last_name = 'User 11'
        user11.save()
        sub = Subscription.objects.get(owner=user11)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user11,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(2),
                                          transaction_id='XX11')

        # paid with 1 day remaining (alert)
        user12 = User.objects.create_user('user12', 'user12@example.com', 'test')
        user12.first_name = 'User 12'
        user12.last_name = 'User 12'
        user12.save()
        sub = Subscription.objects.get(owner=user12)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user12,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(1),
                                          transaction_id='XX12')
        user121 = User.objects.create_user('user121', 'user121@example.com', 'test')
        user121.first_name = 'User 121'
        user121.last_name = 'User 121'
        user121.save()
        sub = Subscription.objects.get(owner=user121)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user121,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(1),
                                          transaction_id='XX121')

        # paid with 0 day remaining (no alert)
        user13 = User.objects.create_user('user13', 'user13@example.com', 'test')
        user13.first_name = 'User 13'
        user13.last_name = 'User 13'
        user13.save()
        sub = Subscription.objects.get(owner=user13)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user13,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today(),
                                          transaction_id='XX13')

        # paid expired (no alert)
        user14 = User.objects.create_user('user14', 'user14@example.com', 'test')
        user14.first_name = 'User 14'
        user14.last_name = 'User 14'
        user14.save()
        sub = Subscription.objects.get(owner=user14)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        sub = Subscription.objects.create(owner=user14,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() - datetime.timedelta(1),
                                          transaction_id='XX14')

        # trial with 1 day remaining and paid not expiring subscription (no alert)
        user15 = User.objects.create_user('user15', 'user15@example.com', 'test')
        user15.first_name = 'User 15'
        user15.last_name = 'User 15'
        user15.save()
        sub = Subscription.objects.get(owner=user15)
        sub.expiration_date = datetime.date.today() + datetime.timedelta(1)
        sub.save()
        sub = Subscription.objects.create(owner=user15,
                                          state=SUBSCRIPTION_STATE_PAID,
                                          expiration_date=datetime.date.today() + datetime.timedelta(30),
                                          transaction_id='XX15')

        call_command('alert_expiring_subscription')

        self.assertEquals(len(mail.outbox), 6)
        self.assertEquals(mail.outbox[0].subject, u"Votre p\xe9riode d'essai \xe0 %(site)s expire dans %(days)d jours" % {'site': Site.objects.get_current().name,
                                                                                                                         'days': 7})
        self.assertEquals(mail.outbox[0].to, ['%s %s <%s>' % (user2.first_name, user2.last_name, user2.email)])
        self.assertEquals(mail.outbox[0].body, u"""Votre p\xe9riode d'essai expire dans %(days)d jours.

Pass\xe9 ce d\xe9lai, vous ne pourrez plus acc\xe9der \xe0 l'application \xe0 moins de vous abonner en vous rendant sur https://%(site)s%(subscribe_url)s.

Si vous ne souhaitez plus utiliser l'application, vous pouvez vous d\xe9sinscrire sur cette m\xeame page, vos donn\xe9es seront alors supprim\xe9es dans les 7 jours. Si vous laissez votre compte en l'\xe9tat, vous pourrez \xe0 tout moment souscrire un abonnement et y acc\xe9der \xe0 nouveau. Cependant, si vous ne souscrivez pas d'abonnement, votre compte sera supprim\xe9 d\xe9finitivement au bout d'un an.

L'\xe9quipe %(site_name)s""" % {'site': Site.objects.get_current(),
                                'site_name': Site.objects.get_current().name,
                                'days': 7,
                                'subscribe_url': reverse('subscribe')})

        self.assertEquals(mail.outbox[1].subject, u"Votre p\xe9riode d'essai \xe0 %(site)s expire dans %(days)d jour" % {'site': Site.objects.get_current().name,
                                                                                                                         'days': 1})
        self.assertEquals(mail.outbox[1].to, ['%s %s <%s>' % (user51.first_name, user51.last_name, user51.email)])
        self.assertEquals(mail.outbox[1].body, u"""Votre p\xe9riode d'essai expire dans %(days)d jour.

Pass\xe9 ce d\xe9lai, vous ne pourrez plus acc\xe9der \xe0 l'application \xe0 moins de vous abonner en vous rendant sur https://%(site)s%(subscribe_url)s.

Si vous ne souhaitez plus utiliser l'application, vous pouvez vous d\xe9sinscrire sur cette m\xeame page, vos donn\xe9es seront alors supprim\xe9es dans les 7 jours. Si vous laissez votre compte en l'\xe9tat, vous pourrez \xe0 tout moment souscrire un abonnement et y acc\xe9der \xe0 nouveau. Cependant, si vous ne souscrivez pas d'abonnement, votre compte sera supprim\xe9 d\xe9finitivement au bout d'un an.

L'\xe9quipe %(site_name)s""" % {'site': Site.objects.get_current(),
                                'site_name': Site.objects.get_current().name,
                                'days': 1,
                                'subscribe_url': reverse('subscribe')})

        self.assertEquals(mail.outbox[2].subject, u"Votre p\xe9riode d'essai \xe0 %(site)s expire dans %(days)d jour" % {'site': Site.objects.get_current().name,
                                                                                                                         'days': 1})
        self.assertEquals(mail.outbox[2].to, ['%s %s <%s>' % (user5.first_name, user5.last_name, user5.email)])
        self.assertEquals(mail.outbox[2].body, u"""Votre p\xe9riode d'essai expire dans %(days)d jour.

Pass\xe9 ce d\xe9lai, vous ne pourrez plus acc\xe9der \xe0 l'application \xe0 moins de vous abonner en vous rendant sur https://%(site)s%(subscribe_url)s.

Si vous ne souhaitez plus utiliser l'application, vous pouvez vous d\xe9sinscrire sur cette m\xeame page, vos donn\xe9es seront alors supprim\xe9es dans les 7 jours. Si vous laissez votre compte en l'\xe9tat, vous pourrez \xe0 tout moment souscrire un abonnement et y acc\xe9der \xe0 nouveau. Cependant, si vous ne souscrivez pas d'abonnement, votre compte sera supprim\xe9 d\xe9finitivement au bout d'un an.

L'\xe9quipe %(site_name)s""" % {'site': Site.objects.get_current(),
                                'site_name': Site.objects.get_current().name,
                                'days': 1,
                                'subscribe_url': reverse('subscribe')})

        self.assertEquals(mail.outbox[3].subject, u"Votre abonnement \xe0 %(site)s expire dans %(days)d jours" % {'site': Site.objects.get_current().name,
                                                                                                                         'days': 7})
        self.assertEquals(mail.outbox[3].to, ['%s %s <%s>' % (user9.first_name, user9.last_name, user9.email)])
        self.assertEquals(mail.outbox[3].body, u"""Votre abonnement expire dans %(days)d jours.

Pass\xe9 ce d\xe9lai, vous ne pourrez plus acc\xe9der \xe0 l'application \xe0 moins de vous abonner en vous rendant sur https://%(site)s%(subscribe_url)s.

Si vous ne souhaitez plus utiliser l'application, vous pouvez vous d\xe9sinscrire sur cette m\xeame page, vos donn\xe9es seront alors supprim\xe9es dans les 7 jours. Si vous laissez votre compte en l'\xe9tat, vous pourrez \xe0 tout moment souscrire un abonnement et y acc\xe9der \xe0 nouveau. Cependant, si vous ne souscrivez pas d'abonnement, votre compte sera supprim\xe9 d\xe9finitivement au bout d'un an.

L'\xe9quipe %(site_name)s""" % {'site': Site.objects.get_current(),
                                'site_name': Site.objects.get_current().name,
                                'days': 7,
                                'subscribe_url': reverse('subscribe')})

        self.assertEquals(mail.outbox[5].subject, u"Votre abonnement \xe0 %(site)s expire dans %(days)d jour" % {'site': Site.objects.get_current().name,
                                                                                                                         'days': 1})
        self.assertEquals(mail.outbox[5].to, ['%s %s <%s>' % (user12.first_name, user12.last_name, user12.email)])
        self.assertEquals(mail.outbox[5].body, u"""Votre abonnement expire dans %(days)d jour.

Pass\xe9 ce d\xe9lai, vous ne pourrez plus acc\xe9der \xe0 l'application \xe0 moins de vous abonner en vous rendant sur https://%(site)s%(subscribe_url)s.

Si vous ne souhaitez plus utiliser l'application, vous pouvez vous d\xe9sinscrire sur cette m\xeame page, vos donn\xe9es seront alors supprim\xe9es dans les 7 jours. Si vous laissez votre compte en l'\xe9tat, vous pourrez \xe0 tout moment souscrire un abonnement et y acc\xe9der \xe0 nouveau. Cependant, si vous ne souscrivez pas d'abonnement, votre compte sera supprim\xe9 d\xe9finitivement au bout d'un an.

L'\xe9quipe %(site_name)s""" % {'site': Site.objects.get_current(),
                                'site_name': Site.objects.get_current().name,
                                'days': 1,
                                'subscribe_url': reverse('subscribe')})

        self.assertEquals(mail.outbox[4].subject, u"Votre abonnement \xe0 %(site)s expire dans %(days)d jour" % {'site': Site.objects.get_current().name,
                                                                                                                         'days': 1})
        self.assertEquals(mail.outbox[4].to, ['%s %s <%s>' % (user121.first_name, user121.last_name, user121.email)])
        self.assertEquals(mail.outbox[4].body, u"""Votre abonnement expire dans %(days)d jour.

Pass\xe9 ce d\xe9lai, vous ne pourrez plus acc\xe9der \xe0 l'application \xe0 moins de vous abonner en vous rendant sur https://%(site)s%(subscribe_url)s.

Si vous ne souhaitez plus utiliser l'application, vous pouvez vous d\xe9sinscrire sur cette m\xeame page, vos donn\xe9es seront alors supprim\xe9es dans les 7 jours. Si vous laissez votre compte en l'\xe9tat, vous pourrez \xe0 tout moment souscrire un abonnement et y acc\xe9der \xe0 nouveau. Cependant, si vous ne souscrivez pas d'abonnement, votre compte sera supprim\xe9 d\xe9finitivement au bout d'un an.

L'\xe9quipe %(site_name)s""" % {'site': Site.objects.get_current(),
                                'site_name': Site.objects.get_current().name,
                                'days': 1,
                                'subscribe_url': reverse('subscribe')})

    def testAddDays(self):
        sub1 = Subscription.objects.create(owner_id=1,
                                           state=SUBSCRIPTION_STATE_TRIAL,
                                           expiration_date=datetime.date.today() + datetime.timedelta(3),
                                           transaction_id='XX1')
        sub2 = Subscription.objects.create(owner_id=2,
                                           state=SUBSCRIPTION_STATE_PAID,
                                           expiration_date=datetime.date.today() + datetime.timedelta(8),
                                           transaction_id='XX2')

        call_command('add_days_to_subscriptions', 3)

        self.assertEquals(Subscription.objects.get(pk=sub1.id).expiration_date,
                          datetime.date.today() + datetime.timedelta(6))
        self.assertEquals(Subscription.objects.get(pk=sub2.id).expiration_date,
                          datetime.date.today() + datetime.timedelta(11))

    def testDoNotAddDaysToExpired(self):
        sub1 = Subscription.objects.create(owner_id=1,
                                           state=SUBSCRIPTION_STATE_TRIAL,
                                           expiration_date=datetime.date.today() - datetime.timedelta(3),
                                           transaction_id='XX1')
        sub2 = Subscription.objects.create(owner_id=2,
                                           state=SUBSCRIPTION_STATE_PAID,
                                           expiration_date=datetime.date.today() + datetime.timedelta(8),
                                           transaction_id='XX2')

        call_command('add_days_to_subscriptions', 3)

        self.assertEquals(Subscription.objects.get(pk=sub1.id).expiration_date,
                          datetime.date.today() - datetime.timedelta(3))
        self.assertEquals(Subscription.objects.get(pk=sub2.id).expiration_date,
                          datetime.date.today() + datetime.timedelta(11))

    def testAddDaysToSubscriptionFollowingExpired(self):
        sub1 = Subscription.objects.create(owner_id=1,
                                           state=SUBSCRIPTION_STATE_TRIAL,
                                           expiration_date=datetime.date.today() - datetime.timedelta(3),
                                           transaction_id='XX1')
        sub1bis = Subscription.objects.create(owner_id=1,
                                              state=SUBSCRIPTION_STATE_PAID,
                                              expiration_date=datetime.date.today() + datetime.timedelta(3),
                                              transaction_id='XX1bis')
        sub2 = Subscription.objects.create(owner_id=2,
                                           state=SUBSCRIPTION_STATE_PAID,
                                           expiration_date=datetime.date.today() + datetime.timedelta(8),
                                           transaction_id='XX2')

        call_command('add_days_to_subscriptions', 3)

        self.assertEquals(Subscription.objects.get(pk=sub1.id).expiration_date,
                          datetime.date.today() - datetime.timedelta(3))
        self.assertEquals(Subscription.objects.get(pk=sub1bis.id).expiration_date,
                          datetime.date.today() + datetime.timedelta(6))
        self.assertEquals(Subscription.objects.get(pk=sub2.id).expiration_date,
                          datetime.date.today() + datetime.timedelta(11))


class UnregisterTest(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        self.client.login(username='test', password='test')

    def testUnregister(self):
        address = Address.objects.create(street='',
                                         zipcode='',
                                         city='',
                                         country_id=7,
                                         owner_id=1)
        contact = Contact.objects.create(contact_type=CONTACT_TYPE_COMPANY,
                                         name='Contact name',
                                         firstname='',
                                         function='',
                                         company_id='',
                                         legal_form='',
                                         representative='',
                                         representative_function='',
                                         email='',
                                         address=address,
                                         owner_id=1)
        project = Project.objects.create(name='Project test',
                                         customer=contact,
                                         state=PROJECT_STATE_PROSPECT,
                                         owner_id=1)
        proposal = Proposal.objects.create(project=project,
                                           update_date=datetime.date.today(),
                                           state=PROPOSAL_STATE_DRAFT,
                                           begin_date=datetime.date(2010, 8, 1),
                                           end_date=datetime.date(2010, 8, 15),
                                           contract_content='Content of contract',
                                           amount=2005,
                                           owner_id=1)
        proposal_row = ProposalRow.objects.create(proposal=proposal,
                                                  label='Day of work',
                                                  category=ROW_CATEGORY_SERVICE,
                                                  quantity=20,
                                                  unit_price='200.5',
                                                  owner_id=1)
        invoice = Invoice.objects.create(customer=contact,
                                         invoice_id=1,
                                         state=INVOICE_STATE_PAID,
                                         amount='100',
                                         edition_date=datetime.date(2010, 8, 31),
                                         payment_date=datetime.date(2010, 9, 30),
                                         paid_date=None,
                                         payment_type=PAYMENT_TYPE_CHECK,
                                         execution_begin_date=datetime.date(2010, 8, 1),
                                         execution_end_date=datetime.date(2010, 8, 7),
                                         penalty_date=datetime.date(2010, 10, 8),
                                         penalty_rate='1.5',
                                         discount_conditions='Nothing',
                                         owner_id=1)

        invoice_row = InvoiceRow.objects.create(proposal=proposal,
                                                invoice=invoice,
                                                label='Day of work',
                                                category=ROW_CATEGORY_SERVICE,
                                                quantity=10,
                                                unit_price='10',
                                                balance_payments=False,
                                                owner_id=1)
        expense = Expense.objects.create(date=datetime.date(2010, 1, 1),
                                         reference='ABCD',
                                         amount='100.0',
                                         payment_type=PAYMENT_TYPE_CHECK,
                                         description='First expense',
                                         owner_id=1)
        issue = Issue.objects.create(owner_id=1,
                                     category=ISSUE_CATEGORY_BUG,
                                     subject='test',
                                     message='test',
                                     update_date=datetime.datetime.now(),
                                     state=ISSUE_STATE_OPEN)
        comment = Comment.objects.create(owner_id=1,
                                         message='comment',
                                         update_date=datetime.datetime.now(),
                                         issue=issue)
        vote = Vote.objects.create(issue=issue,
                                   owner_id=1)

        mkdir_p('%s%s' % (settings.FILE_UPLOAD_DIR, UserProfile.objects.get(pk=1).uuid))
        user_uuid = UserProfile.objects.get(pk=1).uuid
        self.assertTrue(os.path.exists('%s%s' % (settings.FILE_UPLOAD_DIR, user_uuid)))

        response = self.client.get(reverse('unregister'))
        self.assertEquals(response.status_code, 200)

        response = self.client.post(reverse('unregister'),
                                    {'unregister': 'ok'})
        self.assertEquals(response.status_code, 302)

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, ugettext("You've just unregistered from %(site)s") % {'site': Site.objects.get_current()})
        self.assertEquals(mail.outbox[0].to, ['test@example.com'])
        self.assertFalse(User.objects.get(pk=1).is_active)
        self.assertTrue(UserProfile.objects.get(pk=1).unregister_datetime is not None)

        call_command('delete_unregistered_users')

        self.assertEquals(User.objects.filter(pk=1).count(), 1)
        self.assertEquals(UserProfile.objects.filter(pk=1).count(), 1)

        profile = UserProfile.objects.get(pk=1)
        profile.unregister_datetime = profile.unregister_datetime - datetime.timedelta(settings.ACCOUNT_UNREGISTER_DAYS)
        profile.save()

        call_command('delete_unregistered_users')

        self.assertEquals(Address.objects.count(), 1)
        self.assertEquals(Contact.objects.count(), 0)
        self.assertEquals(Project.objects.count(), 0)
        self.assertEquals(Proposal.objects.count(), 0)
        self.assertEquals(ProposalRow.objects.count(), 0)
        self.assertEquals(Invoice.objects.count(), 0)
        self.assertEquals(InvoiceRow.objects.count(), 0)
        self.assertEquals(Expense.objects.count(), 0)
        self.assertEquals(Issue.objects.count(), 1)
        self.assertEquals(Comment.objects.count(), 1)
        self.assertEquals(Vote.objects.count(), 0)
        self.assertEquals(Subscription.objects.filter(owner__id=1).count(), 0)
        self.assertEquals(User.objects.filter(pk=1).count(), 0)
        self.assertEquals(UserProfile.objects.filter(pk=1).count(), 0)
        self.assertFalse(os.path.exists('%s%s' % (settings.FILE_UPLOAD_DIR, user_uuid)))

    def testBug188cleanupregistration(self):
        """
        Cleanup registration provided by registration app is buggy
        and delete registered inactive users while it should not
        """
        registration_profile = RegistrationProfile.objects.create(user_id=1,
                                                                  activation_key=RegistrationProfile.ACTIVATED)

        response = self.client.post(reverse('unregister'),
                                    {'unregister': 'ok'})
        self.assertEquals(response.status_code, 302)

        call_command('cleanupregistration')

        self.assertEquals(User.objects.filter(pk=1).count(), 0)

    def testBug188cleanup_expired_registration(self):
        """
        Cleanup expired registration replace
        and delete registered inactive users while it should not
        """
        registration_profile = RegistrationProfile.objects.create(user_id=1,
                                                                  activation_key=RegistrationProfile.ACTIVATED)

        response = self.client.post(reverse('unregister'),
                                    {'unregister': 'ok'})
        self.assertEquals(response.status_code, 302)

        call_command('cleanup_expired_registration')

        self.assertEquals(User.objects.filter(pk=1).count(), 1)

        registration_profile.activation_key = '1234'
        registration_profile.save()
        user = registration_profile.user
        user.date_joined = datetime.date.today() - datetime.timedelta(settings.ACCOUNT_ACTIVATION_DAYS)
        user.save()
        profile = user.get_profile()
        profile.unregister_datetime = None
        profile.save()

        call_command('cleanup_expired_registration')

        self.assertEquals(User.objects.filter(pk=1).count(), 0)

    def testDeleteExpiredUsers(self):
        subscription = Subscription.objects.get(owner=1)
        mkdir_p('%s%s' % (settings.FILE_UPLOAD_DIR, UserProfile.objects.get(pk=1).uuid))
        user_uuid = UserProfile.objects.get(pk=1).uuid
        self.assertTrue(os.path.exists('%s%s' % (settings.FILE_UPLOAD_DIR, user_uuid)))

        # check it doesn't delete expired free account
        subscription.expiration_date = datetime.date.today() - datetime.timedelta(settings.ACCOUNT_EXPIRED_DAYS + 1)
        subscription.save()

        call_command('delete_expired_users')
        self.assertEquals(User.objects.count(), 2)

        # check it doesn't delete accounts not expired
        subscription.expiration_date = datetime.date.today() + datetime.timedelta(1)
        subscription.state = SUBSCRIPTION_STATE_PAID
        subscription.save()

        call_command('delete_expired_users')
        self.assertEquals(User.objects.count(), 2)

        # check it doesn't delete accounts expired for less than ACCOUNT_EXPIRED_DAYS
        subscription.expiration_date = datetime.date.today() - datetime.timedelta(settings.ACCOUNT_EXPIRED_DAYS - 1)
        subscription.save()

        call_command('delete_expired_users')
        self.assertEquals(User.objects.count(), 2)

        # check it deletes accounts expired for more than ACCOUNT_EXPIRED_DAYS
        subscription.expiration_date = datetime.date.today() - datetime.timedelta(settings.ACCOUNT_EXPIRED_DAYS)
        subscription.save()

        call_command('delete_expired_users')
        self.assertEquals(User.objects.count(), 1)
        self.assertFalse(os.path.exists('%s%s' % (settings.FILE_UPLOAD_DIR, user_uuid)))

class SubscriptionUserSelectTest(TestCase):

    def setUp(self):
        # user in trial period
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'test')
        self.user1.first_name = 'User 1'
        self.user1.last_name = 'User 1'
        self.user1.save()
        # user in trial but having paid to continue
        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'test')
        self.user2.first_name = 'User 2'
        self.user2.last_name = 'User 2'
        self.user2.save()
        Subscription.objects.create(owner=self.user2,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='paiduser2')
        # user after trial with paid subscription
        self.user3 = User.objects.create_user('user3', 'user3@example.com', 'test')
        self.user3.first_name = 'User 3'
        self.user3.last_name = 'User 3'
        self.user3.save()
        sub = Subscription.objects.get(owner=self.user3)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        Subscription.objects.create(owner=self.user3,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='paiduser3')
        # user with expired trial subscription
        self.user4 = User.objects.create_user('user4', 'user4@example.com', 'test')
        self.user4.first_name = 'User 4'
        self.user4.last_name = 'User 4'
        self.user4.save()
        sub = Subscription.objects.get(owner=self.user4)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        # user with expired paid subscription
        self.user5 = User.objects.create_user('user5', 'user5@example.com', 'test')
        self.user5.first_name = 'User 5'
        self.user5.last_name = 'User 5'
        self.user5.save()
        sub = Subscription.objects.get(owner=self.user5)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(20)
        sub.save()
        Subscription.objects.create(owner=self.user5,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() - datetime.timedelta(10),
                                    transaction_id='paiduser5')
        # user with free pass during trial
        self.user6 = User.objects.create_user('user6', 'user6@example.com', 'test')
        self.user6.first_name = 'User 6'
        self.user6.last_name = 'User 6'
        self.user6.save()
        Subscription.objects.create(owner=self.user6,
                                    state=SUBSCRIPTION_STATE_FREE,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='freeuser6')
        # user with free pass after trial
        self.user7 = User.objects.create_user('user7', 'user7@example.com', 'test')
        self.user7.first_name = 'User 7'
        self.user7.last_name = 'User 7'
        self.user7.save()
        sub = Subscription.objects.get(owner=self.user7)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(20)
        sub.save()
        Subscription.objects.create(owner=self.user7,
                                    state=SUBSCRIPTION_STATE_FREE,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='freeuser7')
        # unregistered user in trial
        self.user8 = User.objects.create_user('user8', 'user8@example.com', 'test')
        self.user8.first_name = 'User 8'
        self.user8.last_name = 'User 8'
        self.user8.is_active = False
        self.user8.save()
        profile = self.user8.get_profile()
        profile.unregister_datetime = datetime.datetime.now()
        profile.save()
        # unregistered user with paid subscription
        self.user9 = User.objects.create_user('user9', 'user9@example.com', 'test')
        self.user9.first_name = 'User 9'
        self.user9.last_name = 'User 9'
        self.user9.is_active = False
        self.user9.save()
        profile = self.user9.get_profile()
        profile.unregister_datetime = datetime.datetime.now()
        profile.save()
        sub = Subscription.objects.get(owner=self.user9)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()
        Subscription.objects.create(owner=self.user9,
                                    state=SUBSCRIPTION_STATE_PAID,
                                    expiration_date=datetime.date.today() + datetime.timedelta(10),
                                    transaction_id='paiduser9')
        # unregistered user with expired subscription
        self.user10 = User.objects.create_user('user10', 'user10@example.com', 'test')
        self.user10.first_name = 'User 10'
        self.user10.last_name = 'User 10'
        self.user10.is_active = False
        self.user10.save()
        profile = self.user10.get_profile()
        profile.unregister_datetime = datetime.datetime.now()
        profile.save()
        sub = Subscription.objects.get(owner=self.user10)
        sub.expiration_date = datetime.date.today() - datetime.timedelta(10)
        sub.save()

        # user with only free pass
        self.user11 = User.objects.create_user('user11', 'user11@example.com', 'test')
        self.user11.first_name = 'User 11'
        self.user11.last_name = 'User 11'
        self.user11.save()
        sub = Subscription.objects.get(owner=self.user11)
        sub.state = SUBSCRIPTION_STATE_FREE
        sub.save()

    def testTrialUser(self):
        users = Subscription.objects.get_users_with_trial_subscription()
        intented_user = {'owner__email':u'user1@example.com',
                          'owner__first_name':u'User 1',
                          'owner__last_name':u'User 1'}
        self.assertEquals(len(users), 1)
        self.assertEquals(users[0], intented_user)

    def testPaidUser(self):
        users = Subscription.objects.get_users_with_paid_subscription()
        intented_user1 = {'owner__email':u'user2@example.com',
                          'owner__first_name':u'User 2',
                          'owner__last_name':u'User 2'}
        intented_user2 = {'owner__email':u'user3@example.com',
                          'owner__first_name':u'User 3',
                          'owner__last_name':u'User 3'}
        self.assertEquals(len(users), 2)
        self.assertTrue(intented_user1 in users)
        self.assertTrue(intented_user2 in users)

    def testExpiredUser(self):
        users = Subscription.objects.get_users_with_expired_subscription()
        intended_user1 = {'owner__email':u'user4@example.com',
                          'owner__first_name':u'User 4',
                          'owner__last_name':u'User 4'}
        intended_user2 = {'owner__email':u'user5@example.com',
                          'owner__first_name':u'User 5',
                          'owner__last_name':u'User 5'}
        self.assertEquals(len(users), 2)
        self.assertTrue(intended_user1 in users)
        self.assertTrue(intended_user2 in users)

    def test137(self):
        """
        Test users list when a user has only one free subscription
        Think there may be a bug here because of assuming there is
        at least one trial subscription in a query
        """
        User.objects.all().exclude(username='user11').delete()
        self.assertEquals(len(User.objects.all()), 1)
        l1 = Subscription.objects.get_users_with_paid_subscription()
        l2 = Subscription.objects.get_users_with_trial_subscription()
        l3 = Subscription.objects.get_users_with_expired_subscription()
        self.assertEquals(len(l1), 0)
        self.assertEquals(len(l2), 0)
        self.assertEquals(len(l3), 0)

class TaxTest(TestCase):

    def setUp(self):
        autoentrepreneur.models.datetime = datetimestub.DatetimeStub()
        user = User.objects.create_user('test_user', 'test@example.com', 'test')
        self.user = authenticate(username='test_user', password='test')

    def tearDown(self):
        autoentrepreneur.models.datetime = datetime

    def testGetQuarter(self):
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 1, 1)), (1, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 2, 1)), (1, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 3, 1)), (1, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 4, 1)), (2, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 5, 1)), (2, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 6, 1)), (2, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 7, 1)), (3, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 8, 1)), (3, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 9, 1)), (3, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 10, 1)), (4, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 11, 1)), (4, 2011))
        self.assertEquals(self.user.get_profile().get_quarter(datetimestub.DatetimeStub.date(2011, 12, 1)), (4, 2011))

    def testPeriodQuaterlyFirstPayment(self):
        """
        Periodicite trimestrielle
        La premiere declaration trimestrielle porte sur la periode comprise
        entre le debut d'activite et la fin du trimestre civil qui suit.
        http://www.lautoentrepreneur.fr/questions_reponses.htm#Couts5
        """
        profile = self.user.get_profile()
        profile.payment_option = AUTOENTREPRENEUR_PAYMENT_OPTION_QUATERLY
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2011, 1, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2011, 1, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 6, 30))

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 12, 31)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 12, 31))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 3, 31))

        # first case of www.lautoentrepreneur.fr
        profile.creation_date = datetimestub.DatetimeStub.date(2010, 2, 1)
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 6, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 3
        autoentrepreneur.models.datetime.date.mock_day = 1
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 6, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 5
        autoentrepreneur.models.datetime.date.mock_day = 31
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 6, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 6
        autoentrepreneur.models.datetime.date.mock_day = 30
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 6, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 7
        autoentrepreneur.models.datetime.date.mock_day = 1
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 6, 30))


        # second case of www.lautoentrepreneur.fr
        profile.creation_date = datetimestub.DatetimeStub.date(2010, 7, 10)
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 7
        autoentrepreneur.models.datetime.date.mock_day = 10

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 12, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 8
        autoentrepreneur.models.datetime.date.mock_day = 10

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 12, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 12
        autoentrepreneur.models.datetime.date.mock_day = 31

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 12, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 12, 31))

    def testPeriodQuaterlySecondPayment(self):
        profile = self.user.get_profile()
        profile.payment_option = AUTOENTREPRENEUR_PAYMENT_OPTION_QUATERLY
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 8
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 1, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 9, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 10
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 1, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 9, 30))


        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 7, 10)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2011, 1, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 3, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 4
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 7, 10)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2011, 1, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 3, 31))

    def testPeriodMonthlyFirstPayment(self):
        """
        Periodicite mensuelle
        La premiere declaration mensuelle porte sur la periode comprise entre
        le debut d'activite et la fin du troisieme mois civil qui suit.
        http://www.lautoentrepreneur.fr/questions_reponses.htm#Couts5
        """
        profile = self.user.get_profile()
        profile.payment_option = AUTOENTREPRENEUR_PAYMENT_OPTION_MONTHLY
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2011, 1, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2011, 1, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 4, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 12, 31)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 12, 31))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 3, 31))

        # first case of www.lautoentrepreneur.fr
        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 2, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 5, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 3
        autoentrepreneur.models.datetime.date.mock_day = 1

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 5, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 5
        autoentrepreneur.models.datetime.date.mock_day = 31

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 5, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 6
        autoentrepreneur.models.datetime.date.mock_day = 1

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 2, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 5, 31))

        # second case of www.lautoentrepreneur.fr
        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 7
        autoentrepreneur.models.datetime.date.mock_day = 10

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 7, 10)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 10, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 8
        autoentrepreneur.models.datetime.date.mock_day = 1

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 10, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 10
        autoentrepreneur.models.datetime.date.mock_day = 31

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 10, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 11
        autoentrepreneur.models.datetime.date.mock_day = 1

        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 7, 10))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 10, 31))

    def testPeriodMonthlySecondPayment(self):
        profile = self.user.get_profile()
        profile.payment_option = AUTOENTREPRENEUR_PAYMENT_OPTION_MONTHLY
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 6
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2011, 1, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2011, 5, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2011, 5, 31))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 7
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 2, 1)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 6, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 6, 30))

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 12
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.creation_date = datetimestub.DatetimeStub.date(2010, 7, 10)
        profile.save()
        begin_date, end_date = profile.get_period_for_tax()
        self.assertEquals(begin_date, datetimestub.DatetimeStub.date(2010, 11, 1))
        self.assertEquals(end_date, datetimestub.DatetimeStub.date(2010, 11, 30))

    def testBaseRate(self):
        """
        Without creation help and without freeing tax payment
        http://www.lautoentrepreneur.fr/questions_reponses.htm#Couts1
        """
        profile = self.user.get_profile()
        profile.creation_date = datetimestub.DatetimeStub.date(2011, 1, 1)
        profile.freeing_tax_payment = False
        profile.creation_help = False
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 21.3)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 21.3)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 18.3)

    def testRateWithFreeingTaxPayment(self):
        """
        Without creation help and with freeing tax payment
        http://www.lautoentrepreneur.fr/questions_reponses.htm#Couts1
        """
        profile = self.user.get_profile()
        profile.creation_date = datetimestub.DatetimeStub.date(2011, 1, 1)
        profile.freeing_tax_payment = True
        profile.creation_help = False
        profile.save()

        autoentrepreneur.models.datetime.date.mock_year = 2011
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 13.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 23.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 23.5)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 20.5)

    def testRateWithCreationHelpWithoutFreeingTaxPayment(self):
        """
        With creation help and without freeing tax payment
        http://www.lautoentrepreneur.fr/questions_reponses.htm#Couts1
        """
        profile = self.user.get_profile()
        profile.creation_date = datetimestub.DatetimeStub.date(2007, 1, 1)
        profile.freeing_tax_payment = False
        profile.creation_help = True
        profile.save()

        # inserting fake sales limit for test
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC, limit=80000, limit2=88000)
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC, limit=80000, limit2=88000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC, limit=32000, limit2=34000)

        autoentrepreneur.models.datetime.date.mock_year = 2007
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 3.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 5.4)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 5.4)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 5.3)

        autoentrepreneur.models.datetime.date.mock_year = 2008
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 3.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 5.4)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 5.4)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 5.3)

        autoentrepreneur.models.datetime.date.mock_year = 2008
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 6.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 10.7)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 10.7)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 9.2)

        autoentrepreneur.models.datetime.date.mock_year = 2009
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 6.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 10.7)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 10.7)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 9.2)

        autoentrepreneur.models.datetime.date.mock_year = 2009
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 9.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 16.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 16.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 13.8)

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 9.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 16.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 16.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 13.8)

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 21.3)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 21.3)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 18.3)

    def testRateWithCreationHelpWithFreeingTaxPayment(self):
        """
        With creation help and freeing tax payment
        http://www.lautoentrepreneur.fr/questions_reponses.htm#Couts1
        """
        profile = self.user.get_profile()
        profile.creation_date = datetimestub.DatetimeStub.date(2007, 1, 1)
        profile.freeing_tax_payment = True
        profile.creation_help = True
        profile.save()

        # inserting fake sales limit for test
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC, limit=80000, limit2=88000)
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2007, activity=AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC, limit=80000, limit2=88000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC, limit=32000, limit2=34000)
        SalesLimit.objects.create(year=2008, activity=AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC, limit=32000, limit2=34000)

        autoentrepreneur.models.datetime.date.mock_year = 2007
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 4.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.1)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.6)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.5)

        autoentrepreneur.models.datetime.date.mock_year = 2008
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 4.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.1)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.6)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.5)

        autoentrepreneur.models.datetime.date.mock_year = 2008
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.4)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.9)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 11.4)

        autoentrepreneur.models.datetime.date.mock_year = 2009
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 7.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.4)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.9)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 11.4)

        autoentrepreneur.models.datetime.date.mock_year = 2009
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 10.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 17.7)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 18.2)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 16.0)

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 1
        autoentrepreneur.models.datetime.date.mock_day = 31

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 10.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 17.7)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 18.2)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 16.0)

        autoentrepreneur.models.datetime.date.mock_year = 2010
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 1

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 13.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 23.0)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_SERVICE_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 23.5)

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_LIBERAL_BNC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 20.5)

    def testProfessionalTrainingTaxRate(self):
        user = self.user
        profile = user.get_profile()
        profile.professional_category = AUTOENTREPRENEUR_PROFESSIONAL_CATEGORY_TRADER
        profile.save()
        address = profile.address
        address.zipcode = '44000'
        address.save()
        self.assertEquals(profile.get_professional_training_tax_rate(), 0.1)
        profile.professional_category = AUTOENTREPRENEUR_PROFESSIONAL_CATEGORY_CRAFTSMAN
        profile.save()
        self.assertEquals(profile.get_professional_training_tax_rate(), 0.3)
        address.zipcode = '67350'
        address.save()
        self.assertEquals(profile.get_professional_training_tax_rate(), 0.17)
        address.zipcode = '68350'
        address.save()
        self.assertEquals(profile.get_professional_training_tax_rate(), 0.17)
        profile.professional_category = AUTOENTREPRENEUR_PROFESSIONAL_CATEGORY_LIBERAL
        profile.save()
        self.assertEquals(profile.get_professional_training_tax_rate(), 0.2)

    def testLeapYear(self):
        profile = self.user.get_profile()
        profile.creation_date = datetimestub.DatetimeStub.date(2011, 1, 1)
        profile.freeing_tax_payment = False
        profile.creation_help = False
        profile.payment_option = AUTOENTREPRENEUR_PAYMENT_OPTION_MONTHLY
        profile.save()


        autoentrepreneur.models.datetime.date.mock_year = 2012
        autoentrepreneur.models.datetime.date.mock_month = 2
        autoentrepreneur.models.datetime.date.mock_day = 29

        profile.activity = AUTOENTREPRENEUR_ACTIVITY_PRODUCT_SALE_BIC
        profile.save()
        self.assertEquals(profile.get_tax_rate(), 12.0)
