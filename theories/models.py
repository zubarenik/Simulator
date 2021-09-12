from django.db import models
from lessons.models import Lesson
from simulators.models import Simulator
from user_profile.models import User
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Max

import logging
logger = logging.getLogger("django.server")

# Create your models here.
class TheoryChapter(models.Model):
    simulator = models.ForeignKey(Simulator, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    sequence_no = models.PositiveIntegerField(null=True)

    @property
    def max_seq_no(self):
        seq_no = TheoryChapter.objects.filter(simulator=self.simulator).aggregate(Max("sequence_no"))['sequence_no__max']
        if seq_no:
            seq_no = seq_no + 1
        else:
            seq_no = 1
        return seq_no

    def __str__(self):
        return '{}. {}'.format(self.sequence_no, self.name)
    
    