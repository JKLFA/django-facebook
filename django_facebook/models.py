from datetime import datetime
import re

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from django_facebook import signals

GENDERS = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class FacebookProfile(models.Model):
    user        = models.OneToOneField(User, related_name="fb_profile")
    last_update = models.DateTimeField()

    uid         = models.CharField(max_length=31, unique=True)

    # all optional data
    username    = models.CharField(max_length=64, null=True, blank=True)
    name        = models.CharField(max_length=100, null=True, blank=True)
    first_name  = models.CharField(max_length=31, null=True, blank=True)
    middle_name = models.CharField(max_length=31, null=True, blank=True)
    last_name   = models.CharField(max_length=31, null=True, blank=True)
    link        = models.URLField(null=True, blank=True)
    birthday    = models.DateField(null=True, blank=True)
    hometown    = models.CharField(max_length=31, null=True, blank=True)
    bio         = models.TextField(null=True, blank=True)
    gender      = models.CharField(max_length=1, choices=GENDERS, null=True, blank=True)
    modified    = models.DateTimeField(null=True, blank=True)
    website     = models.CharField(max_length=255, null=True, blank=True)
    locale      = models.CharField(max_length=32, null=True, blank=True)
    timezone    = models.IntegerField(null=True, blank=True)

    schools     = models.ManyToManyField('School', through='Attended')

    def save(self, *args, **kwargs):
        ''' On save, update last_update timestamp '''

        self.last_update = datetime.now()
        super(FacebookProfile, self).save(*args, **kwargs)


    @property
    def websites(self):
        return self.website.split("\n")

    @property
    def newest_school(self):
        if self.attended_set.count() > 1:
            return self.attended_set.order_by('-year')[0]
        else:
            return None

    def update(self, fb_user):
        if self.uid != fb_user['id']:
            raise TypeError("Attempted to update a Facebook User with another "
                            "user's profile information")

        self.name = fb_user['name']
        self.modified = fb_user['updated_time'].replace('T', ' ').replace('+', '.')

        if 'birthday' in fb_user:
            match = re.search('(\d+)/(\d+)/(\d+)', fb_user['birthday'])
            if match:
                self.birthday = "%s-%s-%s" % (match.group(3), match.group(1), match.group(2))
        if 'username' in fb_user:
            self.username = fb_user['username']
        if 'first_name' in fb_user:
            self.first_name = fb_user['first_name']
        if 'middle_name' in fb_user:
            self.middle_name = fb_user['middle_name']
        if 'last_name' in fb_user:
            self.last_name = fb_user['last_name']
        if 'link' in fb_user:
            self.link = fb_user['link']
        if 'hometown' in fb_user:
            self.hometown = fb_user['hometown']['name']
        if 'bio' in fb_user:
            self.bio = fb_user['bio']
        if 'gender' in fb_user:
            self.gender = fb_user['gender'][0].upper()
        if 'website' in fb_user:
            self.website = fb_user['website']
        if 'locale' in fb_user:
            self.locale = fb_user['locale']
        if 'timezone' in fb_user:
            self.timezone = fb_user['timezone']

        if 'education' in fb_user:
            for attended in fb_user['education']:
                a = Attended.fromFacebookObject(attended, self)

        signals.fb_user_updated.send(self)

        self.save()

    @classmethod
    def fromFacebookObject(cls, fb_user, user):
        try:
            return FacebookProfile.objects.get(uid=fb_user['id'])
        except ObjectDoesNotExist:
            pass

        profile = FacebookProfile()

        profile.user = user
        profile.uid = fb_user['id']
        profile.save()

        profile.update(fb_user)

        return profile

    def __unicode__(self):
        return u"%s" % (self.name or self.uid)

