"""
Handles the firing of events to any configured listeners. This module is
responsible for defining what events look like. The specific fire methods for
each event type require data relevant to that event type and package it up
in a consistent event format for that type.
"""

import logging

from pulp.server.db.model.event import EventListener
from pulp.server.event import data as e, notifiers


_logger = logging.getLogger(__name__)


class EventFireManager(object):

    def fire_repo_sync_started(self, repo_id):
        """
        Fires an event indicating the given repository has started a sync.
        """
        payload = {'repo_id': repo_id}
        self._do_fire(e.Event(e.TYPE_REPO_SYNC_STARTED, payload))

    def fire_repo_sync_finished(self, sync_result):
        """
        Fires an event indicating the given repository has completed a sync.
        The success/failure of the sync, timestamp information, and sync report
        provided by the importer are all included in the sync_result.

        @param sync_result: DB object describing the sync result
        @type  sync_result: dict
        """
        sync_result.pop('_id', None)
        self._do_fire(e.Event(e.TYPE_REPO_SYNC_FINISHED, sync_result))

    def fire_repo_publish_started(self, repo_id, distributor_id):
        """
        Fires an event indicating the given repository's distributor has started
        a publish.
        """
        payload = {'repo_id': repo_id, 'distributor_id': distributor_id}
        self._do_fire(e.Event(e.TYPE_REPO_PUBLISH_STARTED, payload))

    def fire_repo_publish_finished(self, publish_result):
        """
        Fires an event indicating the given repository has completed a publish.
        The success/failure of the publish, timestamp information, and publish report
        provided by the distributor are all included in the publish_result.
        """
        publish_result.pop('_id', None)
        self._do_fire(e.Event(e.TYPE_REPO_PUBLISH_FINISHED, publish_result))

    def _do_fire(self, event):
        """
        Performs the actual act of firing an event to all appropriate
        listeners. This call will log but otherwise suppress any exception
        that comes out of a notifier.

        @param event: event object to fire
        @type  event: pulp.server.event.data.Event
        """
        # Determine which listeners should be notified
        listeners = list(EventListener.get_collection().find(
            {'$or': ({'event_types': event.event_type}, {'event_types': '*'})}))

        # For each listener, retrieve the notifier and invoke it. Be sure that
        # an exception from a notifier is logged but does not interrupt the
        # remainder of the firing, nor bubble up.
        for listener in listeners:
            notifier_type_id = listener['notifier_type_id']
            f = notifiers.get_notifier_function(notifier_type_id)

            try:
                f(listener['notifier_config'], event)
            except Exception:
                _logger.exception('Exception from notifier of type [%s]' % notifier_type_id)
