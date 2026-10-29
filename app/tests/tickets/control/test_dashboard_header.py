import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django_scopes import scopes_disabled

from eventyay.base.meetup import EVENT_TYPE_SETTING, MEETUP_EVENT_TYPE
from eventyay.base.models import Event, Organizer, Team, User


@pytest.fixture
def env():
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Dummy', slug='dummy')
        event = Event.objects.create(
            organizer=organizer,
            name='Conference 2026',
            slug='dummy',
            date_from=now(),
        )
        user = User.objects.create_user('with_perm@example.com', 'dummy')
        team = Team.objects.create(
            organizer=organizer,
            can_change_event_settings=True,
            can_view_orders=True,
            all_events=True,
        )
        team.members.add(user)

        return {
            'organizer': organizer,
            'event': event,
            'user': user,
        }


def _dashboard_url(env):
    return reverse(
        'control:event.index',
        kwargs={'organizer': env['organizer'].slug, 'event': env['event'].slug},
    )


# The control middleware redirects to SITE_URL unless it matches the test client's host.
@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_header_shows_tickets_dashboard_title_and_event_name(client, env):
    client.force_login(env['user'])
    response = client.get(_dashboard_url(env))
    assert response.status_code == 200
    content = response.content.decode()

    # Modern dashboard header with the "Tickets dashboard" title.
    assert 'modern-dashboard' in content
    assert '<h2>Tickets dashboard</h2>' in content
    # Event name and date range shown beneath the title.
    assert 'dashboard-header-extra' in content
    assert 'Conference 2026' in content


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_header_preserves_component_link_navigation(client, env):
    client.force_login(env['user'])
    response = client.get(_dashboard_url(env))
    assert response.status_code == 200
    content = response.content.decode()

    # The component_link navigation (Home / Tickets / ...) is still rendered,
    # with the Tickets entry marked active.
    tickets_url = reverse(
        'control:event.index',
        kwargs={'organizer': env['organizer'].slug, 'event': env['event'].slug},
    )
    assert f'href="{tickets_url}"' in content
    assert 'navigation-button' in content


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_header_event_series_branch(client, env):
    with scopes_disabled():
        event = env['event']
        event.has_subevents = True
        event.save(update_fields=['has_subevents'])

    client.force_login(env['user'])
    response = client.get(_dashboard_url(env))
    assert response.status_code == 200
    content = response.content.decode()
    assert '<h2>Tickets dashboard</h2>' in content
    # Event series uses the "Event series" label instead of a date range.
    assert 'Event series' in content


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_header_meetup_branch(client, env):
    with scopes_disabled():
        env['event'].settings.set(EVENT_TYPE_SETTING, MEETUP_EVENT_TYPE)

    client.force_login(env['user'])
    response = client.get(_dashboard_url(env))
    assert response.status_code == 200
    content = response.content.decode()
    assert '<h2>Tickets dashboard</h2>' in content
    # Meetup events use the "Meetup" label.
    assert 'Meetup' in content
