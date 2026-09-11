"""End-to-end tests for the CommUnity event lifecycle and role-based access."""

import json
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from committees.models import Announcement, Associations
from events.models import Event, EventLog, EventRegistration, FacultyLockDate, Location
from faculty.models import Faculty
from Login.models import Notification
from members.models import CoreMember, Member

TEMP_MEDIA = tempfile.mkdtemp()


def make_user(username, role, full_name=None):
    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@somaiya.edu", password='Str0ng-pass!'
    )
    profile = user.userprofile
    profile.full_name = full_name or username.title()
    profile.role = role
    profile.save()
    return user


@override_settings(MEDIA_ROOT=TEMP_MEDIA, AI_PROVIDER='template', GOOGLE_CALENDAR_ID='')
class CommunityTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.faculty_user = make_user('prof', 'faculty', 'Dr. Mehta')
        self.faculty = Faculty.objects.get(id=self.faculty_user.userprofile)
        self.faculty.can_lock_dates = True
        self.faculty.save()

        self.core_user = make_user('lead', 'core_member', 'Asha Lead')
        self.core = CoreMember.objects.get(id=self.core_user.userprofile)
        self.student_user = make_user('stud', 'non_participating', 'Ravi Student')

        self.club = Associations.objects.create(
            name='Coding Club', description='We code.', type='clubs', category='Technical',
            faculty_incharge=self.faculty, created_by=self.core, owner=self.core, status='approved',
        )
        self.core.association = self.club
        self.core.save()

        self.auditorium = Location.objects.create(location='auditorium')
        self.online = Location.objects.create(location='online')

    def make_event(self, days=5, hours=2, status='approved', location=None, **extra):
        return Event.objects.create(
            title=extra.pop('title', 'Hack Night'), description='Build things.',
            date_time=timezone.now() + timedelta(days=days), duration=hours,
            location=location or self.auditorium, association=self.club,
            created_by=self.core.id, status=status, **extra,
        )

    def event_post_data(self, when, **overrides):
        data = {
            'title': 'AI Workshop',
            'description': 'Hands-on intro to machine learning.',
            'date_time': timezone.localtime(when).strftime('%Y-%m-%dT%H:%M'),
            'duration': 2,
            'location': self.auditorium.pk,
            'registration_open': 'on',
        }
        data.update(overrides)
        return data


