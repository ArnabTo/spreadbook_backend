from django.core.management import call_command
from django_cron import CronJobBase, Schedule


def my_backup():
    try:
        call_command("dbbackup")
    except:
        pass


def subscription_maintenance():
    try:
        call_command("subscription_maintenance")
    except:
        pass


# import os
# from django.core import management
# from django.conf import settings
# from django_cron import CronJobBase, Schedule


# class Backup(CronJobBase):
#      RUN_AT_TIMES = ['6:00', '12:24']
#      schedule = Schedule(run_at_times=RUN_AT_TIMES)
#      code = 'ERP_Shop.Backup'

#      def do(self):
#           management.call_command('dbbackup')
