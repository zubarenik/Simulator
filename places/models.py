from django.db.models.deletion import CASCADE
from pages.models import Page
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from theories.models import TheoryChapter
from characters.models import Character
import logging
logger = logging.getLogger("django.server")
User = get_user_model()

PLACE_TYPE_CHOICES = [
  ('theory', 'Теория'),
  ('question', 'Вовпрос'),
  ('message', 'Сообщение'),
  ('safetext', 'Текст'),
  ('openquestion', 'Открытый вопрос'),
  ('test', 'Тест'),
  ('openquestionexpert', 'Открытый вопрос эксперту'),
  ('questionanswercheck', 'Открытый вопрос с проверкой'),
  ('questionuserchoice', 'Вопрос с выбором пользователя')
]
# Create your models here.
class Place(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    type = models.CharField(choices=PLACE_TYPE_CHOICES, max_length=200)

    text = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=10000, blank=True, null=True)
    female_text = models.TextField(blank=True, null=True,)
    text_description = models.TextField(null=True, blank=True)
    postreply_text = models.TextField(blank=True, null=True,)
    postreply_female_text = models.TextField(blank=True, null=True)
    postreply_error_text = models.TextField(blank=True, null=True)
    postreply_error_female_text = models.TextField(blank=True, null=True)
    comment_number = models.IntegerField(blank=True, null=True)
    is_start = models.BooleanField(default=False)
    is_end = models.BooleanField(default=False)
    points = models.IntegerField(default=0, null=True, blank=True)
    points_error = models.IntegerField(default=0, null=True, blank=True)
    comment_advice = models.TextField(blank=True, null=True,)
    comment_female_advice = models.TextField(blank=True, null=True,)
    correct_answer = models.TextField(blank=True, null=True,)
    script_id = models.CharField(max_length=300, blank=True, null=True)
    script_text = models.TextField(blank=True, null=True)
    need_notifications = models.BooleanField(blank=True, null=True)
    award = models.IntegerField(blank=True, null=True)
    award_error = models.IntegerField(blank=True, null=True)
    theory_chapter = models.ForeignKey(TheoryChapter,blank=True, null=True, on_delete=models.CASCADE)
    character = models.ForeignKey(Character,blank=True, null=True, on_delete=models.CASCADE)
    node_position_x = models.IntegerField(blank=True, null=True)
    node_position_y = models.IntegerField(blank=True, null=True)
    node_id = models.CharField(max_length=300, blank=True, null=True)
    node_info = JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    answers = JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    parent_message = models.ForeignKey('self', null=True, blank=True, on_delete=CASCADE)
    next_places = JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    is_multiple = models.BooleanField(null=True, blank=True)
    forced_role = models.CharField(max_length=255,blank=True, null=True)
    is_hero = models.BooleanField(default=False)
    is_current_user = models.BooleanField(default=False)
    is_author_message = models.BooleanField(default=False)

    def get_next_place(self, user, p_user):
      place_user = PlaceUser.objects.get(user=user, place=self, is_completed=True)
      points = place_user.points
      if not self.next_places:
        return None
      if not 'places' in self.next_places:
        return None
      next_place = None
      next_places = [place for place in self.next_places['places'] if 'award' in place]
      next_places = sorted(next_places, key=lambda k: int(k['award']), reverse=True)
      for place in next_places:
        if points >= int(place['award']):
          next_place = Place.objects.filter(id=place['place']).first()
          if not next_place:
            continue
          break
      return next_place

    def complete_place(self, user, p_user, award=0, *args, **kwargs):
      if not award:
        award = 0
      place_user = PlaceUser.objects.filter(user=user, place=self).first()
      answers = None
      user_answer = None
      is_correct = None
      if not place_user:
        place_user = PlaceUser(user=user, place=self)


      if 'answers' in kwargs:
        if 'is_correct' in kwargs:
          is_correct= kwargs['is_correct']
        answers = kwargs['answers']
        place_user.answers = answers

      if 'user_answer' in kwargs:
        if 'is_correct' in kwargs:
          is_correct= kwargs['is_correct']
        user_answer = kwargs['user_answer']
        place_user.answers = user_answer
      place_user.points = award
      place_user.is_completed = True
      for idx, place  in enumerate(p_user.places):
        if self.id == int(place['id']):
          p_user.places[idx]['complete'] = True
          p_user.places[idx]['user_answers'] = answers
          p_user.places[idx]['user_answer'] = user_answer
          p_user.places[idx]['is_correct'] = is_correct
      p_user.points = p_user.points + award
      p_user.save()
      place_user.save()

    def theory_action(self, user, p_user, *args, **kwargs):
      self.complete_place(user, p_user, award=self.points)

    def question_action(self, user, p_user, *args, **kwargs):
      award = 0
      is_correct = True
      answers = kwargs['answers']

      if self.is_multiple:
        for idx, answer in enumerate(self.answers):
          if not answer['is_correct'] and idx in answers:
            is_correct = False
          if answer['is_correct'] and not idx in answers:
            is_correct = False
          if answer['points']:
            award += int(answer['points'])
      else:
        for idx, answer in enumerate(self.answers):
          if idx in answers:
            if not answer['is_correct']:
              is_correct = False
            award += int(answer['points'])
      if is_correct and self.points:
        award += self.points
      elif not is_correct and self.points_error:
        award += self.points_error
      self.complete_place(user, p_user, award, answers=answers, is_correct=is_correct)

    def message_action(self, user, p_user, *args, **kwargs):
      self.complete_place(user, p_user, award=self.points)

    def safetext_action(self, user, p_user, *args, **kwargs):
      self.complete_place(user, p_user, award=self.points)

    def openquestion_action(self, user, p_user, *args, **kwargs):
      self.complete_place(user, p_user, user_answer=kwargs['user_answer'])
    
    def openquestionexpert_action(self, user, p_user, *args, **kwargs):
      self.complete_place(user, p_user, user_answer=kwargs['user_answer'])

    def questionanswercheck_action(self, user, p_user, *args, **kwargs):
      answer = kwargs['user_answer'].strip().lower()
      is_correct = True
      points = 0
      if self.points:
        points = self.points
      if not answer == self.correct_answer.strip().lower():
        is_correct = False
        if self.self.points_error:
          points = self.points_error
      self.complete_place(user, p_user, user_answer=kwargs['user_answer'], award=points, is_correct=is_correct)

    def questionuserchoice_action(self, user, p_user, *args, **kwargs):
      award = 0
      answers = kwargs['answers']
      if self.is_multiple:
        for idx, answer in enumerate(self.answers):
          if idx in answers:
            if answer['points']:
              award += int(answer['points'])
      if self.points:
        award += self.points

      self.complete_place(user, p_user, award, answers=answers)
      
    def __str__(self):
        return '(id={}){} - {}'.format(self.id, self.type, self.text)


class PlaceUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    answers = JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    comments = JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)      

    def __str__(self):
        return '{} - {}'.format(self.place, self.user)