class PageRenderingTests(CommunityTestCase):
    """Every page renders for the roles that can see it."""

    def test_public_pages(self):
        event = self.make_event()
        Announcement.objects.create(title='Welcome', message='Hello', club=self.club, created_by=self.core.id)
        for url in [
            reverse('home'), reverse('club_list'), reverse('committees_list'), reverse('event_list'),
            reverse('event_list') + '?when=past', reverse('view_calendar'), reverse('notice_board'),
            reverse('club_detail', args=[self.club.pk]), reverse('event_details', args=[event.id]),
            reverse('account_login'), reverse('account_signup'), reverse('get_calendar_events'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_core_member_pages(self):
        event = self.make_event()
        self.client.force_login(self.core_user)
        for url in [
            reverse('home'), reverse('dashboard'), reverse('getprofile'), reverse('edit_profile'),
            reverse('notification_view'), reverse('create_event'), reverse('add_announcement'),
            reverse('add_member'), reverse('edit_club_committee', args=[self.club.pk]),
            reverse('delete_club_committee', args=[self.club.pk]), reverse('event_attendees', args=[event.id]),
            reverse('event_details', args=[event.id]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_faculty_pages(self):
        self.make_event(status='pending')
        self.client.force_login(self.faculty_user)
        self.assertRedirects(self.client.get(reverse('home')), reverse('faculty'))
        for url in [
            reverse('faculty'), reverse('approve_clubs'), reverse('faculty_committee'),
            reverse('add_core_member'), reverse('manage_faculty_lock_dates'), reverse('faculty_reports'),
            reverse('club_member', args=[self.club.pk]), reverse('getprofile'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_student_pages(self):
        self.client.force_login(self.student_user)
        for url in [reverse('dashboard'), reverse('getprofile'), reverse('notification_view')]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_core_member_without_team_sees_create_prompt(self):
        loner = make_user('loner', 'core_member')
        self.client.force_login(loner)
        self.assertContains(self.client.get(reverse('dashboard')), 'Create your club or committee')
        self.assertEqual(self.client.get(reverse('add_club_committee')).status_code, 200)


class RoleGuardTests(CommunityTestCase):
    def test_students_cannot_open_faculty_pages(self):
        self.client.force_login(self.student_user)
        for name in ['faculty', 'approve_clubs', 'add_core_member', 'manage_faculty_lock_dates']:
            with self.subTest(name=name):
                self.assertRedirects(self.client.get(reverse(name)), reverse('home'))

    def test_students_cannot_promote_themselves(self):
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('select_student'), json.dumps({'student_id': 'stud'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.student_user.userprofile.refresh_from_db()
        self.assertEqual(self.student_user.userprofile.role, 'non_participating')

    def test_anonymous_users_are_sent_to_login(self):
        response = self.client.get(reverse('create_event'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response['Location'])

    def test_pending_events_are_hidden_from_the_public(self):
        event = self.make_event(status='pending')
        self.assertEqual(self.client.get(reverse('event_details', args=[event.id])).status_code, 404)
        self.client.force_login(self.faculty_user)
        self.assertEqual(self.client.get(reverse('event_details', args=[event.id])).status_code, 200)

    def test_only_owner_can_request_deletion(self):
        other_core = make_user('second', 'core_member')
        CoreMember.objects.filter(id=other_core.userprofile).update(association=self.club)
        self.client.force_login(other_core)
        self.client.post(reverse('delete_club_committee', args=[self.club.pk]))
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, 'approved')


class EventWorkflowTests(CommunityTestCase):
    def test_create_submit_approve_flow(self):
        self.client.force_login(self.core_user)
        response = self.client.post(reverse('create_event'), self.event_post_data(timezone.now() + timedelta(days=3)))
        event = Event.objects.get(title='AI Workshop')
        self.assertRedirects(response, reverse('event_details', args=[event.id]))
        self.assertEqual(event.status, 'pending')
        self.assertTrue(Notification.objects.filter(recipient=self.faculty.id, title__contains='Approval needed').exists())
        self.assertEqual(len(mail.outbox), 1)

        self.client.force_login(self.faculty_user)
        self.client.post(reverse('approve_clubs'), {'action': 'approve_event', 'event_id': event.id, 'remarks': 'Great idea'})
        event.refresh_from_db()
        self.assertEqual(event.status, 'approved')
        self.assertEqual(event.approved_by, self.faculty)
        self.assertEqual(event.remarks, 'Great idea')
        self.assertTrue(Notification.objects.filter(recipient=self.core.id, kind='success').exists())
        self.assertEqual(list(event.logs.values_list('action', flat=True)), ['created', 'approved'])

    def test_reject_then_resubmit(self):
        event = self.make_event(status='pending')
        self.client.force_login(self.faculty_user)
        self.client.post(reverse('review_event', args=[event.id]), {'action': 'reject', 'remarks': 'Pick another venue'})
        event.refresh_from_db()
        self.assertEqual(event.status, 'rejected')

        self.client.force_login(self.core_user)
        data = self.event_post_data(event.date_time, title='Hack Night v2', location=self.online.pk)
        self.client.post(reverse('edit_event', args=[event.id]), data)
        event.refresh_from_db()
        self.assertEqual((event.status, event.title), ('pending', 'Hack Night v2'))
        self.assertTrue(event.logs.filter(action='updated').exists())

    def test_overlapping_booking_is_rejected_at_creation(self):
        existing = self.make_event(days=4, hours=3)
        self.client.force_login(self.core_user)
        response = self.client.post(reverse('create_event'),
                                    self.event_post_data(existing.date_time + timedelta(hours=1)))
        self.assertContains(response, 'already booked')
        self.assertFalse(Event.objects.filter(title='AI Workshop').exists())

    def test_online_events_never_conflict(self):
        existing = self.make_event(days=4, location=self.online)
        self.client.force_login(self.core_user)
        self.client.post(reverse('create_event'), self.event_post_data(existing.date_time, location=self.online.pk))
        self.assertTrue(Event.objects.filter(title='AI Workshop').exists())

    def test_approval_rechecks_conflicts_between_pending_requests(self):
        first = self.make_event(days=6, status='pending', title='First')
        second = self.make_event(days=6, status='pending', title='Second')
        self.client.force_login(self.faculty_user)
        self.client.post(reverse('approve_clubs'), {'action': 'approve_event', 'event_id': first.id})
        self.client.post(reverse('approve_clubs'), {'action': 'approve_event', 'event_id': second.id})
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.status, second.status), ('approved', 'pending'))

    def test_locked_dates_block_events(self):
        when = timezone.now() + timedelta(days=10)
        FacultyLockDate.objects.create(locked_date=timezone.localtime(when).date(), reason='Exams')
        self.client.force_login(self.core_user)
        response = self.client.post(reverse('create_event'), self.event_post_data(when))
        self.assertContains(response, 'reserved by faculty')

    def test_past_dates_are_rejected(self):
        self.client.force_login(self.core_user)
        response = self.client.post(reverse('create_event'), self.event_post_data(timezone.now() - timedelta(days=1)))
        self.assertContains(response, 'must be scheduled in the future')

    def test_check_slot_endpoint(self):
        existing = self.make_event(days=4)
        self.client.force_login(self.core_user)
        params = {'date_time': timezone.localtime(existing.date_time).strftime('%Y-%m-%dT%H:%M'),
                  'duration': 1, 'location': self.auditorium.pk}
        data = self.client.get(reverse('check_slot'), params).json()
        self.assertFalse(data['ok'])
        params['location'] = self.online.pk
        self.assertTrue(self.client.get(reverse('check_slot'), params).json()['ok'])

    def test_cancel_notifies_registrants(self):
        event = self.make_event()
        EventRegistration.objects.create(event=event, participant=self.student_user.userprofile)
        self.client.force_login(self.core_user)
        self.client.post(reverse('cancel_event', args=[event.id]), {'reason': 'Venue unavailable'})
        event.refresh_from_db()
        self.assertEqual(event.status, 'cancelled')
        self.assertTrue(Notification.objects.filter(recipient=self.student_user.userprofile, kind='danger').exists())


class RegistrationTests(CommunityTestCase):
    def test_register_and_unregister(self):
        event = self.make_event()
        self.client.force_login(self.student_user)
        url = reverse('toggle_registration', args=[event.id])
        self.client.post(url)
        self.assertTrue(EventRegistration.objects.filter(event=event).exists())
        self.client.post(url)
        self.assertFalse(EventRegistration.objects.filter(event=event).exists())

    def test_seat_limit(self):
        event = self.make_event(max_participants=1)
        EventRegistration.objects.create(event=event, participant=self.core.id)
        self.client.force_login(self.student_user)
        self.client.post(reverse('toggle_registration', args=[event.id]))
        self.assertEqual(event.registrations.count(), 1)

    def test_attendance_marking_and_csv(self):
        event = self.make_event()
        registration = EventRegistration.objects.create(event=event, participant=self.student_user.userprofile)
        self.client.force_login(self.core_user)
        self.client.post(reverse('event_attendees', args=[event.id]), {'attended': [registration.pk]})
        registration.refresh_from_db()
        self.assertTrue(registration.attended)
        csv_response = self.client.get(reverse('event_attendees', args=[event.id]), {'format': 'csv'})
        self.assertIn('Ravi Student', csv_response.content.decode())


class ReportTests(CommunityTestCase):
    report_data = {
        'organizer': 'Coding Club', 'event_type': 'Workshop', 'attendees': 42,
        'speakers': 'Dr. A. Rao - ML Engineer', 'agenda': 'Intro\nHands-on lab',
        'highlights': 'Live demo', 'outcomes': 'Built a classifier', 'feedback': '', 'media_links': '',
    }

    def completed_event(self):
        event = self.make_event()
        Event.objects.filter(pk=event.pk).update(date_time=timezone.now() - timedelta(days=2))
        event.refresh_from_db()
        return event

    def test_report_cannot_be_generated_before_the_event(self):
        event = self.make_event()
        self.client.force_login(self.core_user)
        self.assertRedirects(self.client.get(reverse('generate_event_report', args=[event.id])),
                             reverse('event_details', args=[event.id]))

    def test_template_report_and_pdf(self):
        event = self.completed_event()
        self.client.force_login(self.core_user)
        self.assertEqual(self.client.get(reverse('generate_event_report', args=[event.id])).status_code, 200)
        self.client.post(reverse('generate_event_report', args=[event.id]), self.report_data)
        event.refresh_from_db()
        self.assertTrue(event.report_generated)
        self.assertIn('## Proceedings', event.report_content)
        self.assertIn('42 participants', event.report_content)
        self.assertTrue(event.report_pdf.name.endswith('.pdf'))
        with event.report_pdf.open('rb') as pdf:
            self.assertEqual(pdf.read(4), b'%PDF')
        self.assertTrue(Notification.objects.filter(recipient=self.faculty.id, title__startswith='Report submitted').exists())

        # Organisers can edit; the public can read.
        self.client.post(reverse('event_report', args=[event.id]), {'report_content': '## Overview\nEdited text'})
        event.refresh_from_db()
        self.assertEqual(event.report_content, '## Overview\nEdited text')
        self.client.logout()
        self.assertContains(self.client.get(reverse('event_report', args=[event.id])), 'Edited text')

    @override_settings(AI_PROVIDER='anthropic', ANTHROPIC_API_KEY='test-key')
    def test_claude_is_used_when_configured(self):
        event = self.completed_event()
        fake_response = mock.Mock(stop_reason='end_turn',
                                  content=[mock.Mock(type='text', text='# Report\n\n## Overview\nClaude wrote this.')])
        fake_client = mock.Mock()
        fake_client.beta.messages.create.return_value = fake_response
        fake_module = mock.Mock(Anthropic=mock.Mock(return_value=fake_client))
        with mock.patch.dict('sys.modules', {'anthropic': fake_module}):
            self.client.force_login(self.core_user)
            self.client.post(reverse('generate_event_report', args=[event.id]), self.report_data)
        event.refresh_from_db()
        self.assertIn('Claude wrote this.', event.report_content)
        self.assertTrue(event.report_provider.startswith('Claude'))
        kwargs = fake_client.beta.messages.create.call_args.kwargs
        self.assertEqual(kwargs['model'], 'claude-opus-5')
        self.assertEqual(kwargs['fallbacks'], 'default')
        self.assertIn('42', kwargs['messages'][0]['content'])

    @override_settings(AI_PROVIDER='anthropic', ANTHROPIC_API_KEY='test-key')
    def test_falls_back_to_template_when_ai_is_unavailable(self):
        event = self.completed_event()
        with mock.patch.dict('sys.modules', {'anthropic': None}):
            self.client.force_login(self.core_user)
            response = self.client.post(reverse('generate_event_report', args=[event.id]), self.report_data, follow=True)
        event.refresh_from_db()
        self.assertTrue(event.report_generated)
        self.assertEqual(event.report_provider, 'CommUnity template')
        self.assertContains(response, "AI generation wasn&#x27;t available")


class CalendarTests(CommunityTestCase):
    def test_ics_download_and_feed(self):
        event = self.make_event()
        ics = self.client.get(reverse('event_ics', args=[event.id])).content.decode()
        self.assertIn('BEGIN:VEVENT', ics)
        self.assertIn('SUMMARY:Hack Night', ics)
        self.assertIn('BEGIN:VEVENT', self.client.get(reverse('calendar_feed')).content.decode())

    def test_calendar_json_includes_locked_days(self):
        self.make_event()
        FacultyLockDate.objects.create(locked_date=timezone.localdate() + timedelta(days=20), reason='Fest')
        feed = self.client.get(reverse('get_calendar_events')).json()
        self.assertEqual({item.get('display') for item in feed}, {None, 'background'})

    def test_google_calendar_sync_is_skipped_when_not_configured(self):
        event = self.make_event(status='pending')
        self.client.force_login(self.faculty_user)
        self.client.post(reverse('review_event', args=[event.id]), {'action': 'approve'})
        event.refresh_from_db()
        self.assertEqual(event.status, 'approved')
        self.assertIsNone(event.google_calendar_event_id)


class AssociationTests(CommunityTestCase):
    def test_follow_toggle_and_announcement_notifications(self):
        self.client.force_login(self.student_user)
        data = self.client.post(reverse('toggle_follow', args=[self.club.pk]), HTTP_ACCEPT='application/json').json()
        self.assertTrue(data['following'])
        Announcement.objects.create(title='Meetup', message='Friday', club=self.club, created_by=self.core.id)
        self.assertContains(self.client.get(reverse('notification_view')), 'Meetup')

    def test_follow_requires_login(self):
        self.assertEqual(self.client.post(reverse('toggle_follow', args=[self.club.pk])).status_code, 401)

    def test_new_association_goes_to_faculty(self):
        founder = make_user('founder', 'core_member')
        self.client.force_login(founder)
        self.client.post(reverse('add_club_committee'), {
            'name': 'Robotics', 'type': 'clubs', 'category': 'Technical',
            'description': 'Robots!', 'faculty_incharge': self.faculty.pk,
        })
        robotics = Associations.objects.get(name='Robotics')
        self.assertEqual(robotics.status, 'pending')

        self.client.force_login(self.faculty_user)
        self.client.post(reverse('approve_clubs'), {'action': 'approve', 'club_id': robotics.pk})
        robotics.refresh_from_db()
        self.assertEqual(robotics.status, 'approved')

    def test_deleting_association_keeps_core_member_records(self):
        self.club.status = 'delete_pending'
        self.club.save()
        self.client.force_login(self.faculty_user)
        self.client.post(reverse('approve_clubs'), {'action': 'approve_delete', 'club_id': self.club.pk})
        self.assertFalse(Associations.objects.filter(pk=self.club.pk).exists())
        self.assertTrue(CoreMember.objects.filter(pk=self.core.pk).exists())

    def test_owner_adds_member_and_core_member(self):
        self.client.force_login(self.core_user)
        results = self.client.post(reverse('add_member'), json.dumps({'query': 'rav'}),
                                   content_type='application/json').json()['students']
        self.assertEqual(results[0]['id'], 'stud')
        response = self.client.post(reverse('select_member'), json.dumps({'student_id': 'stud', 'role': 'member'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.club.pk, Member.objects.get(id=self.student_user.userprofile).association_ids)

        make_user('second', 'non_participating')
        self.client.post(reverse('select_member'), json.dumps({'student_id': 'second', 'role': 'core_member'}),
                         content_type='application/json')
        self.assertEqual(CoreMember.objects.get(id__id__username='second').association, self.club)

    def test_faculty_appoints_core_member_to_their_team(self):
        self.client.force_login(self.faculty_user)
        response = self.client.post(reverse('select_student'),
                                    json.dumps({'student_id': 'stud', 'association_id': self.club.pk}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CoreMember.objects.get(id=self.student_user.userprofile).association, self.club)


class AuthTests(TestCase):
    def test_signup_is_limited_to_college_domain(self):
        response = self.client.post(reverse('account_signup'), {
            'full_name': 'Outsider', 'email': 'someone@gmail.com',
            'password1': 'Str0ng-pass!', 'password2': 'Str0ng-pass!',
        })
        self.assertContains(response, 'somaiya.edu')
        self.assertFalse(get_user_model().objects.filter(email='someone@gmail.com').exists())

    def test_signup_saves_full_name(self):
        self.client.post(reverse('account_signup'), {
            'full_name': 'Neha Shah', 'email': 'neha@somaiya.edu',
            'password1': 'Str0ng-pass!', 'password2': 'Str0ng-pass!',
        })
        user = get_user_model().objects.get(email='neha@somaiya.edu')
        self.assertEqual(user.userprofile.full_name, 'Neha Shah')
