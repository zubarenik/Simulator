from django.db import models
from django.contrib.auth import get_user_model

from emails.models import Email
from payments.models import Payment

from django.core.validators import FileExtensionValidator
from simulator_groups.models import SimulatorGroup
from django.db.models import Max

User = get_user_model()


class Simulator(models.Model):
    completed_by_user_set = models.ManyToManyField(User, blank=True, related_name='completed_simulators')
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField(default=30000)
    domain = models.CharField(max_length=200, unique=True)
    alias = models.CharField(max_length=255, unique=True, null=True, blank=True)
    color = models.CharField(max_length=255, default="#08a2dc")
    description = models.TextField()
    picture = models.ImageField(upload_to='simulator_images', blank=True, null=True)
    logo = models.ImageField(upload_to='simulator_logos', blank=True, null=True)
    favicon = models.ImageField(upload_to='simulator_favicons', blank=True, null=True)
    owner_generated_domain = models.CharField(max_length=200, unique=True, null=True, blank=True)
    admin_comment_request_price = models.PositiveIntegerField(default=10)
    group = models.ForeignKey(SimulatorGroup, on_delete=models.CASCADE)
    order_lesson = models.BooleanField(default=False)
    onboarding_skip = models.BooleanField(default=False, null=True, blank=True)
    onboarding_name = models.CharField(max_length=200, default='Онбординг', null=True, blank=True)
    simulator_script = models.TextField(null=True, blank=True)
    sequence_no = models.PositiveIntegerField(null=True)
    css = models.FileField(upload_to='simulator_css', default='simulator_css/default.css', validators=[FileExtensionValidator(allowed_extensions=['css'])])
    token = models.CharField(max_length=32, blank=True, null=True, unique=True)
    notifications_url = models.CharField(max_length=300, blank=True, null=True)
    agreement_url = models.CharField(max_length=300, blank=True, null=True)
    data_processing_url = models.CharField(max_length=300, blank=True, null=True)

    welcome_message_text = models.TextField(null=True, blank=True)
    welcome_message_author_name = models.CharField(null=True, blank=True, max_length=255)
    welcome_message_author_img = models.ImageField(upload_to='simulator_images', blank=True, null=True)
    main_color = models.CharField(null=True, blank=True, max_length=255)
    message_after_task = models.TextField(null=True, blank=True)
    message_after_chapter = models.TextField(null=True, blank=True)
    text_button_after_chapter = models.CharField(null=True, blank=True, max_length=255)

    pay_TerminalKey = models.CharField(null=True, blank=True, max_length=255)
    pay_EmailCompany = models.CharField(null=True, blank=True, max_length=255)
    pay_password = models.CharField(null=True, blank=True, max_length=255)
    pay_type = models.CharField(max_length=255, default='tinkoff', choices=Payment.TYPE_CHOICES)
    vat = models.IntegerField(default=None, null=True)

    telegram = models.CharField(null=True, blank=True, max_length=300)
    facebook = models.CharField(null=True, blank=True, max_length=300)
    vkontakte = models.CharField(null=True, blank=True, max_length=300)
    whatsapp = models.CharField(null=True, blank=True, max_length=300)

    recommended_volume = models.IntegerField(blank=True, null=True)

    theory_award = models.IntegerField(blank=True, default=0)
    message_award = models.IntegerField(blank=True, default=0)
    safetext_award = models.IntegerField(blank=True, default=0)
    test_award_correct = models.IntegerField(blank=True, default=0)
    test_award_error = models.IntegerField(blank=True, default=0)
    question_award_correct = models.IntegerField(blank=True, default=0)
    question_award_error = models.IntegerField(blank=True, default=0)
    questionuserchoice_award = models.IntegerField(blank=True, default=0)
    openquestion_award = models.IntegerField(blank=True, default=0)
    vat = models.IntegerField(null=True, blank=True)
    openquestionexpert_award = models.IntegerField(blank=True, default=0)
    questionanswercheck_award_correct = models.IntegerField(blank=True, default=0)
    questionanswercheck_award_error = models.IntegerField(blank=True, default=0)

    need_pause = models.BooleanField(blank=True, null=True)
    pause_length = models.IntegerField(blank=True, null=True)
    pause_text = models.TextField(blank=True, null=True)

    random_icon = models.TextField(blank=True, null=True)
    random_text = models.TextField(blank=True, null=True)
    random_link = models.CharField(max_length=2000, blank=True, null=True)
    random_showing = models.BooleanField(blank=True, null=True)
    show_page_mark = models.BooleanField(default=True)
    
    @property
    def onboarding_id(self):
        return self.onboarding.id
        
    @property
    def max_seq_no(self):
        seq_no = Simulator.objects.filter(group=self.group).aggregate(Max("sequence_no"))['sequence_no__max']
        if seq_no:
            seq_no = seq_no + 1
        else:
            seq_no = 1
        return seq_no

    def is_user_owner(self, user):
        return self.group.owner == user

    def create_onboarding(self):
        from pages.models import Page
        onboarding = Page(name="Онбоардинг", is_onboarding_for = self)
        onboarding.save()

    def complete(self, user):
        sim_user = SimulatorUser.objects.get(simulator=self, user=user)
        sim_user.simulator_completed = True
        sim_user.save()

    def send_email(self, type, user, password=None):
        email = Email.objects.filter(simulator=self, email_type=type).first()
        if email:
            email.send_email(user=user, email_sender=self.group.email_sender, password=password)

    def get_vat(self):
        if self.vat:
            return self.vat
        return "null"

    def __str__(self):
        return '({}) {}'.format(self.id, self.name)


class SimulatorUser(models.Model):
    simulator = models.ForeignKey(Simulator, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    current_page = models.ForeignKey('pages.Page', on_delete=models.SET_NULL, null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    simulator_paid = models.BooleanField(default=False)
    simulator_completed = models.BooleanField(default=False)
    first_uncompleted_lesson = models.ForeignKey('lessons.lesson', on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, auto_now_add=True)

    def __str__(self):
        return '({}) {} - {}'.format(self.id, self.simulator.name, self.user.email)