class Attended(models.Model):
    profile     = models.ForeignKey(FacebookProfile)
    school      = models.ForeignKey('School')
    concentrations = models.ManyToManyField('Concentration', null=True, blank=True)
    year        = models.CharField(max_length=8, null=True, blank=True)
    type        = models.CharField(max_length=32, null=True, blank=True)

    def is_alum(self):
        """ If graduating year was before now or graduated this year and it's after May 15 """
        currentYear = int(datetime.today().strftime('%Y'))
        return int(self.year) <  currentYear or \
               int(self.year) == currentYear and \
               datetime.now() > datetime(currentYear, 5, 15)

    @classmethod
    def fromFacebookObject(cls, fb_att, profile):
        try:
            dict = { "profile": profile, }
            if 'school' in fb_att:
                dict['school'] = School.fromFacebookObject(fb_att['school'])
            if 'year' in fb_att:
                if 'name' in fb_att['year']:
                    dict['year'] = fb_att['year']['name']
            if 'type' in fb_att:
                dict['type'] = fb_att['type']
            return Attended.objects.get(**dict)
        except ObjectDoesNotExist:
            pass

        a = Attended()
        if 'school' in fb_att:
            a.school = School.fromFacebookObject(fb_att['school'])
        if 'type' in fb_att:
            a.type = fb_att['type']
        if 'year' in fb_att:
            if 'name' in fb_att['year']:
                a.year = fb_att['year']['name']
        a.profile = profile

        # must have a primary key before creating M2M relationships
        a.save()

        if 'concentration' in fb_att:
            for c in fb_att['concentration']:
                conc = Concentration.fromFacebookObject(c)
                if conc:
                    a.concentrations.add(conc)
            a.save()
        return a

    @property
    def first_concentration(self):
        # TODO: order this somehow?
        if self.concentrations.count() > 0:
            return self.concentrations.all()[0]
        else:
            return None

    def __unicode__(self):
        return u"%s attended %s in %s" % (self.profile, self.school, self.year)

class Concentration(models.Model):
    cid         = models.CharField(max_length=31, unique=True)
    name        = models.CharField(max_length=64, null=True, blank=True)
    link        = models.URLField(null=True, blank=True)

    @classmethod
    def fromFacebookObject(cls, fb_con):
        """
        Build a Concentration model out of the given fb object, or return the
        one that's already built if it exists
        """
        try:
            return Concentration.objects.get(cid=fb_con['id'])
        except ObjectDoesNotExist:
            pass

        c = Concentration()
        if 'id' in fb_con:
            c.cid = fb_con['id']
        if 'name' in fb_con:
            c.name = fb_con['name']
        if 'link' in fb_con:
            c.link = fb_con['link']
        c.save()
        return c

    def __unicode__(self):
        return u"%s" % (self.name or self.cid)

class School(models.Model):
    sid         = models.CharField(max_length=31, unique=True)
    name        = models.CharField(max_length=64, null=True, blank=True)
    picture     = models.URLField(null=True, blank=True)
    founded     = models.DateTimeField(null=True, blank=True)
    link        = models.URLField(null=True, blank=True)
    city        = models.CharField(max_length=128, null=True, blank=True)
    country     = models.CharField(max_length=64, null=True, blank=True)
    state       = models.CharField(max_length=16, null=True, blank=True)
    zip         = models.CharField(max_length=15, null=True, blank=True)
    website     = models.CharField(max_length=255, null=True, blank=True)
    phone       = models.CharField(max_length=32, null=True, blank=True)

    @property
    def websites(self):
        return self.website.split("\n")

    @classmethod
    def fromFacebookObject(cls, fb_school):
        """
        Build a School model out of the given fb object, or return the one
        that's already built if it exists
        """

        try:
            return School.objects.get(sid=fb_school['id'])
        except ObjectDoesNotExist:
            pass

        s = School()

        s.sid = fb_school['id']

        if 'name' in fb_school:
            s.name = fb_school['name']
        if 'picture' in fb_school:
            s.picture = fb_school['picture']
        if 'founded' in fb_school:
            s.founded = fb_school['founded']
        if 'link' in fb_school:
            s.link = fb_school['link']
        if 'city' in fb_school:
            s.city = fb_school['city']
        if 'country' in fb_school:
            s.country = fb_school['country']
        if 'state' in fb_school:
            s.state = fb_school['state']
        if 'zip' in fb_school:
            s.zip = fb_school['zip']
        if 'website' in fb_school:
            s.website = fb_school['website']
        if 'phone' in fb_school:
            s.phone = fb_school['phone']

        s.save()
        return s

    def __unicode__(self):
        return u"%s" % (self.name or self.sid)
