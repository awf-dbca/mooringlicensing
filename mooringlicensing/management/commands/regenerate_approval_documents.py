from django.core.management.base import BaseCommand

import logging

logger = logging.getLogger('cron_tasks')
cron_email = logging.getLogger('cron_email')


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        pass

        #check approvals that need document regen (requires bool field)

        #check why documents need regen (requires char field)

        #regen doc based on type and reason

        #create history record

        #create action log

        #set bool to false, char to None

        #send out notification emails if reason requires it (TODO or NOTE for later?)

