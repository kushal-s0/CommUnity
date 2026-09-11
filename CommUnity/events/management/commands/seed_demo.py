"""
Fill the database with a realistic demo: faculty, clubs, committees, events in
every lifecycle stage, registrations, announcements and a finished report.

    python manage.py seed_demo            # safe to run repeatedly
    python manage.py seed_demo --password "MyDemo@1"
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from committees.models import Announcement, Associations
from events.ai_report import generate_from_template
from events.models import Event, EventLog, EventRegistration, FacultyLockDate, Location
from faculty.models import Faculty
from members.models import CoreMember, Member

DOMAIN = 'somaiya.edu'

FACULTY = [
    ('kavita.sharma', 'Dr. Kavita Sharma', 'Computer Engineering', 'Associate Professor', True),
    ('rahul.iyer', 'Prof. Rahul Iyer', 'Information Technology', 'Assistant Professor', False),
]
CORE = [
    ('aarav.mehta', 'Aarav Mehta', 'Technical Head'),
    ('diya.patel', 'Diya Patel', 'Cultural Secretary'),
    ('kabir.singh', 'Kabir Singh', 'Sports Captain'),
    ('meera.nair', 'Meera Nair', 'NSS Coordinator'),
    ('rohan.das', 'Rohan Das', 'Chair'),
]
STUDENTS = [
    ('ananya.rao', 'Ananya Rao'), ('vikram.joshi', 'Vikram Joshi'), ('sara.khan', 'Sara Khan'),
    ('arjun.kulkarni', 'Arjun Kulkarni'), ('isha.verma', 'Isha Verma'), ('nikhil.shetty', 'Nikhil Shetty'),
]
ASSOCIATIONS = [
    # name, type, category, faculty index, core index, status, description
    ('CodeCraft Club', 'clubs', 'Technical', 0, 0, 'approved',
     'CodeCraft brings together students who love building software — weekly coding circles, hackathons '
     'and hands-on workshops on web, AI and competitive programming.'),
    ('Rhythm Cultural Committee', 'committees', 'Cultural', 1, 1, 'approved',
     'Rhythm organises the annual cultural fest, music nights and dance competitions, and represents the '
     'college at inter-college festivals.'),
    ('Sports Council', 'committees', 'Sports', 1, 2, 'approved',
     'The Sports Council runs intra-college tournaments, fitness drives and selection trials for university teams.'),
    ('NSS Unit', 'committees', 'Social', 0, 3, 'approved',
     'The National Service Scheme unit leads blood donation camps, cleanliness drives and community outreach.'),
    ('IEEE Student Branch', 'clubs', 'Academic', 0, 4, 'pending',
     'A student chapter of IEEE hosting technical talks, paper-writing sessions and industry visits.'),
]
VENUES = ['auditorium', 'seminar hall', 'turf', 'open canteen', 'online']


class Command(BaseCommand):
    help = 'Create demo users, clubs, committees, events and a sample report.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='CommUnity@123', help='Password for every demo account.')

    def handle(self, *args, **options):
        password = options['password']
        now = timezone.now()
        User = get_user_model()

        def user(username, full_name, role):
            account, created = User.objects.get_or_create(
                username=username, defaults={'email': f'{username}@{DOMAIN}'}
            )
            if created:
                account.set_password(password)
                account.save()
            profile = account.userprofile
            profile.full_name = full_name
            profile.role = role
            profile.save()
            return profile

        faculty = []
        for username, name, department, designation, can_lock in FACULTY:
            member = Faculty.objects.get(id=user(username, name, 'faculty'))
            member.department, member.designation, member.can_lock_dates = department, designation, can_lock
            member.save()
            faculty.append(member)

        cores = []
        for username, name, position in CORE:
            core = CoreMember.objects.get(id=user(username, name, 'core_member'))
            core.position = position
            core.save()
            cores.append(core)

        students = [user(username, name, 'non_participating') for username, name in STUDENTS]
        venues = {name: Location.objects.get_or_create(location=name)[0] for name in VENUES}

        associations = []
        for name, kind, category, f_idx, c_idx, status, description in ASSOCIATIONS:
            association, _ = Associations.objects.update_or_create(name=name, defaults={
                'type': kind, 'category': category, 'description': description, 'status': status,
                'faculty_incharge': faculty[f_idx], 'created_by': cores[c_idx], 'owner': cores[c_idx],
            })
            cores[c_idx].association = association
            cores[c_idx].save()
            associations.append(association)
        codecraft, rhythm, sports, nss, _ieee = associations

        for profile in students[:3]:
            profile.role = 'member'
            profile.save()
            member = Member.objects.get(id=profile)
            member.association = sorted(set(member.association_ids) | {codecraft.pk})
            member.save()
        for profile in students:
            profile.preferences = sorted(set(profile.followed_ids) | {codecraft.pk, rhythm.pk})
            profile.save()

        def event(title, association, days, hour, hours, venue, status, description, seats=None):
            start = timezone.localtime(now + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
            record, created = Event.objects.get_or_create(title=title, association=association, defaults={
                'description': description, 'date_time': start, 'duration': hours, 'location': venues[venue],
                'created_by': association.owner.id, 'status': status, 'max_participants': seats,
                'approved_by': association.faculty_incharge if status == 'approved' else None,
            })
            if created:
                EventLog.objects.create(event=record, action='created', actor=association.owner.id)
                if status == 'approved':
                    EventLog.objects.create(event=record, action='approved', actor=association.faculty_incharge.id,
                                            note='Looks good — all the best!')
            return record

        hack = event('HackNight 3.0', codecraft, 6, 17, 5, 'seminar hall', 'approved',
                     'An evening hackathon: form teams of three, build something useful in five hours and demo it '
                     'to a panel of faculty judges.', seats=90)
        event('Intro to Machine Learning', codecraft, 2, 14, 2, 'online', 'approved',
              'A beginner-friendly live session on the building blocks of machine learning, with a hands-on notebook.')
        event('Inter-college Football Trials', sports, 9, 8, 4, 'turf', 'approved',
              'Selection trials for the university football team. Bring your own boots and ID card.', seats=40)
        event('Blood Donation Camp', nss, 4, 10, 6, 'open canteen', 'approved',
              'In partnership with the city blood bank. Every donor receives a certificate and refreshments.')
        event('Garba Night', rhythm, 12, 18, 4, 'auditorium', 'pending',
              'Our annual Navratri celebration with live music, dance and food stalls.', seats=300)
        event('Open Mic Evening', rhythm, 12, 19, 2, 'auditorium', 'pending',
              'Poetry, stand-up and acoustic music — sign up to perform or just come to listen.')
        past = event('Git & GitHub Workshop', codecraft, -12, 13, 3, 'seminar hall', 'approved',
                     'Version control from first commit to pull request, with practice repositories for every attendee.',
                     seats=60)
        event('Annual Sports Meet', sports, -20, 8, 8, 'turf', 'approved',
              'Track and field events, relays and the tug-of-war finals.')

        for profile in students:
            EventRegistration.objects.get_or_create(event=hack, participant=profile)
            EventRegistration.objects.get_or_create(event=past, participant=profile, defaults={'attended': True})

        if not past.report_generated:
            from events.views import _save_report

            data = {
                'organizer': codecraft.name, 'event_type': 'Workshop', 'attendees': 54,
                'speakers': 'Priya Menon - Senior Engineer, GitHub', 'agenda':
                    'Why version control matters\nCommits, branches and merges\nHands-on: fork, clone and open a pull request',
                'highlights': 'Every attendee merged their first pull request', 'outcomes':
                    'Students set up GitHub profiles\nThree teams started open-source contributions',
                'feedback': 'Average rating 4.7/5; students asked for an advanced session on rebasing.', 'media_links': '',
            }
            _save_report(past, generate_from_template(past, data), data, 'CommUnity template')
            EventLog.objects.create(event=past, action='report', actor=codecraft.owner.id, note='CommUnity template')

        for association, title, message in [
            (codecraft, 'HackNight 3.0 registrations are open', 'Teams of three, 90 seats. Register on the event page before Friday.'),
            (rhythm, 'Auditions for the cultural fest', 'Singers, dancers and performers — auditions run all next week in the auditorium.'),
            (nss, 'Volunteers needed for the blood donation camp', 'We need 20 volunteers for registration and refreshments. Reply to the NSS coordinator.'),
        ]:
            Announcement.objects.get_or_create(title=title, club=association,
                                               defaults={'message': message, 'created_by': association.owner.id})

        FacultyLockDate.objects.get_or_create(
            locked_date=(now + timedelta(days=24)).date(),
            defaults={'reason': 'Mid-semester examinations', 'created_by': faculty[0]},
        )

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write(f"All demo accounts use the password: {password}")
        self.stdout.write(f"  Faculty:      kavita.sharma@{DOMAIN}  (can reserve dates)")
        self.stdout.write(f"  Core member:  aarav.mehta@{DOMAIN}    (owner of CodeCraft Club)")
        self.stdout.write(f"  Student:      ananya.rao@{DOMAIN}")
